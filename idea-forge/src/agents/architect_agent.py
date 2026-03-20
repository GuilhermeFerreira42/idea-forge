from src.models.model_provider import ModelProvider
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, SYSTEM_DESIGN_TEMPLATE, STYLE_CONTRACT
)
from src.core.sectional_generator import SectionalGenerator

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
            "Você é o Agente ARQUITETO do sistema IdeaForge.\n\n"
            "## REGRAS INVIOLÁVEIS\n"
            "1. NÃO repita informações do PRD — referencie por ID (RF-XX).\n"
            "2. Cada decisão de design DEVE ter alternativa rejeitada + justificativa.\n"
            "3. Cada risco técnico DEVE ter probabilidade (Alta/Média/Baixa) + mitigação.\n"
            "4. O modelo de dados DEVE ser normalizável e incluir relações explícitas.\n"
            "5. O fluxo de dados DEVE ser numerado sequencialmente.\n"
            "6. Sua saída DEVE ser Markdown válido seguindo o schema abaixo.\n"
            "7. Responda em Português.\n\n"
            "## FRAMEWORKS DE ANÁLISE\n"
            "- Use C4 Model (Context/Container/Component) para descrever arquitetura\n"
            "- Documente decisões como ADRs: Contexto → Decisão → Consequências\n"
            "- Aplique STRIDE simplificado para ameaças: Spoofing, Tampering,\n"
            "  Repudiation, Information Disclosure, DoS, Elevation of Privilege\n\n"
            "## FORMATO DE SAÍDA OBRIGATÓRIO\n"
            f"{SYSTEM_DESIGN_TEMPLATE}\n\n"
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
        Gera System Design a partir do PRD aprovado.
        
        FASE 5: Geração seccional para maximizar densidade técnica.
        """
        generator = SectionalGenerator(
            provider=self.provider, 
            direct_mode=self.direct_mode
        )
        
        result = generator.generate_sectional(
            artifact_type="system_design",
            user_input=prd_content,
            context=context,
        )
        
        if result and len(result) > 200:
            return result
        
        return self._generate_single_pass(prd_content, context)

    def _generate_single_pass(self, prd_content: str, context: str = "") -> str:
        """Geração em chamada única (fallback)."""
        from src.core.golden_examples import DESIGN_EXAMPLE_FRAGMENT
        
        prompt = f"System: {self.system_prompt}\n\n"
        prompt += f"PRD (REFERÊNCIA):\n{prd_content[:1500]}\n\n"
        
        if context:
            prompt += f"Contexto adicional:\n{context}\n\n"
        
        prompt += DESIGN_EXAMPLE_FRAGMENT
        prompt += "Preencha EXATAMENTE as seções do template acima."
        
        return self.provider.generate(prompt=prompt, role="architect")
