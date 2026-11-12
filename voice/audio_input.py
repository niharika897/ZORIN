import asyncio
import sounddevice as sd
import numpy as np

from config.settings import INPUT_SAMPLE_RATE


class MicrophoneInput:

    def __init__(self, device=1):

        self.device = device
        self.capture_rate = 44100

        self.stream = None
        self.audio_queue = None
        self.loop = None

        self.is_recording = False

    def _audio_callback(self, indata, frames, time_info, status):

        if status:
            print("Microphone status:", status)

        if not self.is_recording:
            return

        loop = self.loop

        if loop is None:
            return

        try:

            mono_audio = np.mean(
                indata.astype(np.int32),
                axis=1
            ).astype(np.int16)

            old_positions = np.arange(len(mono_audio))

            new_length = round(
                len(mono_audio)
                * INPUT_SAMPLE_RATE
                / self.capture_rate
            )

            new_positions = (
                np.arange(new_length)
                * self.capture_rate
                / INPUT_SAMPLE_RATE
            )

            converted_audio = np.interp(
                new_positions,
                old_positions,
                mono_audio
            ).astype(np.int16)

            audio_data = converted_audio.tobytes()

            loop.call_soon_threadsafe(
                self._add_audio,
                audio_data
            )

        except RuntimeError:
            pass

        except Exception as error:
            print("Microphone callback error:", error)

    def _add_audio(self, audio_data):

        if not self.is_recording:
            return

        if self.audio_queue is None:
            return

        try:

            if self.audio_queue.full():
                self.audio_queue.get_nowait()

            self.audio_queue.put_nowait(audio_data)

        except asyncio.QueueEmpty:
            pass

        except asyncio.QueueFull:
            pass

        except Exception as error:
            print("Audio queue error:", error)

    async def start(self):

        if self.is_recording:
            return

        self.loop = asyncio.get_running_loop()

        self.audio_queue = asyncio.Queue(maxsize=100)

        try:

            self.stream = sd.InputStream(
                device=self.device,
                samplerate=self.capture_rate,
                channels=2,
                dtype="int16",
                callback=self._audio_callback,
                blocksize=4410
            )

            self.is_recording = True

            self.stream.start()

            print("ZORIN microphone activated!")

        except Exception as error:

            print("Microphone initialization failed:", error)

            await self.stop()

            raise

    async def read(self):

        if not self.is_recording:
            raise RuntimeError("Microphone is not running.")

        if self.audio_queue is None:
            raise RuntimeError("Microphone audio queue is unavailable.")

        return await self.audio_queue.get()

    async def stop(self):

        self.is_recording = False

        stream = self.stream
        self.stream = None

        if stream:

            try:
                if stream.active:
                    stream.stop()

            except Exception as error:
                print("Microphone stop warning:", error)

            try:
                stream.close()

            except Exception as error:
                print("Microphone close warning:", error)

        if self.audio_queue:

            while not self.audio_queue.empty():

                try:
                    self.audio_queue.get_nowait()

                except asyncio.QueueEmpty:
                    break

        self.audio_queue = None
        self.loop = None

        print("ZORIN microphone stopped.")