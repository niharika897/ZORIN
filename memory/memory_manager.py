from typing import Optional, List, Dict, Any
from memory.database import Database, get_default_user_id


class MemoryManager:
    """
    Unified Memory Manager for ZORIN.
    Provides a consistent client interface for desktop, background workers, and services.
    Directly backed by the Central Memory System and persistent database.
    """

    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id or get_default_user_id()
        self.database = Database()
        self.current_conversation_id = None

    # ---------------------------------------------------------
    # CONVERSATION MANAGEMENT
    # ---------------------------------------------------------

    def start_conversation(self, title="New Conversation"):
        self.current_conversation_id = self.database.create_conversation(
            title=title,
            user_id=self.user_id
        )
        return self.current_conversation_id

    def add_message(self, role, content, device_id: Optional[str] = None):
        if not content or not content.strip():
            return

        if self.current_conversation_id is None:
            self.start_conversation()

        self.database.save_message(
            conversation_id=self.current_conversation_id,
            role=role,
            content=content.strip(),
            user_id=self.user_id,
            device_id=device_id
        )

    def get_recent_context(self, limit=20):
        if self.current_conversation_id is None:
            return []

        return self.database.get_recent_messages(
            conversation_id=self.current_conversation_id,
            limit=limit,
            user_id=self.user_id
        )

    def get_past_conversation_context(self, limit=30):
        messages = self.database.get_recent_conversation_messages(
            limit=limit,
            user_id=self.user_id
        )
        if not messages:
            return ""

        lines = []
        for item in messages:
            role = "User" if item["role"] == "user" else "ZORIN"
            lines.append(f"{role}: {item['content']}")

        return "\n".join(lines)[-6000:]

    def end_conversation(self):
        self.current_conversation_id = None

    # ---------------------------------------------------------
    # CORE MEMORY (Explicitly Protected)
    # ---------------------------------------------------------

    def remember_core(self, content, category="general", importance=5):
        if not content or not str(content).strip():
            return False

        self.database.save_memory(
            category=category,
            content=str(content).strip(),
            importance=importance,
            is_core=True,
            source="explicit",
            user_id=self.user_id
        )
        return True

    def get_core_memories(self, limit=500):
        return self.database.get_core_memories(limit=limit, user_id=self.user_id)

    def pin_memory(self, memory_id):
        return self.database.pin_memory(memory_id, user_id=self.user_id)

    def unpin_memory(self, memory_id):
        return self.database.unpin_memory(memory_id, user_id=self.user_id)

    # ---------------------------------------------------------
    # LONG-TERM & GENERAL MEMORY
    # ---------------------------------------------------------

    def remember(self, content, category="general", importance=1):
        if not content or not str(content).strip():
            return False

        self.database.save_memory(
            category=category,
            content=str(content).strip(),
            importance=importance,
            is_core=False,
            source="conversation",
            user_id=self.user_id
        )
        return True

    def recall(self, query, limit=20):
        if not query or not str(query).strip():
            return []

        return self.database.search_memories(
            query=str(query).strip(),
            limit=limit,
            user_id=self.user_id
        )

    def get_all_memories(self, limit=500):
        return self.database.get_all_memories(limit=limit, user_id=self.user_id)

    def update_memory(self, memory_id, new_content):
        if not new_content or not str(new_content).strip():
            return False

        return self.database.update_memory(
            memory_id=memory_id,
            new_content=str(new_content).strip(),
            user_id=self.user_id
        )

    def forget(self, memory_id, allow_core=False):
        return self.database.delete_memory(
            memory_id=memory_id,
            allow_core=allow_core,
            user_id=self.user_id
        )

    def get_persistent_memory_context(self):
        from backend.memory_service import central_memory_service
        return central_memory_service.get_persistent_memory_context(self.user_id)
