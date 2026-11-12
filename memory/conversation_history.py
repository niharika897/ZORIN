from memory.memory_manager import MemoryManager


class ConversationHistory:

    def __init__(self):

        self.memory = MemoryManager()

    def start(self, title="New Conversation"):

        return self.memory.start_conversation(title)

    def add_user_message(self, message):

        self.memory.add_message("user", message)

    def add_assistant_message(self, message):

        self.memory.add_message("assistant", message)

    def get_history(self, limit=20):

        return self.memory.get_recent_context(limit)

    def end(self):

        self.memory.current_conversation_id = None

    def get_current_conversation_id(self):

        return self.memory.current_conversation_id
