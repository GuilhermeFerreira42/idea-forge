from abc import ABC, abstractmethod

class ModelProvider(ABC):
    """
    Interface base for all LLM providers (Local and Cloud).
    """

    @abstractmethod
    def generate(self, prompt: str, context: list = None, role: str = "user") -> str:
        """
        Generates text based on prompt and conversation context.
        """
        pass
