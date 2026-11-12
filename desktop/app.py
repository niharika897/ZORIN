import sys
import asyncio
import threading

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

from memory.memory_manager import MemoryManager
from memory.queue_worker import MemoryQueueWorker
from backend.client import register_current_device


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

    def __init__(self):

        super().__init__()

        self.loop = None
        self.main_task = None

        self.stop_requested = threading.Event()

    # -----------------------------------------------------
    # THREAD ENTRY
    # -----------------------------------------------------

    def run(self):

        try:

            asyncio.run(
                self.run_assistant()
            )

        except asyncio.CancelledError:

            pass

        except Exception as error:

            print("\nZORIN WORKER ERROR:", repr(error))

            self.error_occurred.emit(
                str(error)
            )

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

        saved_memories = (
            memory_manager.get_all_memories()
        )

        persistent_context = (
            memory_manager.get_persistent_memory_context()
        )

        past_conversations = (
            memory_manager.get_past_conversation_context(
                limit=30
            )
        )

        sections = []

        if persistent_context:

            sections.append(
                "PERSISTENT MEMORY:\n"
                + persistent_context
            )

        if past_conversations:

            sections.append(
                "RECENT PAST CONVERSATIONS:\n"
                + past_conversations
            )

        if not sections:

            print(
                "No saved memories or past conversations found."
            )

            return ""

        print(
            f"Loaded {len(saved_memories)} long-term memories."
        )

        if past_conversations:

            print(
                "Previous conversation history loaded."
            )

        return "\n\n".join(sections)

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

        memory_manager = MemoryManager()

        # Handle Stop pressed before the event loop was ready.
        if self.stop_requested.is_set():

            self.main_task.cancel()

        try:

            self.status_changed.emit(
                "connecting",
                "Initializing ZORIN..."
            )

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
            # WAKE WORD
            # ---------------------------------------------

            wake_detector = WakeWordDetector()

            # ---------------------------------------------
            # BACKGROUND MEMORY WORKER
            # ---------------------------------------------

            memory_worker = MemoryQueueWorker(
                memory_manager,
                interval=30
            )

            memory_worker_task = asyncio.create_task(
                memory_worker.run(),
                name="zorin-memory-worker"
            )

            print(
                "\nZORIN: Background memory processing enabled."
            )

            # ---------------------------------------------
            # LOAD EXISTING MEMORY
            # ---------------------------------------------

            memory_context = self.load_memory_context(
                memory_manager
            )

            # ---------------------------------------------
            # INITIAL GEMINI CONNECTION
            # ---------------------------------------------

            ai = GeminiLive(
                memory_context=memory_context
            )

            connection_task = asyncio.create_task(
                ai.connect(),
                name="zorin-gemini-connect"
            )

            # ---------------------------------------------
            # MAIN LOOP
            # ---------------------------------------------

            while not self.stop_requested.is_set():

                self.status_changed.emit(
                    "idle",
                    "Say Hey or Hi to wake me."
                )

                await wake_detector.listen()

                if self.stop_requested.is_set():
                    break

                self.status_changed.emit(
                    "connecting",
                    "Wake word detected! Preparing ZORIN..."
                )

                # Wait for the existing connection attempt.
                if connection_task:

                    try:

                        connected = await connection_task

                    except asyncio.CancelledError:
                        raise

                    except Exception as error:

                        print(
                            "Gemini connection error:",
                            repr(error)
                        )

                        connected = False

                    connection_task = None

                    if not connected:

                        print(
                            "Gemini connection was unsuccessful. "
                            "Conversation will attempt to reconnect."
                        )

                if self.stop_requested.is_set():
                    break

                # -----------------------------------------
                # START CONVERSATION
                # -----------------------------------------

                conversation = VoiceConversation(
                    ai=ai,
                    on_status=self.status_changed.emit,
                    on_message=self.message_received.emit
                )

                await conversation.start()

                if self.stop_requested.is_set():
                    break

                self.status_changed.emit(
                    "idle",
                    "ZORIN is returning to standby..."
                )

                # -----------------------------------------
                # REFRESH MEMORY CONTEXT
                # -----------------------------------------

                memory_context = self.load_memory_context(
                    memory_manager
                )

                # -----------------------------------------
                # PREPARE NEXT GEMINI SESSION
                # -----------------------------------------

                ai = GeminiLive(
                    memory_context=memory_context
                )

                connection_task = asyncio.create_task(
                    ai.connect(),
                    name="zorin-gemini-connect"
                )

        finally:

            print(
                "\nZORIN: Beginning controlled shutdown..."
            )

            # ---------------------------------------------
            # STOP MEMORY WORKER
            # ---------------------------------------------

            if memory_worker:

                try:

                    memory_worker.stop()

                except Exception as error:

                    print(
                        "Memory worker stop error:",
                        repr(error)
                    )

            if memory_worker_task:

                if not memory_worker_task.done():

                    memory_worker_task.cancel()

                try:

                    await asyncio.gather(
                        memory_worker_task,
                        return_exceptions=True
                    )

                except Exception as error:

                    print(
                        "Memory worker cleanup error:",
                        repr(error)
                    )

            # ---------------------------------------------
            # CANCEL PENDING GEMINI CONNECTION
            # ---------------------------------------------

            if connection_task:

                if not connection_task.done():

                    connection_task.cancel()

                try:

                    await asyncio.gather(
                        connection_task,
                        return_exceptions=True
                    )

                except Exception as error:

                    print(
                        "Gemini connection cleanup error:",
                        repr(error)
                    )

            # ---------------------------------------------
            # DISCONNECT GEMINI
            # ---------------------------------------------

            if ai:

                try:

                    await ai.disconnect()

                except Exception as error:

                    print(
                        "Gemini disconnect error:",
                        repr(error)
                    )

            # ---------------------------------------------
            # STOP WAKE WORD MICROPHONE
            # ---------------------------------------------

            if wake_detector:

                try:

                    await wake_detector.microphone.stop()

                except Exception as error:

                    print(
                        "Wake microphone cleanup error:",
                        repr(error)
                    )

            print(
                "\nZORIN: Shutdown completed."
            )

    # -----------------------------------------------------
    # THREAD-SAFE STOP
    # -----------------------------------------------------

    def stop(self):

        self.stop_requested.set()

        loop = self.loop
        task = self.main_task

        if loop is None or task is None:
            return

        try:

            if loop.is_running() and not loop.is_closed():

                loop.call_soon_threadsafe(
                    task.cancel
                )

        except RuntimeError as error:

            print(
                "ZORIN stop request:",
                repr(error)
            )


# =========================================================
# ZORIN CONTROLLER
# =========================================================

class ZorinController:

    def __init__(self, window):

        self.window = window

        self.worker = None

        self.closing_application = False

        self.close_guard = ApplicationCloseGuard(
            window,
            self
        )

        self.window.installEventFilter(
            self.close_guard
        )

        self.window.stop_requested.connect(
            self.stop_zorin
        )

        QTimer.singleShot(
            300,
            self.start_zorin
        )

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    def start_zorin(self):

        if self.closing_application:
            return

        if self.worker and self.worker.isRunning():
            return

        self.worker = ZorinWorker()

        self.worker.status_changed.connect(
            self.window.update_status
        )

        self.worker.message_received.connect(
            self.window.add_message
        )

        self.worker.error_occurred.connect(
            self.show_error
        )

        self.worker.finished.connect(
            self.on_worker_finished
        )

        self.worker.start()

    # -----------------------------------------------------
    # STOP BUTTON
    # -----------------------------------------------------

    def stop_zorin(self):

        if self.worker and self.worker.isRunning():

            self.window.update_status(
                "connecting",
                "Stopping ZORIN safely..."
            )

            self.worker.stop()

        elif self.closing_application:

            self.finish_application_close()

    # -----------------------------------------------------
    # APPLICATION CLOSE
    # -----------------------------------------------------

    def request_application_close(self):

        if self.closing_application:
            return

        self.closing_application = True

        print(
            "\nZORIN: Application close requested."
        )

        if self.worker and self.worker.isRunning():

            self.window.update_status(
                "connecting",
                "Closing ZORIN safely. Please wait..."
            )

            self.worker.stop()

        else:

            self.finish_application_close()

    def finish_application_close(self):

        if self.worker and self.worker.isRunning():
            return

        self.close_guard.allow_close = True

        self.window.close()

    # -----------------------------------------------------
    # ERRORS
    # -----------------------------------------------------

    def show_error(self, message):

        print(
            "\nZORIN ERROR:",
            message
        )

        if not self.closing_application:

            self.window.update_status(
                "idle",
                "Something went wrong. Check the terminal."
            )

    # -----------------------------------------------------
    # WORKER FINISHED
    # -----------------------------------------------------

    def on_worker_finished(self):

        print(
            "\nZORIN: Background worker has stopped."
        )

        self.window.update_status(
            "idle",
            "ZORIN is offline."
        )

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

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":

    main()