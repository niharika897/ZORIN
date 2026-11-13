import json
import platform
import uuid

from pathlib import Path


IDENTITY_FILE = Path(__file__).resolve().parent / "device_identity.json"


def get_device_identity(controller=None):

    # Reuse the existing identity after every restart.
    if IDENTITY_FILE.exists():
        try:
            identity = json.loads(
                IDENTITY_FILE.read_text(encoding="utf-8")
            )

            if identity.get("device_id"):
                return identity

        except (OSError, json.JSONDecodeError):
            pass

    # Generate a permanent identity for this device.
    device_id = str(uuid.uuid4())

    device_info = {}

    if controller is not None:
        try:
            device_info = controller.get_device_info()
        except Exception:
            pass

    node_lower = platform.node().lower()
    dev_type = "laptop" if any(k in node_lower for k in ("laptop", "book", "surface")) else "desktop"

    identity = {
        "device_id": device_id,
        "device_name": device_info.get(
            "device_name", platform.node()
        ),
        "device_type": dev_type,
        "operating_system": device_info.get(
            "operating_system", platform.system()
        ),
        "architecture": device_info.get(
            "architecture", platform.machine()
        ),
        "client_type": "desktop",
        "has_microphone": True,
        "has_speaker": True,
        "ip_address": "127.0.0.1",
        "capabilities": device_info.get(
            "capabilities", ["open_app", "open_website", "create_website", "voice_input", "audio_output"]
        )
    }

    IDENTITY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    IDENTITY_FILE.write_text(
        json.dumps(identity, indent=4),
        encoding="utf-8"
    )

    return identity