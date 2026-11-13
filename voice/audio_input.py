import asyncio
from typing import Optional, List, Dict, Any
import numpy as np
import sounddevice as sd

from config.settings import INPUT_SAMPLE_RATE


class MicrophoneInput:
    """
    Robust microphone input capture with thread-safe queueing,
    dynamic device selection, resampling to 16kHz, and real-time RMS calculation.
    """

    def __init__(self, device: Optional[int] = None):
        # Default device is None (system default) unless explicitly specified
        self.device = device
        self.capture_rate = 44100

        self.stream: Optional[sd.InputStream] = None
        self.audio_queue: Optional[asyncio.Queue] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

        self.is_recording = False
        self._last_rms = 0.0

    def set_device(self, device_index: Optional[int]):
        """Change microphone capture device."""
        if self.device != device_index:
            self.device = device_index
            if self.is_recording:
                # If currently active, restart on new device
                asyncio.create_task(self._restart_stream())

    async def _restart_stream(self):
        await self.stop()
        await self.start()

    def _audio_callback(self, indata, frames, time_info, status):
        """Processes raw microphone input frames from PortAudio."""
        if status:
            pass  # Suppress benign status underflows

        if not self.is_recording:
            return

        loop = self.loop
        if loop is None or loop.is_closed():
            return

        try:
            # Convert multi-channel input to mono int16
            mono_audio = np.mean(indata.astype(np.int32), axis=1).astype(np.int16)

            # Calculate RMS energy for VAD / barge-in detection
            if len(mono_audio) > 0:
                self._last_rms = float(np.sqrt(np.mean(mono_audio.astype(np.float32) ** 2)))

            # Resample from capture_rate (44100) to INPUT_SAMPLE_RATE (16000)
            old_positions = np.arange(len(mono_audio))
            new_length = round(len(mono_audio) * INPUT_SAMPLE_RATE / self.capture_rate)

            new_positions = np.arange(new_length) * self.capture_rate / INPUT_SAMPLE_RATE
            converted_audio = np.interp(new_positions, old_positions, mono_audio).astype(np.int16)

            audio_data = converted_audio.tobytes()

            loop.call_soon_threadsafe(self._add_audio, audio_data)

        except (RuntimeError, ValueError):
            pass
        except Exception as error:
            print("Microphone callback error:", error)

    def _add_audio(self, audio_data: bytes):
        if not self.is_recording or self.audio_queue is None:
            return

        try:
            if self.audio_queue.full():
                # Discard oldest chunk to keep queue fresh without unbounded delay
                self.audio_queue.get_nowait()
            self.audio_queue.put_nowait(audio_data)
        except (asyncio.QueueEmpty, asyncio.QueueFull):
            pass
        except Exception as error:
            print("Audio queue error:", error)

    @property
    def current_rms(self) -> float:
        """Returns the most recent audio RMS energy measured from the microphone."""
        return self._last_rms

    async def start(self):
        """Starts capturing audio from the microphone."""
        if self.is_recording:
            return

        self.loop = asyncio.get_running_loop()
        self.audio_queue = asyncio.Queue(maxsize=150)

        # Check default device if self.device is None
        try:
            # 4410 blocksize at 44.1kHz = 100ms per block
            self.stream = sd.InputStream(
                device=self.device,
                samplerate=self.capture_rate,
                channels=2,
                dtype="int16",
                callback=self._audio_callback,
                blocksize=4410,
            )
            self.is_recording = True
            self.stream.start()
            print(f"ZORIN microphone activated on device: {self.device if self.device is not None else 'Default'}")
        except Exception as error:
            print(f"Microphone initialization failed on device {self.device}: {error}")
            # Try fallback to default device
            if self.device is not None:
                print("Attempting fallback to default system microphone...")
                self.device = None
                try:
                    self.stream = sd.InputStream(
                        device=None,
                        samplerate=self.capture_rate,
                        channels=2,
                        dtype="int16",
                        callback=self._audio_callback,
                        blocksize=4410,
                    )
                    self.is_recording = True
                    self.stream.start()
                    print("ZORIN microphone activated on default fallback device.")
                    return
                except Exception as fallback_err:
                    print("Fallback microphone also failed:", fallback_err)

            await self.stop()
            raise

    async def read(self) -> bytes:
        """Reads a chunk of 16kHz mono PCM audio."""
        if not self.is_recording:
            raise RuntimeError("Microphone is not running.")
        if self.audio_queue is None:
            raise RuntimeError("Microphone audio queue is unavailable.")
        return await self.audio_queue.get()

    async def stop(self):
        """Stops capturing audio and cleans up resources."""
        self.is_recording = False
        stream = self.stream
        self.stream = None

        if stream is not None:
            try:
                if stream.active:
                    stream.stop()
            except Exception as error:
                print("Microphone stop warning:", error)
            try:
                stream.close()
            except Exception as error:
                print("Microphone close warning:", error)

        if self.audio_queue is not None:
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        self.audio_queue = None
        self.loop = None
        print("ZORIN microphone stopped.")

    @staticmethod
    def list_devices() -> List[Dict[str, Any]]:
        """Returns a list of available audio input devices."""
        devices = sd.query_devices()
        input_devices = []
        for index, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                input_devices.append({
                    "index": index,
                    "name": device["name"],
                    "channels": device["max_input_channels"],
                    "default_samplerate": device["default_samplerate"]
                })
        return input_devices
