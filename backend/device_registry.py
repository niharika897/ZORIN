import json
from datetime import datetime, timezone
from typing import Optional, List

from backend.database import get_connection, current_timestamp
from backend.device_hub import device_hub


def register_device(identity: dict, user_id: Optional[str] = None) -> dict:
    """
    Registers or updates a device identity in the database, associating it with a user.
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

    with get_connection() as conn:
        # Check if device already exists to preserve user_id if not supplied
        existing = conn.execute(
            "SELECT user_id, is_default FROM devices WHERE device_id = ?",
            (identity["device_id"],)
        ).fetchone()

        target_user_id = user_id or (existing["user_id"] if existing else None)

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
                is_default
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'online', ?)
            ON CONFLICT(device_id) DO UPDATE SET
                user_id = COALESCE(excluded.user_id, devices.user_id),
                device_name = excluded.device_name,
                operating_system = excluded.operating_system,
                architecture = excluded.architecture,
                client_type = excluded.client_type,
                capabilities = excluded.capabilities,
                last_seen = excluded.last_seen,
                status = 'online'
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
            is_default
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
