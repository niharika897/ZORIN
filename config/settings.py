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
WAKE_WORD = "Hey"

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
