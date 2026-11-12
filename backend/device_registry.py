import json

from datetime import datetime, timezone

from backend.database import get_connection


def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def register_device(identity: dict) -> dict:

    required_fields = [
        "device_id",
        "device_name",
        "operating_system",
        "client_type"
    ]

    for field in required_fields:
        if not identity.get(field):
            raise ValueError(
                f"Missing required device field: {field}"
            )

    timestamp = current_timestamp()

    capabilities = json.dumps(
        identity.get("capabilities", [])
    )

    with get_connection() as connection:

        connection.execute("""
            INSERT INTO devices (
                device_id,
                device_name,
                operating_system,
                architecture,
                client_type,
                capabilities,
                registered_at,
                last_seen,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')

            ON CONFLICT(device_id) DO UPDATE SET
                device_name = excluded.device_name,
                operating_system = excluded.operating_system,
                architecture = excluded.architecture,
                client_type = excluded.client_type,
                capabilities = excluded.capabilities,
                last_seen = excluded.last_seen,
                status = 'active'
        """, (
            identity["device_id"],
            identity["device_name"],
            identity["operating_system"],
            identity.get("architecture", ""),
            identity["client_type"],
            capabilities,
            timestamp,
            timestamp
        ))

        connection.commit()

    return get_device(identity["device_id"])


def get_device(device_id: str):

    with get_connection() as connection:

        row = connection.execute(
            "SELECT * FROM devices WHERE device_id = ?",
            (device_id,)
        ).fetchone()

        if row is None:
            return None

        device = dict(row)

        device["capabilities"] = json.loads(
            device["capabilities"]
        )

        return device


def get_all_devices():

    with get_connection() as connection:

        rows = connection.execute(
            "SELECT * FROM devices ORDER BY registered_at"
        ).fetchall()

        devices = []

        for row in rows:

            device = dict(row)

            device["capabilities"] = json.loads(
                device["capabilities"]
            )

            devices.append(device)

        return devices


def update_device_status(device_id: str, status: str):

    if status not in ("active", "inactive"):
        raise ValueError("Invalid device status.")

    with get_connection() as connection:

        cursor = connection.execute("""
            UPDATE devices
            SET status = ?, last_seen = ?
            WHERE device_id = ?
        """, (
            status,
            current_timestamp(),
            device_id
        ))

        connection.commit()

        return cursor.rowcount > 0