import os
import sys
import numpy as np
from voice.audio_output import AudioOutput
from core.voice_conversation import VoiceConversation, ConversationState

def main():
    print("=" * 60, flush=True)
    print("  ZORIN VOICE SYSTEM & REAL-TIME BARGE-IN TESTS", flush=True)
    print("=" * 60, flush=True)

    # 1. TEST AUDIO OUTPUT GENERATION TRACKING
    speaker = AudioOutput()
    gen1 = speaker.current_generation_id
    print(f"[TEST 1] Initial Generation ID: {gen1}", flush=True)

    dummy_audio = np.zeros(2400, dtype=np.int16).tobytes()

    # Queue chunk for gen1
    speaker.play_chunk(dummy_audio, generation_id=gen1)
    assert not speaker.audio_queue.empty(), "Audio queue should contain gen1 chunk"
    print("  ✓ Gen1 chunk queued successfully.", flush=True)

    # Trigger interruption (advance generation & stop)
    speaker.stop()
    gen2 = speaker.current_generation_id
    assert gen2 == gen1 + 1, f"Expected gen {gen1+1}, got {gen2}"
    assert speaker.audio_queue.empty(), "Audio queue should be emptied upon stop()"
    print(f"  ✓ Barge-in advanced generation to: {gen2} and cleared queue.", flush=True)

    # Attempt to play an obsolete/trailing chunk from gen1
    speaker.play_chunk(dummy_audio, generation_id=gen1)
    assert speaker.audio_queue.empty(), "Stale chunk from older generation must be discarded"
    print("  ✓ Obsolete chunk from older generation was discarded immediately.", flush=True)

    # Play valid chunk from new generation
    speaker.play_chunk(dummy_audio, generation_id=gen2)
    assert not speaker.audio_queue.empty(), "Valid chunk for current generation should be queued"
    print("  ✓ Valid chunk for current generation accepted.", flush=True)
    speaker.stop()

    # 2. TEST VOICE CONVERSATION STATE MACHINE & BARGE-IN
    conv = VoiceConversation()
    status_log = []
    conv.on_status = lambda s, d: status_log.append((s, d))

    print("\n[TEST 2] Testing Conversation State Transitions:", flush=True)
    conv.set_state(ConversationState.LISTENING, "Listening for user...")
    assert conv.state == ConversationState.LISTENING
    print("  ✓ State: LISTENING", flush=True)

    conv.set_state(ConversationState.SPEAKING, "Speaking AI response...")
    assert conv.state == ConversationState.SPEAKING
    print("  ✓ State: SPEAKING", flush=True)

    # Simulate barge-in trigger
    conv.trigger_barge_in(reason="User voice detected")
    assert conv.state == ConversationState.INTERRUPTED
    print("  ✓ State: INTERRUPTED via barge-in", flush=True)
    assert conv.playback_queue.empty(), "Playback queue must be cleared on barge-in"
    print("  ✓ Playback queue purged on barge-in.", flush=True)

    # 3. TEST ACCURATE PHYSICAL PLAYBACK COMPLETION LOGIC
    print("\n[TEST 3] Testing is_playing() accuracy:", flush=True)
    assert not speaker.is_playing()
    print("  ✓ is_playing() accurately reports False when empty.", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("  🏆 ALL VOICE INTERRUPTION & PLAYBACK TESTS PASSED!", flush=True)
    print("=" * 60, flush=True)

    os._exit(0)

if __name__ == "__main__":
    main()
