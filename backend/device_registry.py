import json
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from backend.database import get_connection, current_timestamp
from backend.device_hub import device_hub


def register_device(identity: dict, user_id: Optional[str] = None) -> dict:
    """
    Registers or updates a device identity in the database, associating it with a user.
    Supports comprehensive hardware capabilities (audio input/output, OS, device type).
    """
    required_fields = [
        "device_id",
        "device_name",
        "operating_system",
        "client_type"
    ]

    for field in required_fields:
        if not identity.get(field):
            raise ValueError(f"Missing required device field: {field}")

    timestamp = current_timestamp()
    raw_caps = identity.get("capabilities", [])
    capabilities = json.dumps(raw_caps if isinstance(raw_caps, list) else [])

    # Infer or extract device type
    device_type = identity.get("device_type")
    if not device_type:
        os_lower = str(identity.get("operating_system", "")).lower()
        name_lower = str(identity.get("device_name", "")).lower()
        client_type = str(identity.get("client_type", "")).lower()

        if "android" in os_lower or "android" in name_lower:
            device_type = "android_phone"
        elif "ios" in os_lower or "iphone" in name_lower:
            device_type = "iphone"
        elif "ipad" in name_lower or "tablet" in client_type:
            device_type = "tablet"
        elif "bluetooth" in client_type or "audio" in client_type or "headphone" in name_lower or "speaker" in name_lower:
            device_type = "bluetooth_audio"
        elif "laptop" in name_lower:
            device_type = "laptop"
        else:
            device_type = "desktop"

    has_mic = 1 if identity.get("has_microphone", True) else 0
    has_spk = 1 if identity.get("has_speaker", True) else 0
    ip_addr = identity.get("ip_address") or "127.0.0.1"
    pairing_status = identity.get("pairing_status") or "paired"
    auth_token = identity.get("auth_token")

    with get_connection() as conn:
        # Check if device already exists to preserve user_id if not supplied
        existing = conn.execute(
            "SELECT user_id, is_default, auth_token FROM devices WHERE device_id = ?",
            (identity["device_id"],)
        ).fetchone()

        target_user_id = user_id or (existing["user_id"] if existing else None)
        final_token = auth_token or (existing["auth_token"] if existing else None)

        # If user has no default device yet, make this one the default
        is_default = 0
        if target_user_id:
            count_defaults = conn.execute(
                "SELECT COUNT(*) as cnt FROM devices WHERE user_id = ? AND is_default = 1",
                (target_user_id,)
            ).fetchone()["cnt"]
            if count_defaults == 0:
                is_default = 1
        elif existing:
            is_default = existing["is_default"]

        conn.execute("""
            INSERT INTO devices (
                device_id,
                user_id,
                device_name,
                operating_system,
                architecture,
                client_type,
                capabilities,
                registered_at,
                last_seen,
                status,
                is_default,
                auth_token,
                device_type,
                has_microphone,
                has_speaker,
                ip_address,
                pairing_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'online', ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                user_id = COALESCE(excluded.user_id, devices.user_id),
                device_name = excluded.device_name,
                operating_system = excluded.operating_system,
                architecture = excluded.architecture,
                client_type = excluded.client_type,
                capabilities = excluded.capabilities,
                last_seen = excluded.last_seen,
                status = 'online',
                auth_token = COALESCE(excluded.auth_token, devices.auth_token),
                device_type = excluded.device_type,
                has_microphone = excluded.has_microphone,
                has_speaker = excluded.has_speaker,
                ip_address = excluded.ip_address,
                pairing_status = excluded.pairing_status
        """, (
            identity["device_id"],
            target_user_id,
            identity["device_name"],
            identity["operating_system"],
            identity.get("architecture", ""),
            identity["client_type"],
            capabilities,
            timestamp,
            timestamp,
            is_default,
            final_token,
            device_type,
            has_mic,
            has_spk,
            ip_addr,
            pairing_status
        ))
        conn.commit()

    return get_device(identity["device_id"])


def get_device(device_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM devices WHERE device_id = ?",
            (device_id,)
        ).fetchone()

        if row is None:
            return None

        device = dict(row)
        try:
            device["capabilities"] = json.loads(device["capabilities"])
        except Exception:
            device["capabilities"] = []

        device["is_online"] = device_hub.is_device_online(device_id)
        return device


def get_all_devices() -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM devices ORDER BY registered_at").fetchall()
        devices = []
        for row in rows:
            dev = dict(row)
            try:
                dev["capabilities"] = json.loads(dev["capabilities"])
            except Exception:
                dev["capabilities"] = []
            dev["is_online"] = device_hub.is_device_online(dev["device_id"])
            devices.append(dev)
        return devices


def get_user_devices(user_id: str) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM devices WHERE user_id = ? ORDER BY is_default DESC, last_seen DESC",
            (user_id,)
        ).fetchall()
        devices = []
        for row in rows:
            dev = dict(row)
            try:
                dev["capabilities"] = json.loads(dev["capabilities"])
            except Exception:
                dev["capabilities"] = []
            dev["is_online"] = device_hub.is_device_online(dev["device_id"])
            devices.append(dev)
        return devices


def set_default_device(user_id: str, device_id: str) -> bool:
    with get_connection() as conn:
        # Verify ownership
        dev = conn.execute(
            "SELECT device_id FROM devices WHERE device_id = ? AND user_id = ?",
            (device_id, user_id)
        ).fetchone()
        if not dev:
            return False

        # Reset all for user
        conn.execute("UPDATE devices SET is_default = 0 WHERE user_id = ?", (user_id,))
        # Set target as default
        conn.execute("UPDATE devices SET is_default = 1 WHERE device_id = ?", (device_id,))
        conn.commit()
        return True


def get_default_device(user_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM devices WHERE user_id = ? AND is_default = 1",
            (user_id,)
        ).fetchone()
        if not row:
            # Fallback to most recently seen device
            row = conn.execute(
                "SELECT * FROM devices WHERE user_id = ? ORDER BY last_seen DESC LIMIT 1",
                (user_id,)
            ).fetchone()
        if not row:
            return None
        dev = dict(row)
        try:
            dev["capabilities"] = json.loads(dev["capabilities"])
        except Exception:
            dev["capabilities"] = []
        dev["is_online"] = device_hub.is_device_online(dev["device_id"])
        return dev


def update_device_status(device_id: str, status: str) -> bool:
    if status not in ("active", "inactive", "online", "offline"):
        raise ValueError("Invalid device status.")

    with get_connection() as conn:
        cursor = conn.execute("""
            UPDATE devices
            SET status = ?, last_seen = ?
            WHERE device_id = ?
        """, (status, current_timestamp(), device_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_device(user_id: str, device_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM devices WHERE device_id = ? AND user_id = ?",
            (device_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


# -------------------------------------------------------------
# MULTI-DEVICE PAIRING (6-Digit PIN & QR-Code Cross-Device Sync)
# -------------------------------------------------------------

def create_pairing_token(user_id: str, server_url: Optional[str] = None) -> dict:
    """
    Generates a secure 6-digit pairing PIN and QR Code payload for Android / secondary PC pairing.
    Expires automatically after 10 minutes.
    """
    token_id = str(uuid.uuid4())
    pin_code = f"{random.randint(100000, 999999)}"
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(minutes=10)).isoformat()
    created_at = now.isoformat()

    url = (server_url or "http://127.0.0.1:8000").rstrip("/")
    qr_payload = {
        "zorin_pair": True,
        "token_id": token_id,
        "pin_code": pin_code,
        "server_url": url,
        "user_id": user_id,
        "expires_at": expires_at
    }

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO device_pairing_tokens (token_id, user_id, pin_code, qr_data, created_at, expires_at, used)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (token_id, user_id, pin_code, json.dumps(qr_payload), created_at, expires_at))
        conn.commit()

    return {
        "success": True,
        "token_id": token_id,
        "pin_code": pin_code,
        "qr_data": json.dumps(qr_payload),
        "server_url": url,
        "expires_at": expires_at
    }


def verify_pairing_token(pin_or_token: str) -> Optional[dict]:
    """Checks if a 6-digit PIN or QR token is valid and unexpired."""
    now = datetime.now(timezone.utc).isoformat()
    clean_val = str(pin_or_token).strip()

    with get_connection() as conn:
        row = conn.execute("""
            SELECT * FROM device_pairing_tokens
            WHERE (pin_code = ? OR token_id = ?)
              AND used = 0
              AND expires_at > ?
            ORDER BY created_at DESC LIMIT 1
        """, (clean_val, clean_val, now)).fetchone()

        return dict(row) if row else None


def consume_pairing_token(pin_or_token: str, device_identity: dict) -> dict:
    """
    Pairs an incoming device (Android, iPhone, secondary PC, tablet) using a valid PIN or QR token.
    Authenticates the device, pairs it with the user account, and returns a persistent auth token.
    """
    token_info = verify_pairing_token(pin_or_token)
    if not token_info:
        raise ValueError("Invalid, expired, or already used pairing PIN / QR code.")

    user_id = token_info["user_id"]
    from backend.auth import create_access_token, get_user_by_id

    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("Associated user account not found.")

    # Mark token used
    with get_connection() as conn:
        conn.execute(
            "UPDATE device_pairing_tokens SET used = 1 WHERE token_id = ?",
            (token_info["token_id"],)
        )
        conn.commit()

    # Generate device persistent auth token
    auth_token = create_access_token(user_id, user["email"])
    device_identity["auth_token"] = auth_token

    # Register device into user's fleet
    device = register_device(device_identity, user_id=user_id)
    return {
        "success": True,
        "message": f"Device '{device_identity.get('device_name')}' successfully paired with ZORIN!",
        "device": device,
        "auth_token": auth_token,
        "user": {
            "user_id": user["user_id"],
            "display_name": user["display_name"],
            "email": user["email"]
        }
    }


def set_device_connection_status(user_id: str, device_id: str, status: str) -> bool:
    """Connects or disconnects a device in the user's fleet."""
    if status not in ("online", "offline", "active", "inactive"):
        raise ValueError(f"Invalid status: {status}")

    with get_connection() as conn:
        cursor = conn.execute("""
            UPDATE devices
            SET status = ?, last_seen = ?
            WHERE device_id = ? AND user_id = ?
        """, (status, current_timestamp(), device_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


# -------------------------------------------------------------
# HARDWARE & NEARBY DEVICE DISCOVERY (Bluetooth / Audio / Network)
# -------------------------------------------------------------

def scan_nearby_devices() -> List[dict]:
    """
    Scans for real physical hardware on the host system:
    - Microphones & Microphone Arrays
    - Speakers & Realtek/AMD Audio outputs
    - Connected Bluetooth Headsets & Audio devices
    - Available Network endpoints
    """
    nearby = []
    seen_names = set()

    # 1. Real Audio & Bluetooth hardware via sounddevice
    try:
        import sounddevice as sd
        devices = sd.query_devices()

        for idx, d in enumerate(devices):
            name = str(d.get("name", "")).strip()
            if not name or name in seen_names:
                continue

            # Skip generic duplicate mapper virtual aliases
            if "Microsoft Sound Mapper" in name or "Primary Sound" in name:
                continue

            seen_names.add(name)
            max_in = d.get("max_input_channels", 0)
            max_out = d.get("max_output_channels", 0)
            name_lower = name.lower()

            is_bt = any(k in name_lower for k in ("bluetooth", "wireless", "buds", "airpods", "headset", "hands-free"))
            is_mic = max_in > 0
            is_speaker = max_out > 0

            dtype = "bluetooth_audio" if is_bt else ("audio_input" if is_mic and not is_speaker else "audio_output")

            nearby.append({
                "device_id": f"hw-audio-{idx}",
                "device_name": name,
                "device_type": dtype,
                "operating_system": "Windows",
                "client_type": "hardware",
                "has_microphone": bool(is_mic),
                "has_speaker": bool(is_speaker),
                "capabilities": ["audio_streaming"] if is_bt else (["microphone"] if is_mic else ["speaker"]),
                "connection_status": "available",
                "is_bluetooth": is_bt,
                "is_online": False,
                "last_seen": current_timestamp()
            })

    except Exception as e:
        print("Hardware audio scan notice:", e)

    return nearby
