import queue
import threading
import time
from typing import Optional, List, Dict, Any
import numpy as np
import sounddevice as sd

from config.settings import OUTPUT_SAMPLE_RATE, AUDIO_CHANNELS


class AudioOutput:
    """
    High-performance audio output engine with generation tracking,
    instant barge-in interruption, and smooth callback streaming.
    """

    def __init__(self, device: Optional[int] = None):
        self.device = device
        self.sample_rate = OUTPUT_SAMPLE_RATE
        self.channels = AUDIO_CHANNELS
        self.stream: Optional[sd.OutputStream] = None

        self.audio_queue: queue.Queue = queue.Queue()
        self.current_audio: Optional[np.ndarray] = None
        self.position = 0

        self.lock = threading.Lock()
        self.current_generation_id = 0
        self._is_active = False

    def set_device(self, device_index: Optional[int]):
        """Change output audio device."""
        if self.device != device_index:
            self.device = device_index
            if self.stream is not None:
                self.stop_stream()
                self.start_stream()

    def start_stream(self):
        """Initializes and starts the non-blocking sounddevice output stream."""
        with self.lock:
            if self.stream is not None:
                return

            try:
                self.stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="int16",
                    device=self.device,
                    blocksize=480,
                    callback=self._audio_callback,
                )
                self.stream.start()
                self._is_active = True
                print(f"ZORIN speaker activated on device: {self.device or 'Default'}")
            except Exception as e:
                print(f"AudioOutput stream error: {e}")
                self.stream = None
                self._is_active = False
                raise

    def _audio_callback(self, outdata, frames, time_info, status):
        """Audio engine callback invoked by PortAudio."""
        outdata.fill(0)

        with self.lock:
            written = 0

            while written < frames:
                if self.current_audio is None:
                    try:
                        generation_id, audio_chunk = self.audio_queue.get_nowait()
                        # Discard stale chunk from a previous interrupted turn
                        if generation_id != self.current_generation_id:
                            continue
                        self.current_audio = audio_chunk
                        self.position = 0
                    except queue.Empty:
                        break

                remaining = len(self.current_audio) - self.position
                count = min(frames - written, remaining)

                outdata[written : written + count] = self.current_audio[
                    self.position : self.position + count
                ]

                written += count
                self.position += count

                if self.position >= len(self.current_audio):
                    self.current_audio = None
                    self.position = 0

    def play_chunk(self, audio_data: bytes, generation_id: Optional[int] = None):
        """
        Pushes an audio chunk into playback queue tagged with generation_id.
        Stale chunks from older generations are discarded immediately.
        """
        if not audio_data:
            return

        with self.lock:
            if generation_id is None:
                generation_id = self.current_generation_id
            elif generation_id != self.current_generation_id:
                # Obsolete response chunk arriving after interruption - drop
                return

            try:
                audio = np.frombuffer(audio_data, dtype=np.int16).reshape(-1, self.channels).copy()
                self.audio_queue.put((generation_id, audio))
            except Exception as e:
                print(f"Error buffering audio chunk: {e}")

    def is_playing(self) -> bool:
        """Returns True if audio is actively being played or queued for playback."""
        with self.lock:
            return self.current_audio is not None or not self.audio_queue.empty()

    def advance_generation(self) -> int:
        """
        Increments the generation ID to invalidate any queued or trailing in-flight audio.
        """
        with self.lock:
            self.current_generation_id += 1
            return self.current_generation_id

    def stop(self):
        """
        Immediately stops playback and purges all queued audio.
        Advances generation ID so trailing responses from network are ignored.
        """
        with self.lock:
            self.current_generation_id += 1
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break

            self.current_audio = None
            self.position = 0

        print("ZORIN voice playback interrupted & cleared.")

    def stop_stream(self):
        """Stops and closes the output stream."""
        self.stop()
        with self.lock:
            if self.stream is not None:
                try:
                    if self.stream.active:
                        self.stream.stop()
                    self.stream.close()
                except Exception as e:
                    print(f"Error stopping stream: {e}")
                finally:
                    self.stream = None
                    self._is_active = False
                    print("ZORIN speaker stopped.")

    @staticmethod
    def list_devices() -> List[Dict[str, Any]]:
        """Returns a list of available audio output devices."""
        devices = sd.query_devices()
        output_devices = []
        for index, device in enumerate(devices):
            if device["max_output_channels"] > 0:
                output_devices.append({
                    "index": index,
                    "name": device["name"],
                    "channels": device["max_output_channels"],
                    "default_samplerate": device["default_samplerate"]
                })
        return output_devices
