import json
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
import sounddevice as sd

from config.settings import DATA_DIR

AUDIO_CONFIG_FILE = DATA_DIR / "audio_devices.json"


class AudioManager:
    """
    Manages physical audio endpoints, Bluetooth peripherals,
    and user-configured audio routing for ZORIN voice processing.
    """

    @staticmethod
    def get_devices() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Returns lists of available microphone and speaker hardware devices."""
        devices = sd.query_devices()
        microphones = []
        speakers = []

        for index, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                is_bt = any(term in device["name"].lower() for term in ["bluetooth", "hands-free", "headset", "buds"])
                microphones.append({
                    "id": index,
                    "name": device["name"],
                    "channels": device["max_input_channels"],
                    "is_bluetooth": is_bt,
                    "default_samplerate": device["default_samplerate"]
                })

            if device["max_output_channels"] > 0:
                is_bt = any(term in device["name"].lower() for term in ["bluetooth", "headphone", "headset", "buds", "speaker"])
                speakers.append({
                    "id": index,
                    "name": device["name"],
                    "channels": device["max_output_channels"],
                    "is_bluetooth": is_bt,
                    "default_samplerate": device["default_samplerate"]
                })

        return microphones, speakers

    @staticmethod
    def get_default_devices() -> Tuple[Optional[int], Optional[int]]:
        """Returns the current system default input and output device IDs."""
        try:
            mic = sd.default.device[0]
            speaker = sd.default.device[1]
            return (mic if mic >= 0 else None), (speaker if speaker >= 0 else None)
        except Exception:
            return None, None

    @staticmethod
    def get_saved_devices() -> Tuple[Optional[int], Optional[int]]:
        """Loads user-selected audio device routing from disk."""
        if not AUDIO_CONFIG_FILE.exists():
            return AudioManager.get_default_devices()

        try:
            with AUDIO_CONFIG_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("input_device"), data.get("output_device")
        except Exception as e:
            print(f"Error loading audio config: {e}")
            return AudioManager.get_default_devices()

    @staticmethod
    def save_audio_devices(mic_id: Optional[int], speaker_id: Optional[int]):
        """Persists selected audio routing preferences."""
        AUDIO_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with AUDIO_CONFIG_FILE.open("w", encoding="utf-8") as f:
                json.dump({
                    "input_device": mic_id,
                    "output_device": speaker_id
                }, f, indent=4)
            print(f"ZORIN: Saved audio routing -> Mic: {mic_id}, Speaker: {speaker_id}")
        except Exception as e:
            print(f"Error saving audio config: {e}")

    @staticmethod
    def show_devices():
        microphones, speakers = AudioManager.get_devices()
        print("\n===== ZORIN AUDIO DEVICES =====")
        print("\nAVAILABLE MICROPHONES:")
        for mic in microphones:
            print(f"{mic['id']}: {mic['name']} {'[Bluetooth]' if mic['is_bluetooth'] else ''}")
        print("\nAVAILABLE SPEAKERS:")
        for spk in speakers:
            print(f"{spk['id']}: {spk['name']} {'[Bluetooth]' if spk['is_bluetooth'] else ''}")
        print("===============================\n")


if __name__ == "__main__":
    AudioManager.show_devices()
