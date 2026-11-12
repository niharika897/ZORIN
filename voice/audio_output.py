import sounddevice as sd
import numpy as np
import queue
import threading

from config.settings import OUTPUT_SAMPLE_RATE, AUDIO_CHANNELS


class AudioOutput:

    def __init__(self, device=None):

        self.device = device
        self.sample_rate = OUTPUT_SAMPLE_RATE
        self.stream = None

        self.audio_queue = queue.Queue()
        self.current_audio = None
        self.position = 0

        self.lock = threading.Lock()

    def start_stream(self):

        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=AUDIO_CHANNELS,
            dtype="int16",
            device=self.device,
            blocksize=480,
            callback=self.audio_callback
        )

        self.stream.start()

        print("ZORIN speaker activated!")

    def audio_callback(self, outdata, frames, time_info, status):

        outdata.fill(0)

        with self.lock:

            written = 0

            while written < frames:

                if self.current_audio is None:

                    try:
                        self.current_audio = self.audio_queue.get_nowait()
                        self.position = 0

                    except queue.Empty:
                        break

                remaining = len(self.current_audio) - self.position

                count = min(frames - written, remaining)

                outdata[written:written + count] = (
                    self.current_audio[
                        self.position:self.position + count
                    ]
                )

                written += count
                self.position += count

                if self.position >= len(self.current_audio):

                    self.current_audio = None
                    self.position = 0

    def play_chunk(self, audio_data):

        audio = np.frombuffer(
            audio_data,
            dtype=np.int16
        ).reshape(-1, AUDIO_CHANNELS).copy()

        with self.lock:
            self.audio_queue.put(audio)

    def stop(self):

        with self.lock:

            while not self.audio_queue.empty():

                try:
                    self.audio_queue.get_nowait()

                except queue.Empty:
                    break

            self.current_audio = None
            self.position = 0

        print("ZORIN voice playback interrupted!")

    def stop_stream(self):

        if self.stream:

            self.stream.stop()
            self.stream.close()
            self.stream = None

            print("ZORIN speaker stopped!")

    def play(self, audio_data):

        audio = np.frombuffer(
            audio_data,
            dtype=np.int16
        ).reshape(-1, AUDIO_CHANNELS)

        sd.play(
            audio,
            samplerate=self.sample_rate,
            device=self.device
        )

        sd.wait()

    @staticmethod
    def list_devices():

        devices = sd.query_devices()

        print("\nAvailable audio output devices:\n")

        for index, device in enumerate(devices):

            if device["max_output_channels"] > 0:

                print(f"{index}: {device['name']}")