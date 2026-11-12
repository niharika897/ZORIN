import asyncio
import os
import sys
import threading
import sqlite3
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.database import get_connection, DATABASE_PATH, initialize_database
from backend.auth import (
    register_user,
    authenticate_user,
    seed_default_user_if_needed,
    get_user_by_email,
    get_user_by_id
)
from backend.memory_service import central_memory_service, CoreMemoryProtectedError
from backend.client import ZorinBackendClient
from memory.memory_manager import MemoryManager
from core.tool_router import ToolRouter


def print_header(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def run_tests():
    print_header("RUNNING COMPLETE CENTRAL MEMORY TEST SUITE (10 SCENARIOS)")
    initialize_database()
    seed_default_user_if_needed()

    default_user = get_user_by_email("niharika@zorin.ai")
    assert default_user is not None, "Failed to get default user"
    uid = default_user["user_id"]
    auth_res = authenticate_user("niharika@zorin.ai", "password123")
    user_token = auth_res["token"]

    desktop_manager = MemoryManager(user_id=uid)
    android_client = ZorinBackendClient(user_token=user_token)

    # -------------------------------------------------------------
    # SCENARIO 1: Save a memory from desktop and retrieve from Android
    # -------------------------------------------------------------
    print_header("Scenario 1: Save from Desktop -> Retrieve from Android")
    desktop_fact = "My favourite colour is blue and I love stargazing."
    ok = desktop_manager.remember(desktop_fact, category="preference", importance=4)
    assert ok is True, "Desktop failed to save memory"
    print(f"  [Desktop] Saved memory: '{desktop_fact}'")

    # Android retrieves via central client
    android_memories = android_client.get_memories()
    contents = [m["content"] for m in android_memories]
    assert desktop_fact in contents, f"Android could not find desktop memory! Found: {contents}"
    print(f"  [Android] Successfully retrieved memory from central brain: '{desktop_fact}'")
    print("  -> Scenario 1 PASSED.")

    # -------------------------------------------------------------
    # SCENARIO 2: Save a memory from Android and retrieve from Desktop
    # -------------------------------------------------------------
    print_header("Scenario 2: Save from Android -> Retrieve from Desktop")
    android_fact = "I am planning a trip to Kyoto in October 2027."
    res = android_client.save_memory(category="travel", content=android_fact, importance=3, is_core=False)
    assert res.get("id") or res.get("memory", {}).get("id"), "Android client failed to save memory"
    print(f"  [Android] Saved memory: '{android_fact}'")

    # Desktop recalls
    desktop_recalled = desktop_manager.recall("Kyoto")
    assert len(desktop_recalled) > 0, "Desktop failed to recall memory saved by Android"
    assert desktop_recalled[0]["content"] == android_fact
    print(f"  [Desktop] Recalled Android memory: '{desktop_recalled[0]['content']}'")
    print("  -> Scenario 2 PASSED.")

    # -------------------------------------------------------------
    # SCENARIO 3: Save a memory from Web and retrieve from Desktop
    # -------------------------------------------------------------
    print_header("Scenario 3: Save from Web -> Retrieve from Desktop Context")
    web_fact = "User is the lead system architect for ZORIN AI."
    central_memory_service.save_memory(user_id=uid, category="work", content=web_fact, importance=4)
    print(f"  [Web] Saved memory: '{web_fact}'")

    # Desktop loads context for Gemini Live
    desktop_context = desktop_manager.get_persistent_memory_context()
    assert web_fact in desktop_context, "Web memory missing from desktop persistent context"
    print(f"  [Desktop] Context loaded successfully with Web memory included.")
    print("  -> Scenario 3 PASSED.")

    # -------------------------------------------------------------
    # SCENARIO 4: Delete normal memory and verify deleted across clients
    # -------------------------------------------------------------
    print_header("Scenario 4: Delete Normal Memory Across Clients")
    temp_fact = "Temporary grocery item: buy almond milk today."
    save_res = central_memory_service.save_memory(user_id=uid, category="temp", content=temp_fact, importance=1)
    temp_id = save_res["id"]
    print(f"  Saved temporary memory ID {temp_id}: '{temp_fact}'")

    # Delete via Android / central client
    deleted = android_client.delete_memory(temp_id, allow_core=False)
    assert deleted is True, "Failed to delete normal memory"
    print(f"  Deleted memory ID {temp_id} via central API.")

    # Verify Desktop cannot see it anymore
    desktop_all = [m["id"] for m in desktop_manager.get_all_memories()]
    assert temp_id not in desktop_all, "Deleted memory still appeared in Desktop list!"
    print(f"  [Desktop] Confirmed memory {temp_id} is completely removed.")
    print("  -> Scenario 4 PASSED.")

    # -------------------------------------------------------------
    # SCENARIO 5: Verify Core Memory Cannot Be Automatically Deleted
    # -------------------------------------------------------------
    print_header("Scenario 5: Core Memory Protection Verification")
    core_fact = "Emergency contact is Dr. Sarah Connor, Phone: +1-555-0199."
    ok = desktop_manager.remember_core(core_fact, category="personal", importance=5)
    assert ok is True
    core_items = [m for m in desktop_manager.get_core_memories() if m["content"] == core_fact]
    assert len(core_items) > 0, "Core memory not found after remember_core"
    core_id = core_items[0]["id"]
    print(f"  Created protected Core Memory ID {core_id}: '{core_fact}'")

    # Attempt automatic deletion (allow_core=False)
    try:
        central_memory_service.delete_memory(user_id=uid, memory_id=core_id, allow_core=False)
        assert False, "Core memory was deleted when allow_core=False! Protection failed!"
    except CoreMemoryProtectedError as e:
        print(f"  [BLOCKED] CoreMemoryProtectedError caught as expected: {e}")

    # Verify memory is still intact
    recheck = central_memory_service.get_memory_by_id(uid, core_id)
    assert recheck is not None, "Core memory was removed despite protection!"
    assert recheck["is_core"] == 1, "Core memory flag was corrupted"
    print(f"  Core memory {core_id} confirmed SAFE and PROTECTED in database.")

    # Explicit deletion by user (allow_core=True)
    explicit_del = central_memory_service.delete_memory(user_id=uid, memory_id=core_id, allow_core=True)
    assert explicit_del is True, "Explicit user delete should succeed with allow_core=True"
    print(f"  Explicit user deletion with allow_core=True succeeded.")
    print("  -> Scenario 5 PASSED.")

    # -------------------------------------------------------------
    # SCENARIO 6: Restart Backend and Verify Memories Persist
    # -------------------------------------------------------------
    print_header("Scenario 6: Backend Restart Persistence Verification")
    restart_fact = "Persistence verification key: 7729-ALPHA-OMEGA."
    central_memory_service.save_memory(user_id=uid, category="system", content=restart_fact, importance=5, is_core=True)
    print(f"  Saved pre-restart memory: '{restart_fact}'")

    # Simulate backend restart by re-initializing connection and service
    initialize_database()
    fresh_service = central_memory_service
    reloaded_memories = [m["content"] for m in fresh_service.get_all_memories(uid)]
    assert restart_fact in reloaded_memories, "Memory lost after simulated backend restart!"
    print(f"  Memory successfully loaded after database re-initialization.")
    print("  -> Scenario 6 PASSED.")

    # -------------------------------------------------------------
    # SCENARIO 7: Restart Desktop Application and Verify Memories Persist
    # -------------------------------------------------------------
    print_header("Scenario 7: Desktop App Restart Persistence Verification")
    # Simulate completely fresh desktop launch
    del desktop_manager
    fresh_desktop = MemoryManager(user_id=uid)
    desktop_context_restarted = fresh_desktop.get_persistent_memory_context()
    assert restart_fact in desktop_context_restarted, "Memory lost after simulated desktop restart!"
    print(f"  Fresh desktop manager successfully loaded persistent context.")
    print("  -> Scenario 7 PASSED.")

    # -------------------------------------------------------------
    # SCENARIO 8: Verify Different Users Cannot Access Each Other's Memories
    # -------------------------------------------------------------
    print_header("Scenario 8: Multi-Tenant User Isolation")
    # Register/retrieve User B
    user_b_email = "alice@zorin.ai"
    try:
        user_b = register_user(user_b_email, "securepass123", "Alice")["user"]
    except ValueError:
        user_b = get_user_by_email(user_b_email)
    assert user_b is not None

    user_b_id = user_b["user_id"]
    user_a_private = "Niharika's super secret investment portfolio code: XYZ-909."
    central_memory_service.save_memory(user_id=uid, category="private", content=user_a_private, importance=5)
    print(f"  User A ({default_user['display_name']}) saved private memory.")

    # User B tries to recall User A's memory
    user_b_results = central_memory_service.search_memories(user_id=user_b_id, query="portfolio")
    assert len(user_b_results) == 0, f"User isolation breached! User B saw: {user_b_results}"

    user_b_all = central_memory_service.get_all_memories(user_id=user_b_id)
    user_b_contents = [m["content"] for m in user_b_all]
    assert user_a_private not in user_b_contents, "User B saw User A's private memory in get_all_memories!"

    # User B tries to delete User A's memory
    user_a_mem_id = central_memory_service.search_memories(user_id=uid, query="XYZ-909")[0]["id"]
    attack_delete = central_memory_service.delete_memory(user_id=user_b_id, memory_id=user_a_mem_id, allow_core=True)
    assert attack_delete is False, "User B was able to delete User A's memory!"
    print("  User isolation verified: User B cannot read or delete User A's memories.")
    print("  -> Scenario 8 PASSED.")

    # -------------------------------------------------------------
    # SCENARIO 9: Multiple Simultaneous Clients Access Shared Memory
    # -------------------------------------------------------------
    print_header("Scenario 9: Concurrent Multi-Device Access")
    concurrency_errors = []

    def client_worker(client_num):
        try:
            client_fact = f"Fact from simultaneous client #{client_num} - value {client_num * 100}"
            central_memory_service.save_memory(
                user_id=uid,
                category="concurrency",
                content=client_fact,
                importance=2
            )
            # Read back
            mems = central_memory_service.get_all_memories(uid, limit=10)
            assert len(mems) > 0
        except Exception as e:
            concurrency_errors.append(f"Client {client_num} failed: {e}")

    threads = [threading.Thread(target=client_worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(concurrency_errors) == 0, f"Concurrency errors occurred: {concurrency_errors}"
    print("  10 simultaneous clients concurrently wrote and read from Central Memory with 0 errors.")
    print("  -> Scenario 9 PASSED.")

    # -------------------------------------------------------------
    # SCENARIO 10: Existing Voice & Tool Functionality Verification
    # -------------------------------------------------------------
    print_header("Scenario 10: Voice & Tool Functionality Verification")
    from intelligence.gemini_live import GeminiLive

    ai = GeminiLive(memory_context=fresh_desktop.get_persistent_memory_context())
    tools = ai.build_tools()
    tool_names = [f.name for f in tools[0].function_declarations]
    print(f"  Gemini Live Tool Declarations: {tool_names}")
    assert "open_app" in tool_names, "open_app tool missing"
    assert "open_website" in tool_names, "open_website tool missing"
    assert "create_website" in tool_names, "create_website tool missing"
    assert "save_memory" in tool_names, "save_memory tool missing from GeminiLive"

    # Test ToolRouter save_memory execution
    router = ToolRouter()
    voice_remember_result = router.execute(
        "save_memory",
        content="I prefer morning meetings at 10 AM.",
        category="preference",
        is_core=False
    )
    assert voice_remember_result["success"] is True, f"ToolRouter failed to save memory: {voice_remember_result}"
    print(f"  ToolRouter save_memory tool execution: {voice_remember_result}")

    # Verify that Central Memory holds the voice-saved memory
    voice_recalled = fresh_desktop.recall("morning meetings")
    assert len(voice_recalled) > 0, "Voice tool memory was not saved into Central Memory!"
    print(f"  Voice tool successfully saved to Central Memory: '{voice_recalled[0]['content']}'")
    print("  -> Scenario 10 PASSED.")

    print_header("ALL 10 CENTRAL MEMORY SCENARIOS PASSED WITH ZERO ERRORS!")


if __name__ == "__main__":
    run_tests()
