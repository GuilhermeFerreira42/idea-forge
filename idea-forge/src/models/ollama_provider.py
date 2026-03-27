import requests
import json
import sys
from typing import Optional
from src.models.model_provider import ModelProvider, GenerationResult
from src.config.settings import OLLAMA_ENDPOINT, MODEL_NAME
from src.core.stream_handler import StreamHandler, ANSIStyle

# Diretiva injetada no topo do prompt quando reasoning está desativado na Fase 2.
# O objetivo é desencorajar o raciocínio interno sem causar falhas catastróficas em modelos pequenos.
DIRECT_RESPONSE_DIRECTIVE = (
    "Por favor, responda diretamente em Português. "
    "Não utilize blocos de pensamento ou tags <think>. "
    "Vá direto para a análise técnica solicitada.\n\n"
)

# Modelos que possuem reasoning intrínseco e se beneficiam
# da flag think: false + diretiva de supressão
REASONING_MODEL_KEYWORDS = ["qwen", "deepseek", "r1", "reasoning"]


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
        # Detectar se o modelo é da família reasoning
        self._is_reasoning_model = any(
            kw in model_name.lower() for kw in REASONING_MODEL_KEYWORDS
        )

    def generate(self, prompt: str, context: list = None, 
                 role: str = "user", max_tokens: Optional[int] = None) -> str:
        """
        Gera resposta e retorna apenas o conteúdo limpo (sem pensamento).
        Mantém compatibilidade com contrato original.
        """
        result = self.generate_with_thinking(prompt, context, role, max_tokens=max_tokens)
        return result.content

    def generate_with_thinking(self, prompt: str, context: list = None, 
                                role: str = "user",
                                max_tokens: Optional[int] = None) -> GenerationResult:
        """
        Gera resposta com streaming visual e retorna resultado estruturado.

        FASE 5: Adicionado suporte a max_tokens para o SectionalGenerator.
        """
        # ── Construir prompt final ──
        final_prompt = self._build_prompt(prompt)

        # ── Construir payload ──
        payload = {
            "model": self.model_name,
            "prompt": final_prompt,
            "stream": True,
        }

        # ── Configurar options com restrições técnicas (Fase 3.1 + Fase 5) ──
        if max_tokens:
            num_predict = max_tokens
        else:
            # FASE 7: Aumentar budget de tokens para suportar templates NEXUS
            num_predict = 2500 if not self.think else 5000  # era 1200/3000

        options = {
            "num_predict": num_predict,
            "temperature": 0.1 if not self.think else 0.7,
        }
        
        if self._is_reasoning_model:
            options["think"] = self.think
        elif self.think:
            # Para modelos não-reasoning que recebam think=True por engano
            options["think"] = True

        if options:
            payload["options"] = options

        # ── Timeout dinâmico ──
        timeout = 120 if self.think else 90

        try:
            # Emitir estado: início da geração
            mode_label = "reasoning" if self.think else "direto"
            sys.stdout.write(
                f"{ANSIStyle.CYAN}⏳ Gerando com {self.model_name} "
                f"(modo {mode_label})...{ANSIStyle.RESET}\n"
            )
            sys.stdout.flush()

            response = requests.post(
                self.endpoint, json=payload, timeout=timeout, stream=True
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

    def _build_prompt(self, original_prompt: str) -> str:
        """
        Constrói o prompt final baseado no modo de operação.

        FASE 2: Se think=False E o modelo é da família reasoning,
        injeta a diretiva DIRECT_RESPONSE_DIRECTIVE no topo do prompt
        para instruir o modelo a não usar raciocínio interno.
        """
        if not self.think and self._is_reasoning_model:
            return DIRECT_RESPONSE_DIRECTIVE + original_prompt
        return original_prompt
