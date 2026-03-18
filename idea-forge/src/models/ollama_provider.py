import requests
import json
import sys
from src.models.model_provider import ModelProvider, GenerationResult
from src.config.settings import OLLAMA_ENDPOINT, MODEL_NAME
from src.core.stream_handler import StreamHandler, ANSIStyle


class OllamaProvider(ModelProvider):
    """
    Local LLM provider using Ollama HTTP API.
    """

    def __init__(self, model_name: str = MODEL_NAME, 
                 endpoint: str = OLLAMA_ENDPOINT, 
                 think: bool = False,
                 show_thinking: bool = True):
        self.model_name = model_name
        self.endpoint = endpoint
        self.think = think
        self.show_thinking = show_thinking

    def generate(self, prompt: str, context: list = None, role: str = "user") -> str:
        """
        Gera resposta e retorna apenas o conteúdo limpo (sem pensamento).
        Mantém compatibilidade com contrato original.
        """
        result = self.generate_with_thinking(prompt, context, role)
        return result.content

    def generate_with_thinking(self, prompt: str, context: list = None, 
                                role: str = "user") -> GenerationResult:
        """
        Gera resposta com streaming visual e retorna resultado estruturado.
        O pensamento é exibido em tempo real (dimmed) mas separado do content.
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
        }

        # Habilitar thinking no Ollama se o modelo suporta
        if self.think:
            payload["options"] = {"think": True}

        try:
            # Emitir estado: início da geração
            sys.stdout.write(
                f"{ANSIStyle.CYAN}⏳ Gerando com {self.model_name}...{ANSIStyle.RESET}\n"
            )
            sys.stdout.flush()

            response = requests.post(
                self.endpoint, json=payload, timeout=120, stream=True
            )
            response.raise_for_status()

            # Delegar processamento ao StreamHandler
            handler = StreamHandler(show_thinking=self.show_thinking)
            result = handler.process_ollama_stream(response.iter_lines())

            return GenerationResult(
                content=result.content,
                thinking=result.thinking,
                raw=result.raw
            )

        except requests.exceptions.RequestException as e:
            error_msg = f"Error communicating with Ollama: {str(e)}"
            return GenerationResult(content=error_msg, thinking="", raw=error_msg)
