ZORIN PHASE 3 - CONVERSATION QUALITY UPDATE

Included:
- intelligence/gemini_live.py

What changed:
- Improved spoken-response style and concision.
- Added explicit follow-up/context handling guidance.
- Added clarification rules for ambiguous references.
- Reduced repetitive greetings and unnecessary narration.
- Reinforced truthful tool/action reporting.
- Preserved existing model, voice preference, tools, memory context,
  connection lifecycle, and audio output code.

Important scope note:
This is the first safe Phase 3 implementation based on the source files
provided. The uploaded source collection did not include
memory/queue_worker.py, memory/extraction_queue.py, memory/memory_extractor.py,
voice/audio_input.py, or voice/audio_output.py. Therefore this update does
not modify memory retry/backoff or low-level audio latency behavior.

INSTALLATION:
1. Close ZORIN.
2. Extract this ZIP into C:\Users\Niharika\ZORIN and allow overwrite.
3. Run:
   .\.venv\Scripts\python.exe -m compileall intelligence\gemini_live.py
4. Run:
   python -m desktop.app

The install replaces only intelligence/gemini_live.py.
Make a backup before replacing it.
