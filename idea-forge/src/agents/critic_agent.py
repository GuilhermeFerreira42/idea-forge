from src.models.model_provider import ModelProvider
from src.conversation.conversation_manager import ConversationManager

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
            "Você é um Arquiteto de Software Sênior altamente analítico, "
            "conhecido por suas críticas rigorosas. "
            "Seu trabalho é analisar ideias de projetos/startups e encontrar "
            "lacunas estruturais, componentes "
            "ausentes, requisitos pouco claros e possíveis pontos de falha. "
            "NÃO resolva os problemas. Faça perguntas incisivas e aponte os riscos. "
            "Seja direto e técnico, evite introduções prolixas. Seja pragmático."
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
        NOVO (Fase 3): Analisa um artefato específico (PRD, System Design, etc) do Blackboard.
        """
        prompt = (
            f"System: {self.system_prompt}\n\n"
            f"Reviewing Artifact Type: {artifact_type}\n"
            f"Artifact Content:\n{artifact_content}\n\n"
            f"Additional context from Blackboard:\n{context}\n\n"
            "Perform a rigorous technical review of this artifact, pointing out risks and gaps:"
        )

        response = self.provider.generate(
            prompt=prompt, role="critic"
        )
        return response
