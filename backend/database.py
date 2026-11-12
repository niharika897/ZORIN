import sqlite3

from pathlib import Path
from contextlib import contextmanager


BASE_DIR = Path(__file__).resolve().parent.parent

BACKEND_DATA_DIR = BASE_DIR / "data" / "backend"

DATABASE_PATH = BACKEND_DATA_DIR / "device_registry.db"


def initialize_database():

    BACKEND_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_name TEXT NOT NULL,
                operating_system TEXT NOT NULL,
                architecture TEXT,
                client_type TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                registered_at TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            )
        """)

        connection.commit()


@contextmanager
def get_connection():

    initialize_database()

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
    finally:
        connection.close()