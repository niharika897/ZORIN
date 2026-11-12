import sqlite3
import os
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "zorin_memory.db"


def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def initialize_database():
    """
    Initializes the unified multi-user, multi-device SQLite database schema with safe migrations.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        # 1. Users Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                display_name TEXT NOT NULL,
                voice_preference TEXT DEFAULT 'Puck',
                theme TEXT DEFAULT 'cyberpunk',
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        """)

        # 2. Devices Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                user_id TEXT,
                device_name TEXT NOT NULL,
                operating_system TEXT NOT NULL,
                architecture TEXT,
                client_type TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                registered_at TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                is_default INTEGER DEFAULT 0,
                auth_token TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)

        # 3. Remote Commands Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS remote_commands (
                command_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                target_device_id TEXT NOT NULL,
                origin_device_id TEXT,
                action TEXT NOT NULL,
                parameters TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                result TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (target_device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            )
        """)

        # 4. Conversations Table (Supports historical desktop + multi-device)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                created_at TEXT NOT NULL,
                user_id TEXT,
                updated_at TEXT,
                device_id TEXT
            )
        """)

        # 5. Messages Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                user_id TEXT,
                device_id TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)

        # 6. Memories Table (Unified Core + Long-term Memory)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_core INTEGER NOT NULL DEFAULT 0,
                source TEXT DEFAULT 'conversation',
                memory_type TEXT DEFAULT 'long_term',
                user_id TEXT
            )
        """)

        # Safe Column Migrations if missing
        def ensure_column(table: str, column: str, col_type: str):
            cur = conn.execute(f"PRAGMA table_info({table})")
            existing = {row[1] for row in cur.fetchall()}
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

        ensure_column("devices", "user_id", "TEXT")
        ensure_column("devices", "is_default", "INTEGER DEFAULT 0")
        ensure_column("devices", "auth_token", "TEXT")
        ensure_column("memories", "user_id", "TEXT")
        ensure_column("memories", "is_core", "INTEGER NOT NULL DEFAULT 0")
        ensure_column("memories", "source", "TEXT DEFAULT 'conversation'")
        ensure_column("memories", "memory_type", "TEXT DEFAULT 'long_term'")
        ensure_column("conversations", "user_id", "TEXT")
        ensure_column("conversations", "updated_at", "TEXT")
        ensure_column("conversations", "device_id", "TEXT")
        ensure_column("messages", "user_id", "TEXT")
        ensure_column("messages", "device_id", "TEXT")

        # Indexes for fast lookup
        conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_core ON memories(is_core)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_commands_target ON remote_commands(target_device_id, status)")

        conn.commit()


@contextmanager
def get_connection():
    initialize_database()
    conn = sqlite3.connect(DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()
