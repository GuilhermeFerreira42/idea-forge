from src.models.model_provider import ModelProvider
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, PRD_TEMPLATE, STYLE_CONTRACT
)
from src.core.sectional_generator import SectionalGenerator

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
            "Você é o Agente PRODUCT MANAGER do sistema IdeaForge.\n\n"
            "## REGRAS INVIOLÁVEIS\n"
            "1. Sua saída DEVE seguir EXATAMENTE o schema de seções abaixo.\n"
            "2. Cada requisito DEVE ter ID único (RF-XX, RNF-XX).\n"
            "3. Cada requisito DEVE ter critério de aceite VERIFICÁVEL programaticamente.\n"
            "4. NUNCA gere mais de 20 requisitos funcionais por PRD.\n"
            "5. Se faltar informação, escreva 'A DEFINIR' — NUNCA invente dados.\n"
            "6. Sua saída DEVE ser Markdown válido. Nenhum texto fora das seções.\n"
            "7. Responda em Português.\n\n"
            "## FORMATO DE SAÍDA OBRIGATÓRIO\n"
            f"{PRD_TEMPLATE}\n\n"
            "## FRAMEWORKS DE ANÁLISE APLICADOS\n"
            "- Use MOSCOW (Must/Should/Could/Won't) para priorização\n"
            "- Use critérios SMART para métricas de sucesso\n"
            "- Identifique RISCOS usando Probabilidade × Impacto\n\n"
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
        
        FASE 5: Usa geração sequencial por seções para maximizar densidade.
        Fallback para geração única se falhar.
        """
        generator = SectionalGenerator(
            provider=self.provider, 
            direct_mode=self.direct_mode
        )
        
        result = generator.generate_sectional(
            artifact_type="prd",
            user_input=idea,
            context=context,
        )
        
        if result and len(result) > 200:
            return result
        
        return self._generate_single_pass(idea, context)

    def _generate_single_pass(self, idea: str, context: str = "") -> str:
        """Geração em chamada única (fallback)."""
        from src.core.golden_examples import PRD_EXAMPLE_FRAGMENT
        
        prompt = f"System: {self.system_prompt}\n\n"
        if context:
            prompt += f"CONTEXTO (NÃO repita):\n{context}\n\n"
        prompt += PRD_EXAMPLE_FRAGMENT
        prompt += (
            f"IDEIA DO USUÁRIO:\n{idea}\n\n"
            "Preencha EXATAMENTE as seções do template acima."
        )
        return self.provider.generate(prompt=prompt, role="product_manager")
