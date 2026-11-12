import sqlite3

from pathlib import Path
from datetime import datetime, timezone


class Database:

    def __init__(self, db_path=None):

        project_root = Path(__file__).resolve().parent.parent

        if db_path is None:

            data_folder = project_root / "data"
            data_folder.mkdir(parents=True, exist_ok=True)

            db_path = data_folder / "zorin_memory.db"

        self.db_path = Path(db_path)

        self.initialize()

    def get_connection(self):

        connection = sqlite3.connect(self.db_path)

        connection.row_factory = sqlite3.Row

        connection.execute("PRAGMA foreign_keys = ON")

        return connection

    def initialize(self):

        with self.get_connection() as connection:

            connection.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,

                    FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Migrate existing databases safely.

            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(memories)"
                ).fetchall()
            }

            migrations = {
                "is_core": "INTEGER NOT NULL DEFAULT 0",
                "source": "TEXT DEFAULT 'conversation'",
                "memory_type": "TEXT DEFAULT 'long_term'"
            }

            for column, definition in migrations.items():

                if column not in columns:

                    connection.execute(
                        f"ALTER TABLE memories ADD COLUMN "
                        f"{column} {definition}"
                    )

            connection.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_memories_core
                ON memories(is_core)
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_memories_category
                ON memories(category)
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_messages_conversation
                ON messages(conversation_id)
            """)

            connection.commit()

    # CONVERSATIONS

    def create_conversation(self, title="New Conversation"):

        now = datetime.now(timezone.utc).isoformat()

        with self.get_connection() as connection:

            cursor = connection.execute(
                """
                INSERT INTO conversations (title, created_at)
                VALUES (?, ?)
                """,
                (title, now)
            )

            return cursor.lastrowid

    def save_message(self, conversation_id, role, content):

        now = datetime.now(timezone.utc).isoformat()

        with self.get_connection() as connection:

            connection.execute(
                """
                INSERT INTO messages
                (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, content, now)
            )

    def get_recent_messages(self, conversation_id, limit=20):

        with self.get_connection() as connection:

            results = connection.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, limit)
            ).fetchall()

            return [dict(row) for row in reversed(results)]

    def get_recent_conversation_messages(self, limit=30):

        with self.get_connection() as connection:

            results = connection.execute(
                """
                SELECT
                    messages.role,
                    messages.content,
                    messages.created_at,
                    conversations.id AS conversation_id,
                    conversations.title AS conversation_title

                FROM messages

                INNER JOIN conversations
                ON messages.conversation_id = conversations.id

                ORDER BY messages.id DESC

                LIMIT ?
                """,
                (limit,)
            ).fetchall()

            return [dict(row) for row in reversed(results)]

    # LONG-TERM AND CORE MEMORY

    def save_memory(
        self,
        category,
        content,
        importance=1,
        is_core=False,
        source="conversation"
    ):

        now = datetime.now(timezone.utc).isoformat()

        memory_type = "core" if is_core else "long_term"

        with self.get_connection() as connection:

            existing = connection.execute(
                """
                SELECT id, is_core
                FROM memories
                WHERE category = ? AND content = ?
                LIMIT 1
                """,
                (category, content)
            ).fetchone()

            if existing:

                connection.execute(
                    """
                    UPDATE memories

                    SET importance = ?,
                        is_core = ?,
                        source = ?,
                        memory_type = ?,
                        updated_at = ?

                    WHERE id = ?
                    """,
                    (
                        importance,
                        int(is_core or existing["is_core"]),
                        source,
                        "core" if is_core or existing["is_core"]
                        else memory_type,
                        now,
                        existing["id"]
                    )
                )

                return existing["id"]

            cursor = connection.execute(
                """
                INSERT INTO memories (
                    category,
                    content,
                    importance,
                    created_at,
                    updated_at,
                    is_core,
                    source,
                    memory_type
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category,
                    content,
                    importance,
                    now,
                    now,
                    int(is_core),
                    source,
                    memory_type
                )
            )

            return cursor.lastrowid

    def get_core_memories(self, limit=500):

        with self.get_connection() as connection:

            results = connection.execute(
                """
                SELECT *
                FROM memories
                WHERE is_core = 1
                ORDER BY importance DESC, updated_at DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

            return [dict(row) for row in results]

    def get_all_memories(self, limit=500):

        with self.get_connection() as connection:

            results = connection.execute(
                """
                SELECT *
                FROM memories

                ORDER BY
                    is_core DESC,
                    importance DESC,
                    updated_at DESC

                LIMIT ?
                """,
                (limit,)
            ).fetchall()

            return [dict(row) for row in results]

    def search_memories(self, query, limit=20):

        with self.get_connection() as connection:

            results = connection.execute(
                """
                SELECT *
                FROM memories

                WHERE content LIKE ?
                OR category LIKE ?

                ORDER BY
                    is_core DESC,
                    importance DESC,
                    updated_at DESC

                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", limit)
            ).fetchall()

            return [dict(row) for row in results]

    def update_memory(self, memory_id, new_content):

        now = datetime.now(timezone.utc).isoformat()

        with self.get_connection() as connection:

            cursor = connection.execute(
                """
                UPDATE memories

                SET content = ?,
                    updated_at = ?

                WHERE id = ?
                """,
                (new_content, now, memory_id)
            )

            return cursor.rowcount > 0

    def pin_memory(self, memory_id):

        now = datetime.now(timezone.utc).isoformat()

        with self.get_connection() as connection:

            cursor = connection.execute(
                """
                UPDATE memories

                SET is_core = 1,
                    memory_type = 'core',
                    importance = 5,
                    updated_at = ?

                WHERE id = ?
                """,
                (now, memory_id)
            )

            return cursor.rowcount > 0

    def unpin_memory(self, memory_id):

        now = datetime.now(timezone.utc).isoformat()

        with self.get_connection() as connection:

            cursor = connection.execute(
                """
                UPDATE memories

                SET is_core = 0,
                    memory_type = 'long_term',
                    updated_at = ?

                WHERE id = ?
                """,
                (now, memory_id)
            )

            return cursor.rowcount > 0

    def delete_memory(self, memory_id, allow_core=False):

        with self.get_connection() as connection:

            if not allow_core:

                cursor = connection.execute(
                    """
                    DELETE FROM memories
                    WHERE id = ? AND is_core = 0
                    """,
                    (memory_id,)
                )

            else:

                cursor = connection.execute(
                    """
                    DELETE FROM memories
                    WHERE id = ?
                    """,
                    (memory_id,)
                )

            return cursor.rowcount > 0