import sys
import asyncio
import threading
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import (
    QThread,
    Signal,
    QTimer,
    QObject,
    QEvent,
)

from desktop.modern_ui import ZorinWindow

from voice.wake_word import WakeWordDetector
from core.voice_conversation import VoiceConversation
from intelligence.gemini_live import GeminiLive
from backend.assistant_service import assistant_service

from memory.memory_manager import MemoryManager
from memory.queue_worker import MemoryQueueWorker
from backend.client import register_current_device
from backend.device_registry import get_all_devices
from memory.database import get_default_user_id
from backend.auth import get_user_by_id
from config.settings import get_voice_preference
from voice.audio_manager import AudioManager


# =========================================================
# APPLICATION CLOSE GUARD
# =========================================================

class ApplicationCloseGuard(QObject):

    def __init__(self, window, controller):
        super().__init__(window)
        self.window = window
        self.controller = controller
        self.allow_close = False

    def eventFilter(self, watched, event):
        if (
            watched is self.window
            and event.type() == QEvent.Type.Close
            and not self.allow_close
        ):
            event.ignore()
            self.controller.request_application_close()
            return True
        return False


# =========================================================
# ZORIN BACKGROUND WORKER
# =========================================================

class ZorinWorker(QThread):

    status_changed = Signal(str, str)
    message_received = Signal(str, str)
    error_occurred = Signal(str)
    voice_changed = Signal(str)
    voice_state_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.loop = None
        self.main_task = None
        self.stop_requested = threading.Event()
        self.manual_voice_requested = threading.Event()
        self.active_conversation: Optional[VoiceConversation] = None
        self.conversation_running = False
        self.memory_manager = None

    # -----------------------------------------------------
    # THREAD ENTRY
    # -----------------------------------------------------

    def run(self):
        try:
            asyncio.run(self.run_assistant())
        except asyncio.CancelledError:
            pass
        except Exception as error:
            print("\nZORIN WORKER ERROR:", repr(error))
            self.error_occurred.emit(str(error))
        finally:
            self.loop = None
            self.main_task = None
            print("\nZORIN WORKER THREAD FINISHED.")

    # -----------------------------------------------------
    # MEMORY CONTEXT
    # -----------------------------------------------------

    def load_memory_context(self, memory_manager=None):
        if memory_manager is None:
            memory_manager = MemoryManager()

        saved_memories = memory_manager.get_all_memories()
        persistent_context = memory_manager.get_persistent_memory_context()
        past_conversations = memory_manager.get_past_conversation_context(limit=30)

        sections = []
        if persistent_context:
            sections.append("PERSISTENT MEMORY:\n" + persistent_context)
        if past_conversations:
            sections.append("RECENT PAST CONVERSATIONS:\n" + past_conversations)

        if not sections:
            print("No saved memories or past conversations found.")
            return ""

        print(f"Loaded {len(saved_memories)} long-term memories.")
        return "\n\n".join(sections)

    # -----------------------------------------------------
    # ASYNC WAIT FOR MANUAL TRIGGER OR WAKE WORD
    # -----------------------------------------------------

    async def _wait_for_trigger(self, wake_detector: WakeWordDetector) -> str:
        """
        Listens for EITHER wake-word detection OR manual mic button trigger.
        Ensures both cannot start conflicting voice sessions simultaneously.
        """
        loop = asyncio.get_running_loop()
        wake_task = asyncio.create_task(wake_detector.listen(), name="zorin_wake_listener")

        manual_event = asyncio.Event()

        def poll_manual():
            if self.manual_voice_requested.is_set():
                self.manual_voice_requested.clear()
                manual_event.set()
            elif not self.stop_requested.is_set():
                loop.call_later(0.08, poll_manual)

        poll_manual()
        manual_task = asyncio.create_task(manual_event.wait(), name="zorin_manual_trigger_waiter")

        done, pending = await asyncio.wait(
            [wake_task, manual_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        for p in pending:
            p.cancel()
            try:
                await p
            except (asyncio.CancelledError, Exception):
                pass

        if manual_task in done:
            return "manual"
        return "wake_word"

    # -----------------------------------------------------
    # MAIN ASSISTANT
    # -----------------------------------------------------

    async def run_assistant(self):
        self.loop = asyncio.get_running_loop()
        self.main_task = asyncio.current_task()

        wake_detector = None
        ai = None
        connection_task = None
        memory_worker = None
        memory_worker_task = None

        self.memory_manager = MemoryManager()

        if self.stop_requested.is_set():
            self.main_task.cancel()

        try:
            self.status_changed.emit("connecting", "Initializing ZORIN Central Brain...")

            print("\n==============================")
            print("       ZORIN STARTING")
            print("==============================")

            # ---------------------------------------------
            # AUTOMATIC DEVICE REGISTRATION
            # ---------------------------------------------
            registration_thread = threading.Thread(
                target=register_current_device,
                name="zorin-device-registration",
                daemon=True
            )
            registration_thread.start()
            print("ZORIN: Device registration started in background.")

            # ---------------------------------------------
            # WAKE WORD DETECTOR
            # ---------------------------------------------
            try:
                saved_mic, saved_spk = AudioManager.get_saved_devices()
                wake_detector = WakeWordDetector(device=saved_mic)
            except Exception as e:
                print(f"Wake word detector notice: {e}")
                wake_detector = None

            # ---------------------------------------------
            # BACKGROUND MEMORY WORKER
            # ---------------------------------------------
            memory_worker = MemoryQueueWorker(self.memory_manager, interval=30)
            memory_worker_task = asyncio.create_task(
                memory_worker.run(),
                name="zorin-memory-worker"
            )
            print("ZORIN: Background memory processing enabled.")

            # ---------------------------------------------
            # LOAD EXISTING MEMORY
            # ---------------------------------------------
            memory_context = self.load_memory_context(self.memory_manager)

            # ---------------------------------------------
            # INITIAL GEMINI CONNECTION
            # ---------------------------------------------
            ai = GeminiLive(
                memory_context=memory_context,
                voice_name=get_voice_preference()
            )
            connection_task = asyncio.create_task(
                ai.connect(),
                name="zorin-gemini-connect"
            )

            # ---------------------------------------------
            # MAIN VOICE / INTERACTION LOOP
            # ---------------------------------------------
            while not self.stop_requested.is_set():
                self.conversation_running = False
                self.voice_state_changed.emit(False)
                self.status_changed.emit(
                    "idle",
                    "Say 'Hey Zorin' or click 🎙️ to speak."
                )

                if wake_detector:
                    trigger_source = await self._wait_for_trigger(wake_detector)
                else:
                    # Fallback if wake word model unavailable: wait for manual click
                    loop = asyncio.get_running_loop()
                    manual_event = asyncio.Event()

                    def check_m():
                        if self.manual_voice_requested.is_set():
                            self.manual_voice_requested.clear()
                            manual_event.set()
                        elif not self.stop_requested.is_set():
                            loop.call_later(0.1, check_m)

                    check_m()
                    await manual_event.wait()
                    trigger_source = "manual"

                if self.stop_requested.is_set():
                    break

                # Prepare session
                self.status_changed.emit(
                    "connecting",
                    f"{'Microphone activated' if trigger_source == 'manual' else 'Wake word detected'}! Connecting to Gemini Live..."
                )

                # Wait for pending connection
                if connection_task:
                    try:
                        connected = await connection_task
                    except asyncio.CancelledError:
                        raise
                    except Exception as error:
                        print("Gemini connection error:", repr(error))
                        connected = False
                    connection_task = None

                if self.stop_requested.is_set():
                    break

                # Apply voice preference if changed
                selected_voice = get_voice_preference()
                if ai and ai.voice_name != selected_voice:
                    await ai.disconnect()
                    ai = GeminiLive(
                        memory_context=memory_context,
                        voice_name=selected_voice
                    )
                    connection_task = asyncio.create_task(
                        ai.connect(),
                        name="zorin-gemini-voice-connect"
                    )
                    try:
                        await connection_task
                    except Exception as error:
                        print("Voice-change connection error:", repr(error))
                    connection_task = None

                # Refresh persistent context
                latest_memory_context = self.load_memory_context(self.memory_manager)
                if ai:
                    ai.memory_context = latest_memory_context

                # -----------------------------------------
                # START VOICE CONVERSATION
                # -----------------------------------------
                saved_mic, saved_spk = AudioManager.get_saved_devices()
                conversation = VoiceConversation(
                    ai=ai,
                    on_status=self.status_changed.emit,
                    on_message=self.message_received.emit,
                    on_voice_changed=self.voice_changed.emit,
                    input_device=saved_mic,
                    output_device=saved_spk
                )

                self.active_conversation = conversation
                self.conversation_running = True
                self.voice_state_changed.emit(True)

                try:
                    await conversation.start()
                finally:
                    self.active_conversation = None
                    self.conversation_running = False
                    self.voice_state_changed.emit(False)

                if self.stop_requested.is_set():
                    break

                self.status_changed.emit(
                    "idle",
                    "ZORIN is on standby."
                )

                # Prepare fresh Gemini connection for next session
                memory_context = self.load_memory_context(self.memory_manager)
                ai = GeminiLive(
                    memory_context=memory_context,
                    voice_name=get_voice_preference()
                )
                connection_task = asyncio.create_task(
                    ai.connect(),
                    name="zorin-gemini-connect"
                )

        finally:
            print("\nZORIN: Beginning controlled shutdown...")

            if memory_worker:
                try:
                    memory_worker.stop()
                except Exception as error:
                    print("Memory worker stop error:", repr(error))

            if memory_worker_task and not memory_worker_task.done():
                memory_worker_task.cancel()
                try:
                    await asyncio.gather(memory_worker_task, return_exceptions=True)
                except Exception:
                    pass

            if connection_task and not connection_task.done():
                connection_task.cancel()
                try:
                    await asyncio.gather(connection_task, return_exceptions=True)
                except Exception:
                    pass

            if ai:
                try:
                    await ai.disconnect()
                except Exception as error:
                    print("Gemini disconnect error:", repr(error))

            if wake_detector:
                try:
                    await wake_detector.microphone.stop()
                except Exception as error:
                    print("Wake microphone cleanup error:", repr(error))

            print("\nZORIN: Shutdown completed.")

    # -----------------------------------------------------
    # EXTERNAL CONTROLS (THREAD-SAFE)
    # -----------------------------------------------------

    def toggle_voice(self):
        """Toggle voice session: starts if standby, stops if active."""
        if self.conversation_running and self.active_conversation:
            print("\nZORIN: User requested STOP voice session.")
            self.active_conversation.stop()
        else:
            print("\nZORIN: User requested START voice session via manual mic button.")
            self.manual_voice_requested.set()

    def stop(self):
        self.stop_requested.set()
        if self.conversation_running and self.active_conversation:
            self.active_conversation.stop()

        loop = self.loop
        task = self.main_task
        if loop is None or task is None:
            return

        try:
            if loop.is_running() and not loop.is_closed():
                loop.call_soon_threadsafe(task.cancel)
        except RuntimeError as error:
            print("ZORIN stop request:", repr(error))


# =========================================================
# ZORIN CONTROLLER
# =========================================================

class ZorinController(QObject):

    ui_add_message = Signal(str, str)
    ui_update_status = Signal(str, str)

    def __init__(self, window: ZorinWindow):
        super().__init__()
        self.window = window
        self.worker: Optional[ZorinWorker] = None
        self.closing_application = False
        self.current_user_id = get_default_user_id()
        self.current_user_profile = get_user_by_id(self.current_user_id) or {
            "user_id": self.current_user_id,
            "display_name": "Niharika",
            "voice_preference": "Aoede"
        }

        self.close_guard = ApplicationCloseGuard(window, self)
        self.window.installEventFilter(self.close_guard)

        # Wire window signals
        self.window.stop_requested.connect(self.stop_zorin)
        self.window.voice_toggle_requested.connect(self.toggle_voice)
        self.window.text_submitted.connect(self.handle_text_input)
        self.window.conversation_switched.connect(self.handle_conversation_switched)
        self.window.new_conversation_requested.connect(self.handle_new_conversation)

        # Connect internal cross-thread UI updates
        self.ui_add_message.connect(self.window.add_message)
        self.ui_update_status.connect(self.window.update_status)

        # Periodic real device polling (Never fabricated)
        self.device_poll_timer = QTimer(self)
        self.device_poll_timer.timeout.connect(self.refresh_connected_devices)
        self.device_poll_timer.start(8000)  # poll every 8 seconds

        # Initial device refresh after short delay
        QTimer.singleShot(400, self.refresh_connected_devices)

        # Start assistant background worker
        QTimer.singleShot(500, self.start_zorin)

    # -----------------------------------------------------
    # REAL CONNECTED DEVICE MONITORING
    # -----------------------------------------------------

    def refresh_connected_devices(self):
        try:
            from backend.client import register_current_device
            register_current_device()
            devices = get_all_devices()
            self.window.update_device_badge(devices, server_online=True)
            if self.window.device_dashboard is not None and self.window.device_dashboard.isVisible():
                self.window.device_dashboard.refresh_all()
        except Exception as e:
            print("Device refresh error:", e)
            self.window.update_device_badge([], server_online=False)

    # -----------------------------------------------------
    # START / STOP
    # -----------------------------------------------------

    def start_zorin(self):
        if self.closing_application:
            return
        if self.worker and self.worker.isRunning():
            return

        self.worker = ZorinWorker()
        self.worker.status_changed.connect(self.window.update_status)
        self.worker.message_received.connect(self.window.add_message)
        self.worker.voice_changed.connect(self.window.set_voice_selection)
        self.worker.voice_state_changed.connect(self.window.set_voice_active)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def toggle_voice(self):
        if self.worker and self.worker.isRunning():
            self.worker.toggle_voice()
        else:
            self.start_zorin()

    def stop_zorin(self):
        if self.worker and self.worker.isRunning():
            self.window.update_status("connecting", "Stopping ZORIN safely...")
            self.worker.stop()
        elif self.closing_application:
            self.finish_application_close()

    # -----------------------------------------------------
    # TEXT INPUT PROCESSING (AI ASSISTANT & TOOLS)
    # -----------------------------------------------------

    def handle_text_input(self, text: str):
        if not text.strip():
            return

        # Display user message bubble
        self.window.add_message("YOU", text)

        # Process in separate background thread to keep Qt UI completely fluid
        threading.Thread(
            target=self._process_text_message,
            args=(text.strip(),),
            name="zorin-text-processor",
            daemon=True
        ).start()

    def _process_text_message(self, message: str):
        self.ui_update_status.emit("thinking", "ZORIN is processing your request...")
        conv_id = getattr(self.window, "active_conversation_id", None) or f"conv_{self.current_user_id[:8]}"

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            res = loop.run_until_complete(
                assistant_service.chat(
                    user_id=self.current_user_id,
                    user_profile=self.current_user_profile,
                    message=message,
                    conversation_id=str(conv_id)
                )
            )
            loop.close()

            reply = res.get("text", "I have processed your request.")
            self.ui_add_message.emit("ZORIN", reply)
            self.ui_update_status.emit("idle", "Ready for next message or voice command.")

            # Refresh conversation drawer so new message count shows
            QTimer.singleShot(300, self.window.load_conversations)

        except Exception as error:
            print("Text processing error:", error)
            self.ui_add_message.emit("ZORIN", f"Error processing command: {error}")
            self.ui_update_status.emit("idle", "Something went wrong.")

    def handle_conversation_switched(self, conversation_id: int):
        print(f"ZORIN: Switched to conversation #{conversation_id}")
        if self.worker and self.worker.memory_manager:
            self.worker.memory_manager.current_conversation_id = conversation_id

    def handle_new_conversation(self):
        print("ZORIN: Reset to new conversation thread.")
        if self.worker and self.worker.memory_manager:
            self.worker.memory_manager.current_conversation_id = None

    # -----------------------------------------------------
    # APPLICATION CLOSE
    # -----------------------------------------------------

    def request_application_close(self):
        if self.closing_application:
            return
        self.closing_application = True
        print("\nZORIN: Application close requested.")

        if self.worker and self.worker.isRunning():
            self.window.update_status("connecting", "Closing ZORIN safely. Please wait...")
            self.worker.stop()
        else:
            self.finish_application_close()

    def finish_application_close(self):
        if self.worker and self.worker.isRunning():
            return
        self.close_guard.allow_close = True
        self.window.close()

    def show_error(self, message):
        print("\nZORIN ERROR:", message)
        if not self.closing_application:
            self.window.update_status("idle", "Something went wrong. Check terminal.")

    def on_worker_finished(self):
        print("\nZORIN: Background worker has stopped.")
        self.window.update_status("idle", "ZORIN is offline.")
        if self.closing_application:
            self.finish_application_close()


# =========================================================
# APPLICATION ENTRY POINT
# =========================================================

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    window = ZorinWindow()
    controller = ZorinController(window)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
