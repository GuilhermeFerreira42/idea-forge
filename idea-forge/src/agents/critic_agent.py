from src.models.model_provider import ModelProvider
from src.conversation.conversation_manager import ConversationManager
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, REVIEW_TEMPLATE, STYLE_CONTRACT
)

# Diretiva adicionada ao system prompt quando em modo direto (sem reasoning)
DIRECT_MODE_SUFFIX = (
    "\n\nIMPORTANT: Respond directly without internal reasoning blocks. "
    "Do NOT use <think> tags. Go straight to your critique."
)


class CriticAgent:
    """
    Analisa ideias e encontra problemas, lacunas e vulnerabilidades estruturais.
    """

    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self._base_system_prompt = (
            "Você é um Arquiteto de Software Sênior Crítico. "
            "Saída APENAS em Markdown estruturado, sem prosa.\n\n"
            f"{REVIEW_TEMPLATE}\n"
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

    def analyze(self, idea: str, history: ConversationManager) -> str:
        """
        Analyze the idea and return a critique based on history.
        """
        prompt = (
            f"System: {self.system_prompt}\n\n"
            f"History Context:\n{history.get_context_string()}\n\n"
            f"Analyze this specific concept/idea:\n{idea}\n\n"
            "Provide your critique highlighting gaps and asking technical questions:"
        )

        response = self.provider.generate(
            prompt=prompt, context=history.get_history(), role="critic"
        )
        return response

    def review_artifact(self, artifact_content: str, artifact_type: str = "document", context: str = "") -> str:
        """
        FASE 3.1: Analisa artefato com formato de lista/tabela forçado.
        """
        review_prompt = (
            f"System: {self.system_prompt}\n\n"
            f"ARTEFATO PARA REVISÃO (tipo: {artifact_type}):\n"
            f"{artifact_content}\n\n"
        )

        if context:
            review_prompt += (
                "CONTEXTO ADICIONAL (NÃO repita):\n"
                f"{context}\n\n"
            )

        review_prompt += (
            "Preencha EXATAMENTE as seções do template de revisão acima. "
            "NÃO escreva introduções ou conclusões."
        )

        return self.provider.generate(prompt=review_prompt, role="critic")
