import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from backend.database import get_connection as get_central_connection, DATABASE_PATH, current_timestamp
from backend.auth import get_user_by_email

# Default user lookup for local desktop calls
DEFAULT_USER_EMAIL = "niharika@zorin.ai"


def get_default_user_id() -> str:
    u = get_user_by_email(DEFAULT_USER_EMAIL)
    return u["user_id"] if u else "31aa888e-87d4-4235-9337-d0aec53df402"


class Database:
    """
    Central Database Client Interface.
    Points directly to the single unified ZORIN central database: data/zorin_memory.db.
    Preserves all existing desktop method signatures while ensuring full multi-tenant compatibility.
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else DATABASE_PATH
        self.initialize()

    def get_connection(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self):
        # The central database schema is managed and initialized via backend.database
        from backend.database import initialize_database
        initialize_database()

    # ---------------------------------------------------------
    # CONVERSATIONS & MESSAGES
    # ---------------------------------------------------------

    def create_conversation(self, title="New Conversation", user_id: Optional[str] = None):
        uid = user_id or get_default_user_id()
        now = current_timestamp()

        with self.get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO conversations (title, user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (title, uid, now, now)
            )
            connection.commit()
            return cursor.lastrowid

    def save_message(self, conversation_id, role, content, user_id: Optional[str] = None, device_id: Optional[str] = None):
        uid = user_id or get_default_user_id()
        now = current_timestamp()

        with self.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO messages
                (conversation_id, user_id, role, content, device_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (conversation_id, uid, role, content, device_id, now)
            )
            # Update conversation timestamp
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id)
            )
            connection.commit()

    def get_recent_messages(self, conversation_id, limit=20, user_id: Optional[str] = None):
        uid = user_id or get_default_user_id()
        with self.get_connection() as connection:
            results = connection.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ? AND user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, uid, limit)
            ).fetchall()
            return [dict(row) for row in reversed(results)]

    def get_recent_conversation_messages(self, limit=30, user_id: Optional[str] = None):
        uid = user_id or get_default_user_id()
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
                WHERE messages.user_id = ?
                ORDER BY messages.id DESC
                LIMIT ?
                """,
                (uid, limit)
            ).fetchall()
            return [dict(row) for row in reversed(results)]

    # ---------------------------------------------------------
    # MEMORIES: CORE & LONG-TERM
    # ---------------------------------------------------------

    def save_memory(
        self,
        category,
        content,
        importance=1,
        is_core=False,
        source="conversation",
        user_id: Optional[str] = None
    ):
        from backend.memory_service import central_memory_service
        uid = user_id or get_default_user_id()
        res = central_memory_service.save_memory(
            user_id=uid,
            category=category,
            content=content,
            importance=importance,
            is_core=is_core,
            source=source
        )
        return res["id"]

    def get_core_memories(self, limit=500, user_id: Optional[str] = None):
        from backend.memory_service import central_memory_service
        uid = user_id or get_default_user_id()
        return central_memory_service.get_core_memories(user_id=uid, limit=limit)

    def get_all_memories(self, limit=500, user_id: Optional[str] = None):
        from backend.memory_service import central_memory_service
        uid = user_id or get_default_user_id()
        return central_memory_service.get_all_memories(user_id=uid, limit=limit)

    def search_memories(self, query, limit=20, user_id: Optional[str] = None):
        from backend.memory_service import central_memory_service
        uid = user_id or get_default_user_id()
        return central_memory_service.search_memories(user_id=uid, query=query, limit=limit)

    def update_memory(self, memory_id, new_content, user_id: Optional[str] = None):
        from backend.memory_service import central_memory_service
        uid = user_id or get_default_user_id()
        return central_memory_service.update_memory(user_id=uid, memory_id=memory_id, new_content=new_content)

    def pin_memory(self, memory_id, user_id: Optional[str] = None):
        from backend.memory_service import central_memory_service
        uid = user_id or get_default_user_id()
        return central_memory_service.pin_memory(user_id=uid, memory_id=memory_id)

    def unpin_memory(self, memory_id, user_id: Optional[str] = None):
        from backend.memory_service import central_memory_service
        uid = user_id or get_default_user_id()
        return central_memory_service.unpin_memory(user_id=uid, memory_id=memory_id)

    def delete_memory(self, memory_id, allow_core=False, user_id: Optional[str] = None):
        from backend.memory_service import central_memory_service, CoreMemoryProtectedError
        uid = user_id or get_default_user_id()
        try:
            return central_memory_service.delete_memory(user_id=uid, memory_id=memory_id, allow_core=allow_core)
        except CoreMemoryProtectedError:
            return False
