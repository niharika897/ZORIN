import asyncio
import json
from typing import Optional
from vosk import Model, KaldiRecognizer

from voice.audio_input import MicrophoneInput
from config.settings import WAKE_WORD


class WakeWordDetector:
    """
    Local offline wake-word detector using Vosk speech recognition.
    Configured to recognize 'Hey Zorin' as well as friendly short triggers.
    """

    def __init__(self, device: Optional[int] = None):
        print("Loading ZORIN speech recognition (Vosk)...")

        self.model = Model("models/vosk-model-small-en-us-0.15")

        # Allow words for 'Hey Zorin' wake phrase
        allowed_grammar = [
            "hey zorin",
            "hey",
            "zorin",
            "zoran",
            "soren",
            "hi zorin",
            "hi",
            "[unk]"
        ]

        self.recognizer = KaldiRecognizer(
            self.model,
            16000,
            json.dumps(allowed_grammar)
        )

        self.microphone = MicrophoneInput(device=device)
        print(f"ZORIN wake-word engine ready! Configured trigger: '{WAKE_WORD}'")

    async def listen(self) -> bool:
        """
        Listens continuously on the microphone until the wake word is detected.
        Automatically stops and cleans up the microphone stream on exit.
        """
        print(f"\nZORIN IS WAITING ON STANDBY...")
        print(f"Say: '{WAKE_WORD}' (or 'Hey' / 'Zorin')")

        await self.microphone.start()

        try:
            while True:
                audio_data = await self.microphone.read()

                if self.recognizer.AcceptWaveform(audio_data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").lower().strip()

                    if text:
                        print("Wake Listener Heard:", text)

                    # Trigger condition: 'hey zorin', 'zorin', or 'hey' / 'hi'
                    if any(trigger in text for trigger in ["hey zorin", "zorin", "hey", "hi", "soren"]):
                        print(f"\n🚀 ZORIN ACTIVATED by wake trigger: '{text}'!")
                        self.recognizer.Reset()
                        return True
        finally:
            await self.microphone.stop()
            self.recognizer.Reset()
