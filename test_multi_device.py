import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.database import initialize_database, get_connection
from backend.auth import (
    register_user,
    authenticate_user,
    decode_token,
    seed_default_user_if_needed,
    get_user_by_email
)
from backend.device_registry import (
    register_device,
    get_device,
    get_user_devices,
    set_default_device
)
from device.controller_factory import create_device_controller
from backend.assistant_service import assistant_service


def test_database():
    print("[TEST] 1. Initializing database...")
    initialize_database()
    with get_connection() as conn:
        tables = [
            row["name"] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        print(f"       Found tables: {tables}")
        for req in ["users", "devices", "remote_commands", "conversations", "messages", "memories"]:
            assert req in tables, f"Missing table: {req}"
    print("       -> Database schema PASSED.\n")


def test_auth():
    print("[TEST] 2. Testing user authentication...")
    seed_default_user_if_needed()
    default_user = get_user_by_email("niharika@zorin.ai")
    assert default_user is not None, "Default user was not seeded."
    print(f"       Default user found: {default_user['display_name']} ({default_user['email']})")

    auth_res = authenticate_user("niharika@zorin.ai", "password123")
    assert "token" in auth_res, "Token missing from login result."
    token = auth_res["token"]
    payload = decode_token(token)
    assert payload["email"] == "niharika@zorin.ai", "Decoded token email mismatch."
    print("       -> Auth & token verification PASSED.\n")
    return auth_res["user"]


def test_device_registry(user):
    print("[TEST] 3. Testing device registration...")
    identity = {
        "device_id": "test-win-pc-001",
        "device_name": "Niharika's Windows Laptop",
        "operating_system": "Windows",
        "architecture": "AMD64",
        "client_type": "desktop",
        "capabilities": ["open_app", "open_website", "create_website"]
    }
    dev = register_device(identity, user_id=user["user_id"])
    assert dev["device_id"] == "test-win-pc-001"
    assert dev["device_name"] == "Niharika's Windows Laptop"
    print(f"       Registered device: {dev['device_name']} (Default: {dev['is_default']})")

    # Register phone device
    phone_id = {
        "device_id": "test-phone-002",
        "device_name": "iPhone 15 Pro",
        "operating_system": "iOS",
        "architecture": "ARM64",
        "client_type": "mobile",
        "capabilities": ["open_website", "mobile_pwa"]
    }
    phone = register_device(phone_id, user_id=user["user_id"])
    print(f"       Registered second device: {phone['device_name']}")

    user_devs = get_user_devices(user["user_id"])
    assert len(user_devs) >= 2, "Expected at least 2 registered devices."
    print(f"       User total paired devices: {len(user_devs)}")
    print("       -> Device registry PASSED.\n")


def test_controllers():
    print("[TEST] 4. Testing cross-platform controllers...")
    win_ctrl = create_device_controller("windows")
    info = win_ctrl.get_device_info()
    assert info["operating_system"] == "Windows"
    print(f"       Windows controller initialized: {info['capabilities']}")

    darwin_ctrl = create_device_controller("darwin")
    assert darwin_ctrl.get_device_info()["operating_system"] == "macOS"
    print("       macOS controller initialized.")

    linux_ctrl = create_device_controller("linux")
    assert linux_ctrl.get_device_info()["operating_system"] == "Linux"
    print("       Linux controller initialized.")

    mobile_ctrl = create_device_controller("ios")
    assert mobile_ctrl.get_device_info()["operating_system"] == "Ios"
    print("       Mobile controller initialized.")
    print("       -> Controllers PASSED.\n")


async def test_assistant(user):
    print("[TEST] 5. Testing Assistant AI Service with multi-device context...")
    res = await assistant_service.chat(
        user_id=user["user_id"],
        user_profile=user,
        message="Hello ZORIN, who are you and what devices do I have?",
        conversation_id="test_conv_001"
    )
    assert res["success"] is True, f"Chat failed: {res}"
    print(f"       AI Spoken Reply: {res['text'][:120]}...")
    print(f"       Model used: {res.get('model')}")
    print("       -> Assistant multi-device chat PASSED.\n")


async def run_all():
    print("=" * 60)
    print("      RUNNING ZORIN MULTI-DEVICE ARCHITECTURE TESTS")
    print("=" * 60)
    test_database()
    user = test_auth()
    test_device_registry(user)
    test_controllers()
    await test_assistant(user)
    print("=" * 60)
    print("      ALL MULTI-DEVICE ARCHITECTURE TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all())
