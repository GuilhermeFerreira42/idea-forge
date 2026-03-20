from src.models.model_provider import ModelProvider
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, DEBATE_RESPONSE_TEMPLATE, STYLE_CONTRACT
)

# Diretiva adicionada ao system prompt quando em modo direto (sem reasoning)
DIRECT_MODE_SUFFIX = (
    "\n\nIMPORTANT: Respond directly without internal reasoning blocks. "
    "Do NOT use <think> tags. Go straight to your technical proposal."
)


class ProponentAgent:
    """
    Defende a solução, estrutura a proposta e responde às criticas apresentadas.
    """

    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self._base_system_prompt = (
            "Você é um Engenheiro Líder Proponente. "
            "Saída APENAS em Markdown estruturado, sem prosa.\n\n"
            f"{DEBATE_RESPONSE_TEMPLATE}\n"
            f"{ANTI_PROLIXITY_DIRECTIVE}\n"
            f"{STYLE_CONTRACT}"
        )

    @property
    def system_prompt(self) -> str:
        """
        System prompt dinâmico baseado no modo de operação.
        FASE 2: Em direct_mode, adiciona diretiva de supressão de reasoning.
        """
        if self.direct_mode:
            return self._base_system_prompt + DIRECT_MODE_SUFFIX
        return self._base_system_prompt

    def propose(self, idea: str, debate_context: str) -> str:
        """
        Formulate a defense or initial proposal given the context.
        """
        prompt = (
            f"System: {self.system_prompt}\n\n"
            f"Core Idea:\n{idea}\n\n"
            f"Current Debate Context/Critiques:\n{debate_context}\n\n"
            "Formulate your technical defense and propose a structured "
            "architectural direction:"
        )

        response = self.provider.generate(prompt=prompt, role="proponent")
        return response

    def defend_artifact(self, artifact_content: str, critique: str, context: str = "") -> str:
        """
        FASE 3.1: Defende artefato com formato bullet/tabela forçado.
        """
        defense_prompt = (
            f"System: {self.system_prompt}\n\n"
            f"ARTEFATO:\n{artifact_content[:1000]}\n\n"
            f"CRÍTICA RECEBIDA:\n{critique[:500]}\n\n"
        )

        if context:
            defense_prompt += f"Contexto adicional (NÃO repita):\n{context}\n\n"

        defense_prompt += (
            "Responda APENAS com:\n"
            "## Pontos Aceitos\n"
            "- [ponto da crítica que é válido]\n\n"
            "## Defesa Técnica\n"
            "- [argumento técnico]\n\n"
            "## Melhorias Propostas\n"
            "| Área | Mudança | Justificativa |\n"
            "|---|---|---|\n"
        )

        return self.provider.generate(prompt=defense_prompt, role="proponent")
