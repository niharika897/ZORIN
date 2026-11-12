import sys
import asyncio

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, Signal, QTimer

from desktop.modern_ui import ZorinWindow
from voice.wake_word import WakeWordDetector
from core.voice_conversation import VoiceConversation
from intelligence.gemini_live import GeminiLive


class ZorinWorker(QThread):

    status_changed = Signal(str, str)
    message_received = Signal(str, str)
    error_occurred = Signal(str)

    def run(self):
        try:
            asyncio.run(self.run_assistant())

        except asyncio.CancelledError:
            pass

        except Exception as error:
            self.error_occurred.emit(str(error))

    async def run_assistant(self):

        self.loop = asyncio.get_running_loop()
        self.main_task = asyncio.current_task()

        wake_detector = None
        ai = None
        connection_task = None

        try:

            self.status_changed.emit(
                "connecting",
                "Initializing ZORIN..."
            )

            wake_detector = WakeWordDetector()

            ai = GeminiLive()

            connection_task = asyncio.create_task(
                ai.connect()
            )

            while True:

                self.status_changed.emit(
                    "idle",
                    "Say Hey or Hi to wake me."
                )

                await wake_detector.listen()

                self.status_changed.emit(
                    "connecting",
                    "Wake word detected! Preparing ZORIN..."
                )

                if connection_task:

                    connected = await connection_task
                    connection_task = None

                    if not connected:
                        print("Gemini will reconnect when needed.")

                conversation = VoiceConversation(
                    ai=ai,
                    on_status=self.status_changed.emit,
                    on_message=self.message_received.emit
                )

                await conversation.start()

                self.status_changed.emit(
                    "idle",
                    "ZORIN is returning to standby..."
                )

                ai = GeminiLive()

                connection_task = asyncio.create_task(
                    ai.connect()
                )

        finally:

            if connection_task and not connection_task.done():

                connection_task.cancel()

                await asyncio.gather(
                    connection_task,
                    return_exceptions=True
                )

            if ai:
                await ai.disconnect()

            if wake_detector:
                await wake_detector.microphone.stop()

    def stop(self):

        if hasattr(self, "loop") and hasattr(self, "main_task"):

            self.loop.call_soon_threadsafe(
                self.main_task.cancel
            )


class ZorinController:

    def __init__(self, window):

        self.window = window
        self.worker = None

        self.window.stop_requested.connect(
            self.stop_zorin
        )

        QTimer.singleShot(
            300,
            self.start_zorin
        )

    def start_zorin(self):

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

    def stop_zorin(self):

        if self.worker and self.worker.isRunning():

            self.window.update_status(
                "connecting",
                "Stopping ZORIN..."
            )

            self.worker.stop()

    def show_error(self, message):

        self.window.update_status(
            "idle",
            "Something went wrong. Check the terminal."
        )

        print("\nZORIN ERROR:", message)

    def on_worker_finished(self):

        self.window.update_status(
            "idle",
            "ZORIN is offline."
        )

        self.worker = None


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = ZorinWindow()
    controller = ZorinController(window)

    window.show()

    sys.exit(app.exec())