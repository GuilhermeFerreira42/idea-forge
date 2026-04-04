"""
prompt_profiles.py — Perfis de prompt calibrados por faixa de modelo.

Fase 9.7 (Onda 3 — W3-01): Alternância automática entre prompts curtos
(few-shot agressivo para 1B) e prompts descritivos (SOP completo para 20B+).

REGRAS DESTE MÓDULO:
- Zero imports de src.*
- Todos os perfis são frozen dataclasses (imutáveis)
- detect_range() é determinístico: mesma entrada → mesma saída sempre
- Ordem de avaliação SMALL antes de MEDIUM (evitar falso-positivo)
"""

from dataclasses import dataclass
from typing import Literal, List


# ---------------------------------------------------------------------------
# Tipo de faixa de modelo
# ---------------------------------------------------------------------------
ModelRange = Literal["SMALL", "MEDIUM", "LARGE"]
SystemPromptMode = Literal["FEW_SHOT", "HYBRID", "FULL_SOP"]


# ---------------------------------------------------------------------------
# Dataclass de perfil (frozen = imutável)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PromptProfile:
    """
    Perfil imutável de configuração de prompt por faixa de modelo.

    Invariantes:
    - max_output_tokens >= retry_max_tokens
    - use_atomic_decomposition == True implica max_output_tokens <= 400
    - model_range == "LARGE" implica system_prompt_mode == "FULL_SOP"
    """
    model_range: ModelRange
    max_output_tokens: int          # Tokens máximos por chamada ao provider
    retry_max_tokens: int           # Tokens máximos no retry Nível 2
    system_prompt_mode: SystemPromptMode
    max_exemplar_chars: int         # Tamanho máximo do exemplar injetado
    max_context_chars: int          # Tamanho máximo do contexto injetado
    inline_examples_count: int      # Exemplos inline no prompt (0 = usa arquivo)
    use_atomic_decomposition: bool  # True = ativa AtomicTaskDecomposer
    input_budget_override: int      # Override do input_budget do SectionPass


# ---------------------------------------------------------------------------
# Palavras-chave para detecção de faixa
# Avaliadas em ORDEM: SMALL → MEDIUM → LARGE (default)
# ---------------------------------------------------------------------------

# Modelos de 1B a 2B de parâmetros
_SMALL_KEYWORDS: List[str] = [
    "1b", "1.5b", "0.5b", "0.6b",
    "gemma3:1b", "gemma:2b", "gemma2:2b",
    "phi3:mini", "phi-3-mini",
    "qwen2.5:1b", "qwen2.5:1.5b", "qwen2:1.5b",
    "tinyllama", "smollm",
]

# Modelos de 3B a 7B de parâmetros
_MEDIUM_KEYWORDS: List[str] = [
    "3b", "3.8b", "4b",
    "qwen2.5:3b", "qwen2:3b",
    "phi3:3b", "phi-3-small",
    "gemma:7b", "gemma2:9b", "gemma3:4b",
    "llama3.2:3b", "mistral:7b",
]


# ---------------------------------------------------------------------------
# Perfis concretos
# ---------------------------------------------------------------------------

PROFILE_SMALL = PromptProfile(
    model_range="SMALL",
    max_output_tokens=400,       # Janela segura para modelos 1B com saída limitada
    retry_max_tokens=300,        # Retry ainda mais curto para não travar
    system_prompt_mode="FEW_SHOT",
    max_exemplar_chars=150,      # Exemplar mínimo: apenas 2-3 linhas de tabela
    max_context_chars=800,       # Contexto total de projeto muito comprimido
    inline_examples_count=2,     # 2 exemplos inline direto no prompt
    use_atomic_decomposition=True,
    input_budget_override=400,   # Override do input_budget de cada SectionPass
)

PROFILE_MEDIUM = PromptProfile(
    model_range="MEDIUM",
    max_output_tokens=800,       # Janela para modelos 3B (conservador)
    retry_max_tokens=600,
    system_prompt_mode="HYBRID", # SOP resumido + 1 exemplo inline
    max_exemplar_chars=400,
    max_context_chars=1600,
    inline_examples_count=1,
    use_atomic_decomposition=False,
    input_budget_override=800,
)

PROFILE_LARGE = PromptProfile(
    model_range="LARGE",
    max_output_tokens=2500,      # Equivalente ao comportamento pré-fase 9.7
    retry_max_tokens=1500,       # Equivalente ao max_tokens=1500 do Nível 2 atual
    system_prompt_mode="FULL_SOP",
    max_exemplar_chars=1200,     # Exemplares completos dos arquivos exemplars/
    max_context_chars=3000,      # input_budget=3000 dos SectionPass atuais
    inline_examples_count=0,     # Usa exemplar files — sem inline
    use_atomic_decomposition=False,
    input_budget_override=3000,  # Preserva comportamento atual
)

# Mapeamento de range → profile (único ponto de verdade)
_PROFILE_MAP = {
    "SMALL": PROFILE_SMALL,
    "MEDIUM": PROFILE_MEDIUM,
    "LARGE": PROFILE_LARGE,
}


# ---------------------------------------------------------------------------
# Classe de API pública
# ---------------------------------------------------------------------------

class PromptProfiles:
    """
    Factory e detector de perfis de prompt por faixa de modelo.

    Uso:
        range_ = PromptProfiles.detect_range("qwen2.5:3b")  # → "MEDIUM"
        profile = PromptProfiles.get_profile(range_)         # → PROFILE_MEDIUM
    """

    @staticmethod
    def detect_range(model_name: str) -> ModelRange:
        """
        Detecta a faixa do modelo pelo nome.

        Regras (avaliadas em ordem):
        1. Se model_name é None ou vazio → "LARGE" (conservador)
        2. Se qualquer keyword de SMALL_KEYWORDS é substring → "SMALL"
        3. Se qualquer keyword de MEDIUM_KEYWORDS é substring → "MEDIUM"
        4. Default → "LARGE"

        Args:
            model_name: Nome do modelo conforme registrado no Ollama.
                        Ex: "qwen2.5:3b", "gpt-oss:20b-cloud"

        Returns:
            Literal["SMALL", "MEDIUM", "LARGE"]
        """
        if not model_name:
            return "LARGE"

        name_lower = model_name.lower()

        # Avaliação SMALL primeiro (evita falso-positivo em "qwen2.5:1.5b" → MEDIUM)
        for keyword in _SMALL_KEYWORDS:
            if keyword in name_lower:
                return "SMALL"

        for keyword in _MEDIUM_KEYWORDS:
            if keyword in name_lower:
                return "MEDIUM"

        return "LARGE"

    @staticmethod
    def get_profile(model_range: ModelRange) -> PromptProfile:
        """
        Retorna o perfil correspondente à faixa.

        Args:
            model_range: "SMALL", "MEDIUM" ou "LARGE"

        Returns:
            PromptProfile imutável

        Raises:
            ValueError: Se model_range não é um dos três valores válidos
        """
        profile = _PROFILE_MAP.get(model_range)
        if profile is None:
            raise ValueError(
                f"model_range inválido: '{model_range}'. "
                f"Valores permitidos: {list(_PROFILE_MAP.keys())}"
            )
        return profile

    @staticmethod
    def from_model_name(model_name: str) -> PromptProfile:
        """
        Atalho: detecta faixa e retorna perfil em uma chamada.

        Args:
            model_name: Nome do modelo

        Returns:
            PromptProfile correspondente
        """
        range_ = PromptProfiles.detect_range(model_name)
        return PromptProfiles.get_profile(range_)
