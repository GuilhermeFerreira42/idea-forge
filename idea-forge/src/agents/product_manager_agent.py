from src.models.model_provider import ModelProvider
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, PRD_TEMPLATE, STYLE_CONTRACT
)

# Diretiva adicionada ao system prompt quando em modo direto (sem reasoning)
DIRECT_MODE_SUFFIX = (
    "\n\nIMPORTANT: Respond directly without internal reasoning blocks. "
    "Do NOT use <think> tags. Go straight to your PRD."
)

class ProductManagerAgent:
    """
    Gera PRD (Product Requirements Document) a partir da ideia bruta.
    Opera sob SOP com Schema Enforcement (Fase 3.1).
    """

    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self._base_system_prompt = (
            "Você é um Product Manager técnico. "
            "Saída APENAS em Markdown estruturado, sem prosa.\n\n"
            f"{PRD_TEMPLATE}\n"
            f"{ANTI_PROLIXITY_DIRECTIVE}\n"
            f"{STYLE_CONTRACT}"
        )

    @property
    def system_prompt(self) -> str:
        if self.direct_mode:
            return self._base_system_prompt + DIRECT_MODE_SUFFIX
        return self._base_system_prompt

    def generate_prd(self, idea: str, context: str = "") -> str:
        """
        Gera PRD a partir da ideia do usuário.
        
        FASE 3.1: Instrução determinística — "preencha o template",
        não "gere um documento completo".
        """
        prompt = f"System: {self.system_prompt}\n\n"

        if context:
            prompt += (
                "CONTEXTO (NÃO repita, apenas use como referência):\n"
                f"{context}\n\n"
            )

        prompt += (
            f"IDEIA DO USUÁRIO:\n{idea}\n\n"
            "Preencha EXATAMENTE as seções do template acima com base na ideia. "
            "Não adicione seções extras. Não escreva introduções."
        )

        return self.provider.generate(prompt=prompt, role="product_manager")
