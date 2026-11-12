from memory.database import Database


class MemoryManager:

    def __init__(self):

        self.database = Database()

        self.current_conversation_id = None

    # CONVERSATION MANAGEMENT

    def start_conversation(self, title="New Conversation"):

        self.current_conversation_id = (
            self.database.create_conversation(title)
        )

        return self.current_conversation_id

    def add_message(self, role, content):

        if not content or not content.strip():
            return

        if self.current_conversation_id is None:
            self.start_conversation()

        self.database.save_message(
            self.current_conversation_id,
            role,
            content.strip()
        )

    def get_recent_context(self, limit=20):

        if self.current_conversation_id is None:
            return []

        return self.database.get_recent_messages(
            self.current_conversation_id,
            limit
        )

    def get_past_conversation_context(self, limit=30):

        messages = (
            self.database.get_recent_conversation_messages(limit)
        )

        if not messages:
            return ""

        lines = []

        for item in messages:

            role = (
                "User"
                if item["role"] == "user"
                else "ZORIN"
            )

            lines.append(
                f"{role}: {item['content']}"
            )

        return "\n".join(lines)[-6000:]

    # CORE MEMORY

    def remember_core(
        self,
        content,
        category="general",
        importance=5
    ):

        if not content or not content.strip():
            return False

        self.database.save_memory(
            category=category,
            content=content.strip(),
            importance=importance,
            is_core=True,
            source="explicit"
        )

        return True

    def get_core_memories(self, limit=500):

        return self.database.get_core_memories(limit)

    def pin_memory(self, memory_id):

        return self.database.pin_memory(memory_id)

    def unpin_memory(self, memory_id):

        return self.database.unpin_memory(memory_id)

    # LONG-TERM MEMORY

    def remember(
        self,
        content,
        category="general",
        importance=1
    ):

        if not content or not content.strip():
            return False

        self.database.save_memory(
            category=category,
            content=content.strip(),
            importance=importance,
            is_core=False,
            source="conversation"
        )

        return True

    def recall(self, query, limit=20):

        if not query or not query.strip():
            return []

        return self.database.search_memories(
            query.strip(),
            limit
        )

    def get_all_memories(self, limit=500):

        return self.database.get_all_memories(limit)

    def update_memory(self, memory_id, new_content):

        if not new_content or not new_content.strip():
            return False

        return self.database.update_memory(
            memory_id,
            new_content.strip()
        )

    def forget(self, memory_id, allow_core=False):

        return self.database.delete_memory(
            memory_id,
            allow_core=allow_core
        )

    def end_conversation(self):

        self.current_conversation_id = None

    def get_persistent_memory_context(self):

        core_memories = self.get_core_memories()

        other_memories = [
            memory
            for memory in self.get_all_memories()
            if not memory["is_core"]
        ]

        sections = []

        if core_memories:

            sections.append("PROTECTED CORE MEMORIES:")

            for memory in core_memories:

                sections.append(
                    f"- [{memory['category']}] "
                    f"{memory['content']}"
                )

        if other_memories:

            sections.append("LONG-TERM MEMORIES:")

            for memory in other_memories:

                sections.append(
                    f"- [{memory['category']}] "
                    f"{memory['content']}"
                )

        return "\n".join(sections)