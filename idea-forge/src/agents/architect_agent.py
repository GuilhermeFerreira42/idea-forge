from src.models.model_provider import ModelProvider

# Diretiva adicionada ao system prompt quando em modo direto (sem reasoning)
DIRECT_MODE_SUFFIX = (
    "\n\nIMPORTANT: Respond directly without internal reasoning blocks. "
    "Do NOT use <think> tags. Go straight to your System Design."
)

class ArchitectAgent:
    """
    Gera System Design a partir do PRD aprovado.
    Responsável pela arquitetura técnica, escolha de stack e design de módulos.
    """

    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self._base_system_prompt = (
            "Você é um Arquiteto de Software Líder especializado em sistemas escaláveis. "
            "Seu trabalho é pegar um PRD e desenhar uma arquitetura técnica robusta. "
            "O System Design deve incluir: Visão Geral da Arquitetura, Escolha de Stack, "
            "Design de Módulos/Componentes, Modelo de Dados/Entidades e Fluxo de Dados. "
            "Foque em simplicidade, mantenibilidade e performance. Seja técnico e direto."
        )

    @property
    def system_prompt(self) -> str:
        if self.direct_mode:
            return self._base_system_prompt + DIRECT_MODE_SUFFIX
        return self._base_system_prompt

    def design_system(self, prd_content: str, context: str = "") -> str:
        """
        Gera o design do sistema a partir do PRD.
        """
        prompt = (
            f"System: {self.system_prompt}\n\n"
            f"PRD Content:\n{prd_content}\n\n"
            f"Additional Context:\n{context}\n\n"
            "Generate a complete System Design document in Markdown format:"
        )

        response = self.provider.generate(
            prompt=prompt, role="architect"
        )
        return response
