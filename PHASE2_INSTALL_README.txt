ZORIN PHASE 2 — MALE/FEMALE VOICE SWITCHING

Included updated files:
- desktop/modern_ui.py
- desktop/app.py
- core/voice_conversation.py
- intelligence/gemini_live.py
- config/settings.py

What this update adds:
- A visible MALE VOICE / FEMALE VOICE selector in the ZORIN header.
- Male voice uses Gemini Live voice Puck.
- Female voice uses Gemini Live voice Aoede.
- The selected voice is saved in data/voice_settings.json and persists across restarts.
- Spoken commands: "Zorin, switch to male voice" and "Zorin, switch to female voice".
- Voice changes are applied by safely ending the current conversation and reconnecting for the next one.

INSTALLATION:
1. Close ZORIN completely.
2. Back up the five existing files before replacing them.
3. Extract this ZIP into the ZORIN project root (C:\Users\Niharika\ZORIN), preserving folder structure, and allow overwrite.
4. Start ZORIN normally.

The update does not include or change your .env file, API key, memory database, or conversation history.

VALIDATION:
All five updated Python files passed Python syntax parsing before packaging.
