import sqlite3
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CENTRAL_DB = DATA_DIR / "zorin_memory.db"
OLD_BACKEND_DB = DATA_DIR / "backend" / "device_registry.db"

DEFAULT_USER_ID = "31aa888e-87d4-4235-9337-d0aec53df402"


def migrate():
    print("=" * 60)
    print("Starting Central Database Migration & Unification...")
    print("=" * 60)

    # 1. Connect to central DB (zorin_memory.db)
    conn = sqlite3.connect(CENTRAL_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 2. Add users table if not exists
    cursor.execute("""
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

    # 3. Add devices table if not exists
    cursor.execute("""
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

    # 4. Add remote_commands table if not exists
    cursor.execute("""
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

    # 5. Check and migrate columns in memories table
    cursor.execute("PRAGMA table_info(memories)")
    mem_cols = {row[1] for row in cursor.fetchall()}
    if "user_id" not in mem_cols:
        print("Adding user_id column to memories...")
        cursor.execute("ALTER TABLE memories ADD COLUMN user_id TEXT")
    
    # Update existing memories to have DEFAULT_USER_ID if null
    cursor.execute("UPDATE memories SET user_id = ? WHERE user_id IS NULL OR user_id = ''", (DEFAULT_USER_ID,))

    # 6. Check and migrate columns in conversations table
    cursor.execute("PRAGMA table_info(conversations)")
    conv_cols = {row[1] for row in cursor.fetchall()}
    if "user_id" not in conv_cols:
        print("Adding user_id column to conversations...")
        cursor.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")
    if "updated_at" not in conv_cols:
        print("Adding updated_at column to conversations...")
        cursor.execute("ALTER TABLE conversations ADD COLUMN updated_at TEXT")
    if "device_id" not in conv_cols:
        cursor.execute("ALTER TABLE conversations ADD COLUMN device_id TEXT")

    # Update existing conversations with DEFAULT_USER_ID and updated_at
    cursor.execute("UPDATE conversations SET user_id = ? WHERE user_id IS NULL OR user_id = ''", (DEFAULT_USER_ID,))
    cursor.execute("UPDATE conversations SET updated_at = created_at WHERE updated_at IS NULL OR updated_at = ''")

    # 7. Check and migrate columns in messages table
    cursor.execute("PRAGMA table_info(messages)")
    msg_cols = {row[1] for row in cursor.fetchall()}
    if "user_id" not in msg_cols:
        print("Adding user_id column to messages...")
        cursor.execute("ALTER TABLE messages ADD COLUMN user_id TEXT")
    if "device_id" not in msg_cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN device_id TEXT")

    cursor.execute("UPDATE messages SET user_id = ? WHERE user_id IS NULL OR user_id = ''", (DEFAULT_USER_ID,))

    # 8. Copy users and devices from old backend DB if exists
    if OLD_BACKEND_DB.exists():
        print(f"Migrating users and devices from {OLD_BACKEND_DB}...")
        old_conn = sqlite3.connect(OLD_BACKEND_DB)
        old_conn.row_factory = sqlite3.Row
        old_cursor = old_conn.cursor()

        # Copy users
        for u in old_cursor.execute("SELECT * FROM users").fetchall():
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, email, password_hash, salt, display_name, voice_preference, theme, created_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (u["user_id"], u["email"], u["password_hash"], u["salt"], u["display_name"], u["voice_preference"], u["theme"], u["created_at"], u["last_login"]))

        # Copy devices
        for d in old_cursor.execute("SELECT * FROM devices").fetchall():
            cursor.execute("""
                INSERT OR IGNORE INTO devices (device_id, user_id, device_name, operating_system, architecture, client_type, capabilities, registered_at, last_seen, status, is_default, auth_token)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (d["device_id"], d["user_id"], d["device_name"], d["operating_system"], d["architecture"], d["client_type"], d["capabilities"], d["registered_at"], d["last_seen"], d["status"], d["is_default"], d["auth_token"]))

        old_conn.close()

    # 9. Create indexes for high-speed multi-client retrieval
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_is_core ON memories(is_core)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_conv ON messages(user_id, conversation_id)")

    conn.commit()

    # Summary
    print("\n--- MIGRATION VERIFICATION ---")
    mem_count = cursor.execute("SELECT count(*) FROM memories").fetchone()[0]
    core_count = cursor.execute("SELECT count(*) FROM memories WHERE is_core = 1").fetchone()[0]
    conv_count = cursor.execute("SELECT count(*) FROM conversations").fetchone()[0]
    msg_count = cursor.execute("SELECT count(*) FROM messages").fetchone()[0]
    user_count = cursor.execute("SELECT count(*) FROM users").fetchone()[0]
    dev_count = cursor.execute("SELECT count(*) FROM devices").fetchone()[0]

    print(f"Total Users:         {user_count}")
    print(f"Total Devices:       {dev_count}")
    print(f"Total Conversations: {conv_count}")
    print(f"Total Messages:      {msg_count}")
    print(f"Total Memories:      {mem_count} (Core: {core_count})")
    print("------------------------------")
    print("Central Database Unified Successfully at:", CENTRAL_DB)

    conn.close()


if __name__ == "__main__":
    migrate()
