from src.models.model_provider import ModelProvider

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
            "Você é um Engenheiro Líder visionário, porém prático. "
            "Seu trabalho é pegar uma ideia crua ou criticada e formular "
            "uma proposta técnica "
            "forte, estruturada e viável. "
            "Defenda suas escolhas arquiteturais contra críticas, mas esteja "
            "disposto a incorporar "
            "preocupações válidas em um design melhor. Seja confiante e técnico. "
            "Seja direto e técnico, evite introduções prolixas."
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
