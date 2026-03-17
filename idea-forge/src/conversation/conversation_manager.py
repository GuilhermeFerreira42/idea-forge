from typing import List, Dict

class ConversationManager:
    """
    Manages the context and history of interactions.
    """

    def __init__(self):
        self._history: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str):
        """Append a generic message to the conversation."""
        self._history.append({"role": role, "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        """Return the current conversation history."""
        return self._history

    def get_context_string(self) -> str:
        """Format the history into a single string context."""
        context = ""
        for msg in self._history:
            context += f"[{msg['role'].upper()}]: {msg['content']}\n\n"
        return context

    def reset(self):
        """Clear conversation history."""
        self._history.clear()
