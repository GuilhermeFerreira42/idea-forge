from src.models.model_provider import ModelProvider
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, SYSTEM_DESIGN_TEMPLATE, STYLE_CONTRACT
)

# Diretiva adicionada ao system prompt quando em modo direto (sem reasoning)
DIRECT_MODE_SUFFIX = (
    "\n\nIMPORTANT: Respond directly without internal reasoning blocks. "
    "Do NOT use <think> tags. Go straight to your System Design."
)


class ArchitectAgent:
    """
    Gera System Design a partir do PRD aprovado.
    Opera sob SOP com Schema Enforcement (Fase 3.1).
    """

    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self._base_system_prompt = (
            "Você é um Arquiteto de Software. "
            "Saída APENAS em Markdown estruturado, sem prosa.\n"
            "NÃO reescreva nem resuma o PRD de entrada. "
            "Use-o APENAS como fonte de requisitos.\n\n"
            f"{SYSTEM_DESIGN_TEMPLATE}\n"
            f"{ANTI_PROLIXITY_DIRECTIVE}\n"
            f"{STYLE_CONTRACT}"
        )

    @property
    def system_prompt(self) -> str:
        if self.direct_mode:
            return self._base_system_prompt + DIRECT_MODE_SUFFIX
        return self._base_system_prompt

    def design_system(self, prd_content: str, context: str = "") -> str:
        """
        Gera System Design a partir do PRD.
        
        FASE 3.1: Instrução explícita de não-repetição + formato tabular.
        """
        prompt = f"System: {self.system_prompt}\n\n"

        prompt += (
            "PRD (REFERÊNCIA — NÃO reescreva, apenas extraia requisitos):\n"
            f"{prd_content}\n\n"
        )

        if context:
            prompt += f"Contexto adicional (NÃO repita):\n{context}\n\n"

        prompt += (
            "Preencha EXATAMENTE as seções do template acima. "
            "Não adicione seções extras. Não repita dados do PRD."
        )

        return self.provider.generate(prompt=prompt, role="architect")
