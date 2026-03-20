from abc import ABC, abstractmethod
from typing import NamedTuple, Optional


class GenerationResult(NamedTuple):
    """Resultado estruturado de uma geração de LLM."""
    content: str          # Resposta final limpa
    thinking: str         # Raciocínio capturado (vazio se não disponível)
    raw: str              # Output bruto completo


class ModelProvider(ABC):
    """
    Interface base for all LLM providers (Local and Cloud).
    """

    @abstractmethod
    def generate(self, prompt: str, context: list = None, 
                 role: str = "user", max_tokens: Optional[int] = None) -> str:
        """
        Generates text based on prompt and conversation context.
        Returns clean content string (backward compatible).
        """
        pass

    def generate_with_thinking(self, prompt: str, context: list = None, 
                                role: str = "user", 
                                max_tokens: Optional[int] = None) -> GenerationResult:
        """
        Generates text and returns structured result with thinking separated.
        Default implementation wraps generate() for providers that don't support thinking.
        """
        content = self.generate(prompt, context, role, max_tokens=max_tokens)
        return GenerationResult(content=content, thinking="", raw=content)
