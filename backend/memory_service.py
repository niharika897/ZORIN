import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from backend.database import get_connection, current_timestamp


class CoreMemoryProtectedError(Exception):
    """Raised when an automated or unprivileged action attempts to delete a protected Core Memory."""
    pass


class CentralMemoryService:
    """
    Unified Central Persistent Memory Service for ZORIN.
    Acts as the single source of truth for all clients (Desktop, Android, Web, etc.).
    Enforces user isolation, core memory protection, duplicate prevention, and thread-safe persistence.
    """

    # -------------------------------------------------------------
    # MEMORY RETRIEVAL
    # -------------------------------------------------------------

    def get_all_memories(self, user_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT id, user_id, category, content, importance, is_core, source, memory_type, created_at, updated_at
                FROM memories
                WHERE user_id = ?
                ORDER BY is_core DESC, importance DESC, updated_at DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
            return [dict(r) for r in rows]

    def get_core_memories(self, user_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT id, user_id, category, content, importance, is_core, source, memory_type, created_at, updated_at
                FROM memories
                WHERE user_id = ? AND is_core = 1
                ORDER BY importance DESC, updated_at DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
            return [dict(r) for r in rows]

    def search_memories(self, user_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            search_param = f"%{query.strip()}%"
            rows = conn.execute("""
                SELECT id, user_id, category, content, importance, is_core, source, memory_type, created_at, updated_at
                FROM memories
                WHERE user_id = ? AND (content LIKE ? OR category LIKE ?)
                ORDER BY is_core DESC, importance DESC, updated_at DESC
                LIMIT ?
            """, (user_id, search_param, search_param, limit)).fetchall()
            return [dict(r) for r in rows]

    def get_memory_by_id(self, user_id: str, memory_id: int) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute("""
                SELECT id, user_id, category, content, importance, is_core, source, memory_type, created_at, updated_at
                FROM memories
                WHERE id = ? AND user_id = ?
            """, (memory_id, user_id)).fetchone()
            return dict(row) if row else None

    # -------------------------------------------------------------
    # MEMORY CREATION & UPDATE (Safe against duplicates)
    # -------------------------------------------------------------

    def save_memory(
        self,
        user_id: str,
        category: str,
        content: str,
        importance: int = 1,
        is_core: bool = False,
        source: str = "conversation"
    ) -> Dict[str, Any]:
        content = str(content).strip()
        if not content:
            raise ValueError("Memory content cannot be empty.")

        category = str(category or "general").strip().lower()
        now = current_timestamp()
        memory_type = "core" if is_core else "long_term"

        with get_connection() as conn:
            # Check for existing duplicate under this user account
            existing = conn.execute("""
                SELECT id, is_core, importance, source, memory_type
                FROM memories
                WHERE user_id = ? AND category = ? AND LOWER(content) = LOWER(?)
                LIMIT 1
            """, (user_id, category, content)).fetchone()

            if existing:
                # Merge: preserve core status if either was core
                final_is_core = int(is_core or bool(existing["is_core"]))
                final_type = "core" if final_is_core else memory_type
                final_importance = max(importance, existing["importance"])
                final_source = "explicit" if (source == "explicit" or existing["source"] == "explicit") else source

                conn.execute("""
                    UPDATE memories
                    SET importance = ?,
                        is_core = ?,
                        source = ?,
                        memory_type = ?,
                        updated_at = ?
                    WHERE id = ? AND user_id = ?
                """, (final_importance, final_is_core, final_source, final_type, now, existing["id"], user_id))
                conn.commit()

                return {
                    "id": existing["id"],
                    "category": category,
                    "content": content,
                    "importance": final_importance,
                    "is_core": final_is_core,
                    "source": final_source,
                    "memory_type": final_type,
                    "updated": True
                }

            # Insert new memory
            cursor = conn.execute("""
                INSERT INTO memories (
                    user_id, category, content, importance, is_core, source, memory_type, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                category,
                content,
                importance,
                int(is_core),
                source,
                memory_type,
                now,
                now
            ))
            conn.commit()
            new_id = cursor.lastrowid

            return {
                "id": new_id,
                "category": category,
                "content": content,
                "importance": importance,
                "is_core": int(is_core),
                "source": source,
                "memory_type": memory_type,
                "created": True
            }

    def update_memory(self, user_id: str, memory_id: int, new_content: str) -> bool:
        new_content = str(new_content).strip()
        if not new_content:
            raise ValueError("New content cannot be empty.")

        now = current_timestamp()
        with get_connection() as conn:
            cursor = conn.execute("""
                UPDATE memories
                SET content = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (new_content, now, memory_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def pin_memory(self, user_id: str, memory_id: int) -> bool:
        """Promote an existing memory to protected Core Memory status."""
        now = current_timestamp()
        with get_connection() as conn:
            cursor = conn.execute("""
                UPDATE memories
                SET is_core = 1, memory_type = 'core', importance = 5, updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (now, memory_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def unpin_memory(self, user_id: str, memory_id: int) -> bool:
        """Demote a Core Memory to standard long-term memory."""
        now = current_timestamp()
        with get_connection() as conn:
            cursor = conn.execute("""
                UPDATE memories
                SET is_core = 0, memory_type = 'long_term', updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (now, memory_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    # -------------------------------------------------------------
    # CORE MEMORY PROTECTION ON DELETION
    # -------------------------------------------------------------

    def delete_memory(self, user_id: str, memory_id: int, allow_core: bool = False) -> bool:
        """
        Deletes a memory item.
        If the memory is marked as Core (is_core == 1) and allow_core is False,
        the deletion is prohibited to protect important user facts.
        """
        with get_connection() as conn:
            target = conn.execute("""
                SELECT is_core, content FROM memories WHERE id = ? AND user_id = ?
            """, (memory_id, user_id)).fetchone()

            if not target:
                return False

            if target["is_core"] and not allow_core:
                raise CoreMemoryProtectedError(
                    f"Memory '{target['content']}' is a protected Core Memory and cannot be automatically deleted. "
                    "Only explicit user action can delete Core Memories."
                )

            cursor = conn.execute("""
                DELETE FROM memories WHERE id = ? AND user_id = ?
            """, (memory_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    # -------------------------------------------------------------
    # CONTEXT GENERATION FOR AI ASSISTANT (All Clients)
    # -------------------------------------------------------------

    def get_persistent_memory_context(self, user_id: str) -> str:
        """Generates structured memory context for Gemini Live and client prompts."""
        all_memories = self.get_all_memories(user_id)
        if not all_memories:
            return ""

        core_memories = [m for m in all_memories if m["is_core"]]
        other_memories = [m for m in all_memories if not m["is_core"]]

        sections = []
        if core_memories:
            sections.append("PROTECTED CORE MEMORIES:")
            for m in core_memories:
                sections.append(f"- [{m['category']}] {m['content']}")

        if other_memories:
            sections.append("LONG-TERM MEMORIES:")
            for m in other_memories:
                sections.append(f"- [{m['category']}] {m['content']}")

        return "\n".join(sections)

    def get_past_conversation_context(self, user_id: str, limit: int = 30) -> str:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT m.role, m.content, m.created_at, c.title AS conv_title
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE m.user_id = ?
                ORDER BY m.id DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()

            if not rows:
                return ""

            lines = []
            for r in reversed(rows):
                speaker = "User" if r["role"] == "user" else "ZORIN"
                lines.append(f"{speaker}: {r['content']}")

            return "\n".join(lines)[-6000:]

    # -------------------------------------------------------------
    # CONVERSATIONS & MESSAGES
    # -------------------------------------------------------------

    def create_conversation(self, user_id: str, title: str = "New Conversation", device_id: Optional[str] = None) -> int:
        now = current_timestamp()
        with get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO conversations (user_id, title, device_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, title.strip() or "New Conversation", device_id, now, now))
            conn.commit()
            return cursor.lastrowid

    def save_message(self, user_id: str, conversation_id: int, role: str, content: str, device_id: Optional[str] = None):
        content = str(content).strip()
        if not content:
            return

        now = current_timestamp()
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO messages (conversation_id, user_id, role, content, device_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (conversation_id, user_id, role, content, device_id, now))

            # Update conversation timestamp
            conn.execute("""
                UPDATE conversations
                SET updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (now, conversation_id, user_id))
            conn.commit()

    def get_conversations(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT c.id, c.title, c.created_at, c.updated_at, COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = ?
                GROUP BY c.id
                ORDER BY c.updated_at DESC, c.id DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
            return [dict(r) for r in rows]

    def get_recent_messages(self, user_id: str, conversation_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT id, role, content, device_id, created_at
                FROM messages
                WHERE conversation_id = ? AND user_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (conversation_id, user_id, limit)).fetchall()
            return [dict(r) for r in reversed(rows)]

    def delete_conversation(self, user_id: str, conversation_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM conversations WHERE id = ? AND user_id = ?
            """, (conversation_id, user_id))
            conn.commit()
            return cursor.rowcount > 0


# Global singleton instance
central_memory_service = CentralMemoryService()
