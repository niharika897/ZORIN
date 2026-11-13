import asyncio
from enum import Enum
import re
import time
from typing import Optional, Callable, List, Tuple

from google.genai import types

from intelligence.gemini_live import GeminiLive
from core.tool_router import ToolRouter
from voice.audio_input import MicrophoneInput
from voice.audio_output import AudioOutput
from config.settings import (
    INPUT_SAMPLE_RATE,
    set_voice_preference,
    get_voice_gender,
)
from memory.conversation_history import ConversationHistory
from memory.memory_extractor import MemoryExtractor
from memory.extraction_queue import ExtractionQueue


class ConversationState(str, Enum):
    """Controlled conversation states for predictable turn-taking."""
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    RECONNECTING = "RECONNECTING"
    STOPPED = "STOPPED"


class VoiceConversation:
    """
    Central real-time voice conversation coordinator for ZORIN.
    Features instant barge-in interruption, turn-taking state management,
    lossless audio playback buffering, and shared persistent memory integration.
    """

    # Barge-in RMS threshold (when AI speaker is playing)
    BARGE_IN_RMS_THRESHOLD = 350.0

    def __init__(
        self,
        ai: Optional[GeminiLive] = None,
        on_status: Optional[Callable[[str, str], None]] = None,
        on_message: Optional[Callable[[str, str], None]] = None,
        on_voice_changed: Optional[Callable[[str], None]] = None,
        input_device: Optional[int] = None,
        output_device: Optional[int] = None,
    ):
        self.ai = ai if ai is not None else GeminiLive()
        self.tool_router = ToolRouter()

        self.microphone = MicrophoneInput(device=input_device)
        self.speaker = AudioOutput(device=output_device)

        self.on_status = on_status
        self.on_message = on_message
        self.on_voice_changed = on_voice_changed

        self.history = ConversationHistory()
        self.memory_extractor = MemoryExtractor(self.history.memory)
        self.extraction_queue = ExtractionQueue()

        self.stop_sending = asyncio.Event()

        # Unbounded queue of tuples: (generation_id, audio_bytes) to prevent chunk drops
        self.playback_queue: asyncio.Queue[Tuple[int, bytes]] = asyncio.Queue()

        self.state = ConversationState.IDLE
        self.current_generation_id = 0

        self.user_transcript_buffer = ""
        self.ai_transcript_buffer = ""
        self.session_transcript: List[str] = []

        self.tasks: List[asyncio.Task] = []
        self.started = False
        self.cleaned_up = False

        # Barge-in tracking counters
        self._consecutive_loud_frames = 0

    # ==========================================
    # STATE MANAGEMENT
    # ==========================================

    def set_state(self, new_state: ConversationState, description: str = ""):
        """Controlled transition of conversation state."""
        self.state = new_state
        print(f"[CONVERSATION STATE] -> {new_state.value}: {description}")
        self.update_status(new_state.value.lower(), description)

    def update_status(self, state: str, description: str = ""):
        if self.on_status:
            try:
                self.on_status(state, description)
            except Exception as error:
                print("STATUS CALLBACK ERROR:", error)

    # ==========================================
    # MESSAGE HANDLING
    # ==========================================

    def add_message(self, speaker: str, message: str):
        if not message or not message.strip():
            return

        message = message.strip()

        if speaker == "YOU":
            self.history.add_user_message(message)
        elif speaker == "ZORIN":
            self.history.add_assistant_message(message)

        self.session_transcript.append(f"{speaker}: {message}")

        if self.on_message:
            try:
                self.on_message(speaker, message)
            except Exception as error:
                print("MESSAGE CALLBACK ERROR:", error)

    # ==========================================
    # TRANSCRIPT FLUSHING
    # ==========================================

    def flush_transcripts(self):
        if self.user_transcript_buffer.strip():
            message = self.user_transcript_buffer.strip()
            print("\nYOU:", message)
            self.add_message("YOU", message)

        if self.ai_transcript_buffer.strip():
            message = self.ai_transcript_buffer.strip()
            print("\nZORIN:", message)
            self.add_message("ZORIN", message)

        self.user_transcript_buffer = ""
        self.ai_transcript_buffer = ""

    # ==========================================
    # MEMORY EXTRACTION
    # ==========================================

    async def extract_session_memories(self):
        if not self.session_transcript:
            return

        conversation = "\n".join(self.session_transcript)
        if len(conversation.strip()) < 30:
            return

        try:
            queue_id = self.extraction_queue.enqueue(conversation)
            if queue_id:
                print(
                    "\nZORIN MEMORY: Conversation saved "
                    f"to offline extraction queue. ID: {queue_id}"
                )
        except Exception as error:
            print("\nZORIN MEMORY QUEUE ERROR:", repr(error))

    # ==========================================
    # REAL-TIME BARGE-IN INTERRUPTION
    # ==========================================

    def trigger_barge_in(self, reason: str = "User spoke"):
        """
        Immediately stops currently playing AI audio, invalidates obsolete
        response generation, and clears all queued playback buffers.
        """
        print(f"\n⚡ [BARGE-IN] Interruption triggered ({reason})! Halting speaker output...")

        # Invalidate current generation so trailing in-flight network chunks are discarded
        self.current_generation_id += 1

        # Stop speaker output stream & clear local sounddevice queue
        self.speaker.stop()

        # Clear asyncio playback queue
        self.clear_playback_queue()

        self.set_state(ConversationState.INTERRUPTED, "Listening to you...")

    def clear_playback_queue(self):
        """Purges any pending chunks from the async playback queue."""
        while not self.playback_queue.empty():
            try:
                self.playback_queue.get_nowait()
                self.playback_queue.task_done()
            except asyncio.QueueEmpty:
                break

    # ==========================================
    # MICROPHONE SENDER & BARGE-IN MONITOR
    # ==========================================

    async def send_microphone_audio(self):
        print("\nZORIN IS LISTENING...")
        self.set_state(ConversationState.LISTENING, "I'm listening. Speak naturally...")

        while not self.stop_sending.is_set():
            if self.ai.session is None:
                await asyncio.sleep(0.1)
                continue

            try:
                audio_data = await asyncio.wait_for(
                    self.microphone.read(),
                    timeout=0.25
                )

                if self.stop_sending.is_set():
                    break

                # ----------------------------------------------------
                # BARGE-IN DETECTION: Check if user spoke while AI plays
                # ----------------------------------------------------
                if self.speaker.is_playing():
                    rms = self.microphone.current_rms
                    if rms > self.BARGE_IN_RMS_THRESHOLD:
                        self._consecutive_loud_frames += 1
                        if self._consecutive_loud_frames >= 2:
                            # 2 consecutive blocks (~200ms) of sustained user voice
                            self.trigger_barge_in("Voice energy detected during speech")
                            self._consecutive_loud_frames = 0
                    else:
                        self._consecutive_loud_frames = 0
                else:
                    self._consecutive_loud_frames = 0

                # Send audio chunk to Gemini Live
                session = self.ai.session
                if session is not None:
                    await session.send_realtime_input(
                        audio=types.Blob(
                            data=audio_data,
                            mime_type=f"audio/pcm;rate={INPUT_SAMPLE_RATE}"
                        )
                    )

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception as error:
                if self.stop_sending.is_set():
                    break
                print("MICROPHONE SENDING ERROR:", repr(error))
                await asyncio.sleep(0.5)

    # ==========================================
    # AUDIO PLAYBACK WORKER
    # ==========================================

    async def playback_worker(self):
        """Dedicated worker feeding non-blocking PortAudio stream with generation guards."""
        while not self.stop_sending.is_set():
            try:
                generation_id, audio_data = await asyncio.wait_for(
                    self.playback_queue.get(),
                    timeout=0.2
                )
            except asyncio.TimeoutError:
                continue

            try:
                # Discard chunks belonging to an interrupted or past turn
                if generation_id == self.current_generation_id and not self.stop_sending.is_set():
                    await asyncio.to_thread(
                        self.speaker.play_chunk,
                        audio_data,
                        generation_id
                    )
            except asyncio.CancelledError:
                raise
            except Exception as error:
                print("AUDIO PLAYBACK ERROR:", repr(error))
            finally:
                self.playback_queue.task_done()

    # ==========================================
    # GEMINI TOOL CALL HANDLER
    # ==========================================

    async def handle_tool_calls(self, session, tool_call):
        self.set_state(ConversationState.PROCESSING, "Executing action...")
        function_responses = []

        for function_call in tool_call.function_calls:
            name = function_call.name
            arguments = dict(function_call.args or {})

            print(f"\nZORIN TOOL REQUEST: {name}")
            print("TOOL ARGUMENTS:", arguments)

            try:
                result = await asyncio.to_thread(
                    self.tool_router.execute,
                    name,
                    **arguments
                )
            except Exception as error:
                print("TOOL EXECUTION ERROR:", repr(error))
                result = {"success": False, "message": str(error)}

            print("TOOL RESULT:", result)

            function_responses.append(
                types.FunctionResponse(
                    id=function_call.id,
                    name=name,
                    response=result
                )
            )

        if function_responses:
            await session.send_tool_response(
                function_responses=function_responses
            )

    # ==========================================
    # GEMINI RESPONSE RECEIVER
    # ==========================================

    async def receive_ai_audio(self):
        print("\nZORIN IS READY TO RESPOND!")

        while not self.stop_sending.is_set():
            try:
                if self.ai.session is None:
                    self.set_state(ConversationState.RECONNECTING, "Reconnecting to Gemini...")
                    connected = await self.ai.connect()
                    if not connected:
                        await asyncio.sleep(2)
                        continue

                session = self.ai.session
                if session is None:
                    await asyncio.sleep(0.5)
                    continue

                async for response in session.receive():
                    if self.stop_sending.is_set():
                        break

                    # 1. TOOL CALLS
                    tool_call = getattr(response, "tool_call", None)
                    if tool_call and tool_call.function_calls:
                        await self.handle_tool_calls(session, tool_call)

                    content = getattr(response, "server_content", None)
                    if not content:
                        continue

                    # 2. USER TRANSCRIPTION
                    if content.input_transcription:
                        user_text = content.input_transcription.text or ""
                        if user_text:
                            self.user_transcript_buffer += user_text + " "
                            if self.state != ConversationState.SPEAKING:
                                self.set_state(ConversationState.LISTENING, "Listening to your voice...")

                            normalized_text = re.sub(
                                r"[^a-z\s]",
                                " ",
                                self.user_transcript_buffer.lower()
                            )
                            normalized_text = " ".join(normalized_text.split())
                            words = normalized_text.split()

                            # Spoken voice switching
                            requested_voice = None
                            voice_patterns = {
                                "female": (
                                    r"\b(?:switch|change|set|make|use|choose|select)\b.{0,40}\bfemale\b",
                                    r"\b(?:i want|id like|give me|please use)\b.{0,30}\bfemale\b",
                                    r"\bfemale\s+voice\s+(?:please|now|instead)\b",
                                ),
                                "male": (
                                    r"\b(?:switch|change|set|make|use|choose|select)\b.{0,40}\bmale\b",
                                    r"\b(?:i want|id like|give me|please use)\b.{0,30}\bmale\b",
                                    r"\bmale\s+voice\s+(?:please|now|instead)\b",
                                ),
                            }
                            for gender, patterns in voice_patterns.items():
                                if any(re.search(pat, normalized_text) for pat in patterns):
                                    requested_voice = gender
                                    break

                            if requested_voice:
                                voice_name = set_voice_preference(requested_voice)
                                gender = get_voice_gender(voice_name)
                                print(f"\nZORIN: Switching to {gender} voice.")
                                self.flush_transcripts()
                                if self.on_voice_changed:
                                    self.on_voice_changed(gender)
                                self.set_state(ConversationState.IDLE, f"Switched to {gender} voice. Returning to standby...")
                                self.stop_sending.set()
                                break

                            # Spoken goodbye
                            if "goodbye" in words and any(
                                n in words for n in ["zorin", "soren", "sorin", "zoren", "zoran"]
                            ):
                                self.flush_transcripts()
                                print("\nZORIN: Returning to standby.")
                                self.set_state(ConversationState.IDLE, "Returning to wake-word standby...")
                                self.stop_sending.set()
                                break

                    # 3. AI TRANSCRIPTION
                    if content.output_transcription:
                        ai_text = content.output_transcription.text or ""
                        if ai_text:
                            self.ai_transcript_buffer += ai_text + " "
                            if self.state != ConversationState.SPEAKING:
                                self.set_state(ConversationState.SPEAKING, "ZORIN is responding...")

                    # 4. SERVER-SIDE GEMINI INTERRUPTION EVENT
                    if content.interrupted:
                        self.trigger_barge_in("Gemini Live server signaled interruption")

                    # 5. AI AUDIO STREAMING
                    if content.model_turn:
                        for part in content.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                # Queue chunk with current generation id
                                self.playback_queue.put_nowait(
                                    (self.current_generation_id, part.inline_data.data)
                                )
                                self.set_state(ConversationState.SPEAKING, "ZORIN is speaking...")

                    # 6. TURN COMPLETE FROM SERVER
                    if content.turn_complete:
                        # Flush captured transcripts
                        self.flush_transcripts()
                        print("\nZORIN: Server finished generating audio.")

                        # Wait until the speaker has finished playing buffered audio chunks
                        # before declaring turn complete and returning to LISTENING
                        turn_gen_id = self.current_generation_id
                        while (
                            self.speaker.is_playing()
                            and turn_gen_id == self.current_generation_id
                            and not self.stop_sending.is_set()
                        ):
                            await asyncio.sleep(0.05)

                        if turn_gen_id == self.current_generation_id and not self.stop_sending.is_set():
                            print("\nZORIN FINISHED RESPONDING.")
                            self.set_state(ConversationState.LISTENING, "I'm listening...")

                if not self.stop_sending.is_set():
                    await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                raise
            except Exception as error:
                if self.stop_sending.is_set():
                    break
                print("\nGEMINI RECEIVE ERROR:", repr(error))
                self.set_state(ConversationState.RECONNECTING, "Reconnecting to Gemini...")
                try:
                    await self.ai.disconnect()
                except Exception as disconnect_error:
                    print("GEMINI DISCONNECT ERROR:", repr(disconnect_error))
                await asyncio.sleep(2)

    # ==========================================
    # RESOURCE CLEANUP
    # ==========================================

    async def cleanup(self):
        if self.cleaned_up:
            return
        self.cleaned_up = True

        print("\nZORIN: Cleaning up conversation resources...")
        self.stop_sending.set()

        current_task = asyncio.current_task()
        for task in self.tasks:
            if task is not current_task and not task.done():
                task.cancel()

        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

        try:
            self.flush_transcripts()
        except Exception as error:
            print("TRANSCRIPT SAVE ERROR:", repr(error))

        try:
            self.clear_playback_queue()
        except Exception as error:
            print("PLAYBACK QUEUE CLEANUP ERROR:", repr(error))

        try:
            await self.microphone.stop()
        except Exception as error:
            print("MICROPHONE CLEANUP ERROR:", repr(error))

        try:
            await asyncio.to_thread(self.speaker.stop)
        except Exception as error:
            print("SPEAKER STOP ERROR:", repr(error))

        try:
            await asyncio.to_thread(self.speaker.stop_stream)
        except Exception as error:
            print("SPEAKER STREAM CLEANUP ERROR:", repr(error))

        try:
            await self.ai.disconnect()
        except Exception as error:
            print("GEMINI CLEANUP ERROR:", repr(error))

        try:
            await self.extract_session_memories()
        except Exception as error:
            print("MEMORY EXTRACTION QUEUE ERROR:", repr(error))

        try:
            self.history.end()
        except Exception as error:
            print("HISTORY CLEANUP ERROR:", repr(error))

        self.set_state(ConversationState.IDLE, "Conversation ended. Returning to standby...")
        print("ZORIN: Conversation cleanup completed.")

    def stop(self):
        """Signals active voice conversation to cleanly end and return to standby."""
        print("\nZORIN: Manual stop requested for active voice conversation.")
        self.stop_sending.set()
        for task in self.tasks:
            if not task.done():
                task.cancel()

    # ==========================================
    # START CONVERSATION LIFECYCLE
    # ==========================================

    async def start(self):
        if self.started:
            print("Conversation already started.")
            return

        self.started = True
        self.history.start()
        print("\nConversation memory session started.")

        try:
            if self.ai.session is None:
                connected = await self.ai.connect()
                if not connected:
                    print("Unable to connect to Gemini.")
                    return

            await self.microphone.start()
            await asyncio.to_thread(self.speaker.start_stream)

            print("\n==============================")
            print("       ZORIN IS ONLINE")
            print("==============================")

            self.set_state(ConversationState.LISTENING, "I'm listening. Talk to me!")

            sender = asyncio.create_task(
                self.send_microphone_audio(),
                name="zorin_microphone_sender"
            )
            receiver = asyncio.create_task(
                self.receive_ai_audio(),
                name="zorin_gemini_receiver"
            )
            playback = asyncio.create_task(
                self.playback_worker(),
                name="zorin_audio_playback"
            )

            self.tasks = [sender, receiver, playback]

            done, pending = await asyncio.wait(
                self.tasks,
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                if task.cancelled():
                    continue
                error = task.exception()
                if error:
                    raise error

            self.stop_sending.set()

        except asyncio.CancelledError:
            print("\nZORIN: Conversation cancellation requested.")
            raise
        except Exception as error:
            print("\nVOICE CONVERSATION ERROR:", repr(error))
            self.set_state(ConversationState.IDLE, "Conversation ended because of an error.")
        finally:
            await self.cleanup()
