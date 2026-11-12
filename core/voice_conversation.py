import asyncio

from google.genai import types

from intelligence.gemini_live import GeminiLive
from core.tool_router import ToolRouter
from voice.audio_input import MicrophoneInput
from voice.audio_output import AudioOutput

from config.settings import INPUT_SAMPLE_RATE

from memory.conversation_history import ConversationHistory
from memory.memory_extractor import MemoryExtractor
from memory.extraction_queue import ExtractionQueue


class VoiceConversation:

    def __init__(self, ai=None, on_status=None, on_message=None):

        self.ai = ai if ai else GeminiLive()
        self.tool_router = ToolRouter()

        self.microphone = MicrophoneInput()
        self.speaker = AudioOutput()

        self.on_status = on_status
        self.on_message = on_message

        self.history = ConversationHistory()

        self.memory_extractor = MemoryExtractor(
            self.history.memory
        )

        self.extraction_queue = ExtractionQueue()

        self.stop_sending = asyncio.Event()
        self.playback_queue = asyncio.Queue()

        self.user_transcript_buffer = ""
        self.ai_transcript_buffer = ""

        self.session_transcript = []

        self.tasks = []
        self.started = False
        self.cleaned_up = False

    # ==========================================
    # STATUS
    # ==========================================

    def update_status(self, state, description=""):

        if self.on_status:

            try:
                self.on_status(state, description)

            except Exception as error:
                print("STATUS CALLBACK ERROR:", error)

    # ==========================================
    # MESSAGE HANDLING
    # ==========================================

    def add_message(self, speaker, message):

        if not message or not message.strip():
            return

        message = message.strip()

        if speaker == "YOU":
            self.history.add_user_message(message)

        elif speaker == "ZORIN":
            self.history.add_assistant_message(message)

        self.session_transcript.append(
            f"{speaker}: {message}"
        )

        if self.on_message:

            try:
                self.on_message(speaker, message)

            except Exception as error:
                print("MESSAGE CALLBACK ERROR:", error)

    # ==========================================
    # TRANSCRIPT HANDLING
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
    # MEMORY EXTRACTION QUEUE
    # ==========================================

    async def extract_session_memories(self):

        if not self.session_transcript:
            return

        conversation = "\n".join(
            self.session_transcript
        )

        if len(conversation.strip()) < 30:
            return

        try:

            queue_id = self.extraction_queue.enqueue(
                conversation
            )

            if queue_id:

                print(
                    "\nZORIN MEMORY: Conversation saved "
                    f"to offline extraction queue. ID: {queue_id}"
                )

        except Exception as error:

            print(
                "\nZORIN MEMORY QUEUE ERROR:",
                repr(error)
            )

    # ==========================================
    # MICROPHONE SENDER
    # ==========================================

    async def send_microphone_audio(self):

        print("\nZORIN IS LISTENING...")

        while not self.stop_sending.is_set():

            if self.ai.session is None:

                await asyncio.sleep(0.1)
                continue

            try:

                audio_data = await asyncio.wait_for(
                    self.microphone.read(),
                    timeout=0.2
                )

                if self.stop_sending.is_set():
                    break

                session = self.ai.session

                if session is None:
                    continue

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

                print(
                    "MICROPHONE SENDING ERROR:",
                    repr(error)
                )

                await asyncio.sleep(0.5)

    # ==========================================
    # AUDIO PLAYBACK WORKER
    # ==========================================

    async def playback_worker(self):

        while not self.stop_sending.is_set():

            try:

                audio_data = await asyncio.wait_for(
                    self.playback_queue.get(),
                    timeout=0.2
                )

            except asyncio.TimeoutError:
                continue

            try:

                if not self.stop_sending.is_set():

                    await asyncio.to_thread(
                        self.speaker.play_chunk,
                        audio_data
                    )

            except asyncio.CancelledError:
                raise

            except Exception as error:

                print(
                    "AUDIO PLAYBACK ERROR:",
                    repr(error)
                )

            finally:

                self.playback_queue.task_done()

    # ==========================================
    # CLEAR PLAYBACK QUEUE
    # ==========================================

    def clear_playback_queue(self):

        while not self.playback_queue.empty():

            try:

                self.playback_queue.get_nowait()
                self.playback_queue.task_done()

            except asyncio.QueueEmpty:
                break

    # ==========================================
    # GEMINI TOOL CALL HANDLER
    # ==========================================

    async def handle_tool_calls(self, session, tool_call):

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

                result = {
                    "success": False,
                    "message": str(error)
                }

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

                    self.update_status(
                        "connecting",
                        "Reconnecting to Gemini..."
                    )

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

                    # HANDLE GEMINI TOOL CALLS FIRST

                    tool_call = getattr(
                        response,
                        "tool_call",
                        None
                    )

                    if tool_call and tool_call.function_calls:

                        await self.handle_tool_calls(
                            session,
                            tool_call
                        )

                    # NORMAL GEMINI RESPONSE

                    content = getattr(
                        response,
                        "server_content",
                        None
                    )

                    if not content:
                        continue

                    # USER TRANSCRIPTION

                    if content.input_transcription:

                        user_text = (
                            content.input_transcription.text or ""
                        )

                        if user_text:

                            self.user_transcript_buffer += (
                                user_text + " "
                            )

                            self.update_status(
                                "listening",
                                "Listening to your voice..."
                            )

                            normalized_text = (
                                self.user_transcript_buffer.lower()
                                .replace(".", " ")
                                .replace(",", " ")
                                .replace("!", " ")
                                .replace("?", " ")
                            )

                            words = normalized_text.split()

                            if (
                                "goodbye" in words
                                and any(
                                    name in words
                                    for name in [
                                        "zorin",
                                        "soren",
                                        "sorin",
                                        "zoren",
                                        "zoran"
                                    ]
                                )
                            ):

                                self.flush_transcripts()

                                print(
                                    "\nZORIN: Returning to standby."
                                )

                                self.update_status(
                                    "idle",
                                    "Returning to wake-word standby..."
                                )

                                self.stop_sending.set()
                                break

                    # AI TRANSCRIPTION

                    if content.output_transcription:

                        ai_text = (
                            content.output_transcription.text or ""
                        )

                        if ai_text:

                            self.ai_transcript_buffer += (
                                ai_text + " "
                            )

                            self.update_status(
                                "speaking",
                                "ZORIN is responding..."
                            )

                    # USER INTERRUPTS AI

                    if content.interrupted:

                        self.clear_playback_queue()

                        await asyncio.to_thread(
                            self.speaker.stop
                        )

                        self.update_status(
                            "listening",
                            "I'm listening..."
                        )

                    # AI AUDIO

                    if content.model_turn:

                        for part in content.model_turn.parts:

                            if (
                                part.inline_data
                                and part.inline_data.data
                            ):

                                self.playback_queue.put_nowait(
                                    part.inline_data.data
                                )

                                self.update_status(
                                    "speaking",
                                    "ZORIN is speaking..."
                                )

                    # TURN COMPLETE

                    if content.turn_complete:

                        self.flush_transcripts()

                        print(
                            "\nZORIN FINISHED RESPONDING."
                        )

                        self.update_status(
                            "listening",
                            "I'm listening..."
                        )

                if not self.stop_sending.is_set():

                    await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                raise

            except Exception as error:

                if self.stop_sending.is_set():
                    break

                print(
                    "\nGEMINI RECEIVE ERROR:",
                    repr(error)
                )

                self.update_status(
                    "connecting",
                    "Reconnecting to Gemini..."
                )

                try:
                    await self.ai.disconnect()

                except Exception as disconnect_error:

                    print(
                        "GEMINI DISCONNECT ERROR:",
                        repr(disconnect_error)
                    )

                await asyncio.sleep(2)

    # ==========================================
    # SAFE RESOURCE CLEANUP
    # ==========================================

    async def cleanup(self):

        if self.cleaned_up:
            return

        self.cleaned_up = True

        print("\nZORIN: Cleaning up conversation resources...")

        self.stop_sending.set()

        current_task = asyncio.current_task()

        # Cancel background tasks.

        for task in self.tasks:

            if task is not current_task and not task.done():
                task.cancel()

        if self.tasks:

            await asyncio.gather(
                *self.tasks,
                return_exceptions=True
            )

        self.tasks.clear()

        # Save remaining transcripts.

        try:

            self.flush_transcripts()

        except Exception as error:

            print(
                "TRANSCRIPT SAVE ERROR:",
                repr(error)
            )

        # Clear playback queue.

        try:

            self.clear_playback_queue()

        except Exception as error:

            print(
                "PLAYBACK QUEUE CLEANUP ERROR:",
                repr(error)
            )

        # Stop microphone.

        try:

            await self.microphone.stop()

        except Exception as error:

            print(
                "MICROPHONE CLEANUP ERROR:",
                repr(error)
            )

        # Stop speaker.

        try:

            await asyncio.to_thread(
                self.speaker.stop
            )

        except Exception as error:

            print(
                "SPEAKER CLEANUP ERROR:",
                repr(error)
            )

        try:

            await asyncio.to_thread(
                self.speaker.stop_stream
            )

        except Exception as error:

            print(
                "SPEAKER STREAM CLEANUP ERROR:",
                repr(error)
            )

        # Disconnect Gemini.

        try:

            await self.ai.disconnect()

        except Exception as error:

            print(
                "GEMINI CLEANUP ERROR:",
                repr(error)
            )

        # Queue conversation for memory extraction.

        try:

            await self.extract_session_memories()

        except Exception as error:

            print(
                "MEMORY EXTRACTION QUEUE ERROR:",
                repr(error)
            )

        # Close conversation history.

        try:

            self.history.end()

        except Exception as error:

            print(
                "HISTORY CLEANUP ERROR:",
                repr(error)
            )

        self.update_status(
            "idle",
            "Conversation ended. Returning to standby..."
        )

        print("ZORIN: Conversation cleanup completed.")

    # ==========================================
    # START CONVERSATION
    # ==========================================

    async def start(self):

        if self.started:

            print("Conversation already started.")
            return

        self.started = True

        self.history.start()

        print("\nConversation memory session started.")

        try:

            # Connect Gemini.

            if self.ai.session is None:

                connected = await self.ai.connect()

                if not connected:

                    print(
                        "Unable to connect to Gemini."
                    )

                    return

            # Start microphone.

            await self.microphone.start()

            # Start speaker.

            await asyncio.to_thread(
                self.speaker.start_stream
            )

            print("\n==============================")
            print("       ZORIN IS ONLINE")
            print("==============================")

            self.update_status(
                "listening",
                "I'm listening. Talk to me!"
            )

            # Create background tasks.

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

            self.tasks = [
                sender,
                receiver,
                playback
            ]

            # Wait until one task exits or fails.

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

            print(
                "\nZORIN: Conversation cancellation requested."
            )

            raise

        except Exception as error:

            print(
                "\nVOICE CONVERSATION ERROR:",
                repr(error)
            )

            self.update_status(
                "idle",
                "Conversation ended because of an error."
            )

        finally:

            await self.cleanup()