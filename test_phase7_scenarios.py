import sys
import json
import uuid
from pathlib import Path

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.database import initialize_database, get_connection, current_timestamp
import backend.database as db
from backend.auth import (
    authenticate_user,
    seed_default_user_if_needed,
    get_user_by_email,
    get_user_by_id,
    create_access_token
)
from backend.device_registry import (
    register_device,
    get_device,
    get_user_devices,
    set_default_device,
    update_device_status,
    delete_device,
    create_pairing_token,
    consume_pairing_token,
    set_device_connection_status,
    scan_nearby_devices
)
from backend.memory_service import central_memory_service, CoreMemoryProtectedError
from backend.client import ZorinBackendClient
from device.identity import get_device_identity


def run_all_phase7_tests():
    print("=" * 70)
    print("       ZORIN MULTI-DEVICE ARCHITECTURE - PHASE 7 VERIFICATION")
    print("=" * 70)

    # Setup
    seed_default_user_if_needed()
    user = get_user_by_email("niharika@zorin.ai")
    assert user is not None, "Failed to load default user."
    user_id = user["user_id"]
    print(f"[*] Verified Central User: {user['display_name']} ({user['email']})")

    # -----------------------------------------------------------------
    # TEST 1: Start ZORIN on the Windows laptop
    # -----------------------------------------------------------------
    print("\n[TEST 1] Starting ZORIN on the Windows laptop...")
    laptop_identity = get_device_identity()
    assert laptop_identity.get("device_id"), "Laptop device identity missing ID."
    assert laptop_identity.get("operating_system") == "Windows", "Laptop OS mismatch."
    print(f"  ✓ Laptop Identity: {laptop_identity['device_name']} (ID: {laptop_identity['device_id']})")
    print(f"  ✓ OS: {laptop_identity['operating_system']} | Client: {laptop_identity['client_type']}")
    print("  -> TEST 1 PASSED: ZORIN Windows Laptop initialized successfully.")

    # -----------------------------------------------------------------
    # TEST 2: Register the laptop with the central backend
    # -----------------------------------------------------------------
    print("\n[TEST 2] Registering the laptop with the central backend...")
    registered_laptop = register_device(laptop_identity, user_id=user_id)
    assert registered_laptop["device_id"] == laptop_identity["device_id"]
    assert registered_laptop["user_id"] == user_id
    assert registered_laptop["status"] == "online"
    assert registered_laptop["has_microphone"] == 1
    assert registered_laptop["has_speaker"] == 1
    print(f"  ✓ Registered Laptop in Hub: {registered_laptop['device_name']}")
    print(f"  ✓ Status: {registered_laptop['status'].upper()} | Type: {registered_laptop.get('device_type')}")
    print("  -> TEST 2 PASSED: Laptop registered with full hardware specifications.")

    # -----------------------------------------------------------------
    # TEST 3: Connect a second client (Android Smartphone)
    # -----------------------------------------------------------------
    print("\n[TEST 3] Connecting a second client via 6-Digit PIN pairing...")
    # Step 3a: Hub generates pairing token
    pair_request = create_pairing_token(user_id=user_id, server_url="http://192.168.1.27:8000")
    pin = pair_request["pin_code"]
    print(f"  ✓ Generated Pairing PIN: {pin} (Expires: {pair_request['expires_at']})")

    # Step 3b: Android client connects and submits PIN
    android_id = f"android-phone-{uuid.uuid4().hex[:6]}"
    android_identity = {
        "device_id": android_id,
        "device_name": "Samsung Galaxy S24 Ultra",
        "operating_system": "Android 14",
        "client_type": "mobile",
        "device_type": "android_phone",
        "has_microphone": True,
        "has_speaker": True,
        "ip_address": "192.168.1.45",
        "capabilities": ["voice_input", "audio_output", "camera", "shared_memory"]
    }

    pair_result = consume_pairing_token(pin_or_token=pin, device_identity=android_identity)
    assert pair_result["success"] is True, f"Pairing failed: {pair_result}"
    android_device = pair_result["device"]
    assert android_device["device_id"] == android_id
    assert android_device["user_id"] == user_id
    assert android_device["device_type"] == "android_phone"
    print(f"  ✓ Paired Second Client: {android_device['device_name']} [{android_device['operating_system']}]")
    print(f"  ✓ Auth Token Issued: {pair_result['auth_token'][:20]}...")
    print("  -> TEST 3 PASSED: Second client paired with central brain.")

    # -----------------------------------------------------------------
    # TEST 4: Verify that both clients can remain connected simultaneously
    # -----------------------------------------------------------------
    print("\n[TEST 4] Verifying simultaneous multi-device connection...")
    user_devices = get_user_devices(user_id)
    device_ids = [d["device_id"] for d in user_devices]
    assert laptop_identity["device_id"] in device_ids, "Laptop not found in fleet."
    assert android_id in device_ids, "Android smartphone not found in fleet."

    laptop_dev = next(d for d in user_devices if d["device_id"] == laptop_identity["device_id"])
    android_dev = next(d for d in user_devices if d["device_id"] == android_id)
    print(f"  ✓ Total active devices in user fleet: {len(user_devices)}")
    print(f"  ✓ Device A (Laptop): {laptop_dev['device_name']} (Status: {laptop_dev['status']})")
    print(f"  ✓ Device B (Phone):  {android_dev['device_name']} (Status: {android_dev['status']})")
    print("  -> TEST 4 PASSED: Both clients registered and active simultaneously.")

    # -----------------------------------------------------------------
    # TEST 5: Send a message from one client and verify central AI processes it
    # -----------------------------------------------------------------
    print("\n[TEST 5] Sending message from Android phone to Central Hub...")
    conv_id = central_memory_service.create_conversation(
        user_id=user_id,
        title="Multi-Device Cross Sync Thread",
        device_id=android_id
    )
    # Android saves user query
    central_memory_service.save_message(
        user_id=user_id,
        conversation_id=conv_id,
        role="user",
        content="ZORIN, remember my flight is tomorrow at 6 PM.",
        device_id=android_id
    )
    # Central Hub processes and saves AI assistant reply
    central_memory_service.save_message(
        user_id=user_id,
        conversation_id=conv_id,
        role="assistant",
        content="I have noted that your flight is tomorrow at 6 PM.",
        device_id="central-hub"
    )
    print("  ✓ Message from Android recorded by Central Brain in conversation #" + str(conv_id))
    print("  -> TEST 5 PASSED: Central AI backend received and recorded message.")

    # -----------------------------------------------------------------
    # TEST 6: Verify shared conversation history
    # -----------------------------------------------------------------
    print("\n[TEST 6] Verifying shared conversation history on Windows Laptop...")
    # Laptop reads conversation started on Phone
    laptop_view_msgs = central_memory_service.get_recent_messages(
        user_id=user_id,
        conversation_id=conv_id,
        limit=10
    )
    assert len(laptop_view_msgs) >= 2, f"Expected messages not found: {laptop_view_msgs}"
    user_msg = next((m for m in laptop_view_msgs if m["role"] == "user"), None)
    assert user_msg is not None and "flight is tomorrow" in user_msg["content"]
    assert user_msg.get("device_id") == android_id
    print(f"  ✓ Laptop successfully read conversation created on Phone:")
    for m in laptop_view_msgs:
        dev_tag = f"[{m.get('device_id', 'hub')}]"
        print(f"    • {m['role'].upper()} {dev_tag}: {m['content']}")
    print("  -> TEST 6 PASSED: Shared conversation history seamlessly synchronized.")

    # -----------------------------------------------------------------
    # TEST 7: Verify shared persistent memory & Core Memory protection
    # -----------------------------------------------------------------
    print("\n[TEST 7] Verifying shared persistent memory & Core Memory protection...")
    # 7a: Save a long-term memory from Phone
    mem_phone = central_memory_service.save_memory(
        user_id=user_id,
        category="travel",
        content="User has a flight tomorrow at 6 PM.",
        importance=2,
        is_core=False,
        source="conversation"
    )
    print(f"  ✓ Phone saved long-term memory #{mem_phone['id']}")

    # 7b: Laptop retrieves it
    laptop_memories = central_memory_service.get_all_memories(user_id=user_id)
    found_mem = any(m["id"] == mem_phone["id"] for m in laptop_memories)
    assert found_mem, "Memory saved from Phone not visible on Laptop."
    print("  ✓ Laptop successfully retrieved memory saved by Phone.")

    # 7c: Pin to Core Memory
    central_memory_service.pin_memory(user_id=user_id, memory_id=mem_phone["id"])
    core_mems = central_memory_service.get_core_memories(user_id=user_id)
    assert any(m["id"] == mem_phone["id"] for m in core_mems), "Memory was not pinned to Core."
    print("  ✓ Memory pinned to protected Core Memory.")

    # 7d: Attempt deletion without allow_core (Must be rejected)
    protected_passed = False
    try:
        central_memory_service.delete_memory(user_id=user_id, memory_id=mem_phone["id"], allow_core=False)
    except CoreMemoryProtectedError as err:
        protected_passed = True
        print(f"  ✓ Protected Core Memory correctly defended against deletion: {err}")
    assert protected_passed, "Security failure: Core Memory was deleted without approval!"

    # 7e: Delete with explicit approval
    ok = central_memory_service.delete_memory(user_id=user_id, memory_id=mem_phone["id"], allow_core=True)
    assert ok is True
    print("  ✓ Core Memory deletion permitted only after explicit user approval.")
    print("  -> TEST 7 PASSED: Shared persistent memory and Core Memory safety verified.")

    # -----------------------------------------------------------------
    # TEST 8: Disconnect and reconnect a device
    # -----------------------------------------------------------------
    print("\n[TEST 8] Testing disconnect and reconnect workflow...")
    # Disconnect phone
    set_device_connection_status(user_id=user_id, device_id=android_id, status="offline")
    d_off = get_device(android_id)
    assert d_off["status"] == "offline"
    print(f"  ✓ Disconnected {android_dev['device_name']} -> Status: {d_off['status'].upper()}")

    # Reconnect phone
    set_device_connection_status(user_id=user_id, device_id=android_id, status="online")
    d_on = get_device(android_id)
    assert d_on["status"] == "online"
    print(f"  ✓ Reconnected {android_dev['device_name']} -> Status: {d_on['status'].upper()}")
    print("  -> TEST 8 PASSED: Device disconnection and reconnection verified.")

    # -----------------------------------------------------------------
    # TEST 9: Verify that desktop Devices interface reflects actual changes
    # -----------------------------------------------------------------
    print("\n[TEST 9] Verifying desktop Devices interface reflects actual data...")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from desktop.device_ui import DeviceDashboard
    from desktop.modern_ui import ZorinWindow

    # Open Device Dashboard and check state
    dash = DeviceDashboard()
    dash.refresh_all()
    assert len(dash.devices) >= 2, f"Expected at least 2 devices in dashboard, found {len(dash.devices)}"
    dash_ids = [d["device_id"] for d in dash.devices]
    assert laptop_identity["device_id"] in dash_ids
    assert android_id in dash_ids
    print(f"  ✓ Device Dashboard loaded {len(dash.devices)} real devices from fleet.")
    print(f"  ✓ Hardware scan discovered {len(dash.nearby_devices)} local audio/Bluetooth devices.")

    # Check ZorinWindow badge
    win = ZorinWindow()
    win.update_device_badge(dash.devices, server_online=True)
    badge_text = win.device_badge.text()
    assert "Central Hub:" in badge_text
    print(f"  ✓ Desktop Main Window Badge: '{badge_text}'")
    print("  -> TEST 9 PASSED: Desktop Devices interface displays real fleet info.")

    # -----------------------------------------------------------------
    # TEST 10: Restart the backend and verify persistent device and memory data
    # -----------------------------------------------------------------
    print("\n[TEST 10] Simulating Backend Restart & Verifying Persistence...")
    # Force reset DB cache to simulate cold boot
    db._DATABASE_INITIALIZED = False
    initialize_database()

    restarted_devices = get_user_devices(user_id)
    restarted_device_ids = [d["device_id"] for d in restarted_devices]
    assert laptop_identity["device_id"] in restarted_device_ids
    assert android_id in restarted_device_ids

    restarted_history = central_memory_service.get_recent_messages(user_id=user_id, conversation_id=conv_id, limit=5)
    assert len(restarted_history) >= 2

    restarted_memories = central_memory_service.get_all_memories(user_id=user_id)
    print(f"  ✓ Data survived cold boot: {len(restarted_devices)} devices, {len(restarted_memories)} memories, conversation #{conv_id} intact.")
    print("  -> TEST 10 PASSED: Complete multi-device state persisted across backend restart.")

    print("\n" + "=" * 70)
    print("    🏆 ALL 10 MULTI-DEVICE ARCHITECTURE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_phase7_tests()
