from src.models.model_provider import ModelProvider

# Diretiva adicionada ao system prompt quando em modo direto (sem reasoning)
DIRECT_MODE_SUFFIX = (
    "\n\nIMPORTANT: Respond directly without internal reasoning blocks. "
    "Do NOT use <think> tags. Go straight to your PRD."
)

class ProductManagerAgent:
    """
    Gera PRD (Product Requirements Document) a partir da ideia bruta.
    Responsável por definir o escopo, objetivos e requisitos do produto.
    """

    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self._base_system_prompt = (
            "Você é um Product Manager Sênior focado em clareza e execução. "
            "Seu trabalho é transformar ideias brutas em um Product Requirements Document (PRD) "
            "estruturado e denso. "
            "O PRD deve incluir: Objetivos do Produto, Personas, Requisitos Funcionais, "
            "Requisitos Não Funcionais e Escopo (O que está dentro e o que está fora). "
            "Seja pragmático, evite jargões desnecessários e foque no valor de negócio."
        )

    @property
    def system_prompt(self) -> str:
        if self.direct_mode:
            return self._base_system_prompt + DIRECT_MODE_SUFFIX
        return self._base_system_prompt

    def generate_prd(self, idea: str, context: str = "") -> str:
        """
        Gera um PRD a partir da ideia e do contexto (se houver).
        """
        prompt = (
            f"System: {self.system_prompt}\n\n"
            f"Idea:\n{idea}\n\n"
            f"Context (Decisions/Refinements):\n{context}\n\n"
            "Generate a complete PRD in Markdown format:"
        )

        response = self.provider.generate(
            prompt=prompt, role="product_manager"
        )
        return response
