import os
from pathlib import Path
from dotenv import load_dotenv

# Locate the main project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# AI model configuration
GEMINI_MODEL =  "gemini-3.1-flash-live-preview"

# ZORIN identity
ASSISTANT_NAME = "ZORIN"
WAKE_WORD = "Hey Zorin"

# Audio configuration
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
AUDIO_CHANNELS = 1

# Project directories
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

# Create required directories
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)


# Persistent voice preference (survives application restarts)
VOICE_SETTINGS_FILE = DATA_DIR / "voice_settings.json"

VOICE_OPTIONS = {
    "male": "Puck",
    "female": "Aoede",
}


def get_voice_preference():
    """Return the saved Gemini voice name, defaulting to the female voice (Aoede)."""
    import json

    try:
        if VOICE_SETTINGS_FILE.exists():
            with VOICE_SETTINGS_FILE.open("r", encoding="utf-8") as file:
                saved = json.load(file)

            voice_name = saved.get("voice_name")
            if voice_name in VOICE_OPTIONS.values():
                return voice_name
    except (OSError, ValueError, TypeError):
        pass

    return VOICE_OPTIONS["female"]


def set_voice_preference(voice):
    """Save a voice choice; accepts 'male', 'female', 'Puck' or 'Aoede'."""
    import json

    normalized = str(voice).strip().lower()

    if normalized in VOICE_OPTIONS:
        voice_name = VOICE_OPTIONS[normalized]
    elif voice in VOICE_OPTIONS.values():
        voice_name = voice
    else:
        raise ValueError("Voice must be male/Puck or female/Aoede.")

    VOICE_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = VOICE_SETTINGS_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(
            {"voice_name": voice_name},
            file,
            indent=4
        )

    temporary_file.replace(VOICE_SETTINGS_FILE)
    return voice_name


def get_voice_gender(voice_name=None):
    """Return the friendly gender label for a Gemini voice name."""
    voice_name = voice_name or get_voice_preference()
    return "female" if voice_name == VOICE_OPTIONS["female"] else "male"


def validate_settings():
	"""Check whether essential configuration is available."""

	if not GEMINI_API_KEY:
		raise ValueError(
			"GEMINI_API_KEY is missing. Check your .env file."
		)

	print("ZORIN configuration loaded successfully!")
	print(f"Assistant: {ASSISTANT_NAME}")
	print(f"AI Model: {GEMINI_MODEL}")
	print(f"Wake Word: {WAKE_WORD}")


if __name__ == "__main__":
	validate_settings()
