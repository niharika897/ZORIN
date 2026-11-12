import asyncio
import json

from vosk import Model, KaldiRecognizer

from voice.audio_input import MicrophoneInput


class WakeWordDetector:

    def __init__(self):

        print("Loading ZORIN speech recognition...")

        self.model = Model(
            "models/vosk-model-small-en-us-0.15"
        )

        self.recognizer = KaldiRecognizer(
            self.model,
            16000,
            json.dumps(["hey", "hi"])
        )

        self.microphone = MicrophoneInput()

        print("ZORIN speech recognition ready!")

    async def listen(self):

        print("\nZORIN IS WAITING...")
        print("Say: Hey or Hi")

        await self.microphone.start()

        try:

            while True:

                audio_data = await self.microphone.read()

                if self.recognizer.AcceptWaveform(audio_data):

                    result = json.loads(
                        self.recognizer.Result()
                    )

                    text = result.get(
                        "text", ""
                    ).lower().strip()

                    if text:
                        print("Heard:", text)

                    if text in ("hey", "hi"):

                        print("\nZORIN ACTIVATED!")

                        self.recognizer.Reset()

                        return True

        finally:

            await self.microphone.stop()
            self.recognizer.Reset()