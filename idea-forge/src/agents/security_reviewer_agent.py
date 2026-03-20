"""
security_reviewer_agent.py — Agente de Revisão de Segurança (Hardening).

Responsabilidade:
Analisar System Design para ameaças de segurança usando STRIDE simplificado.
Produzir relatório de ameaças com mitigações concretas.

Contrato:
    Input: System Design (string) + PRD (string para contexto)
    Output: Security Review em Markdown com tabela de ameaças
"""
from src.models.model_provider import ModelProvider
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, SECURITY_REVIEW_TEMPLATE, STYLE_CONTRACT
)
from src.core.golden_examples import SECURITY_EXAMPLE_FRAGMENT

DIRECT_MODE_SUFFIX = (
    "\n\nIMPORTANT: Respond directly without internal reasoning blocks. "
    "Do NOT use <think> tags. Go straight to your security analysis."
)

class SecurityReviewerAgent:
    """
    Analisa artefatos de design para ameaças de segurança.
    Opera sob STRIDE simplificado.
    """
    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self._base_system_prompt = (
            "Você é o Agente de SEGURANÇA do sistema IdeaForge.\n\n"
            "## REGRAS INVIOLÁVEIS\n"
            "1. Analise CADA componente do System Design contra STRIDE.\n"
            "2. Cada ameaça DEVE ter: categoria, componente afetado, "
            "severidade, mitigação concreta.\n"
            "3. NUNCA ignore autenticação, autorização ou validação de input.\n"
            "4. Se o design não menciona criptografia de dados sensíveis, "
            "isso é automaticamente uma ameaça HIGH.\n"
            "5. Responda em Português.\n\n"
            "## CATEGORIAS STRIDE\n"
            "- S: Spoofing (falsificação de identidade)\n"
            "- T: Tampering (adulteração de dados)\n"
            "- R: Repudiation (negação de ações)\n"
            "- I: Information Disclosure (vazamento de dados)\n"
            "- D: Denial of Service (indisponibilidade)\n"
            "- E: Elevation of Privilege (escalonamento)\n\n"
            "## FORMATO DE SAÍDA OBRIGATÓRIO\n"
            f"{SECURITY_REVIEW_TEMPLATE}\n\n"
            f"{ANTI_PROLIXITY_DIRECTIVE}\n"
            f"{STYLE_CONTRACT}"
        )

    @property
    def system_prompt(self) -> str:
        if self.direct_mode:
            return self._base_system_prompt + DIRECT_MODE_SUFFIX
        return self._base_system_prompt

    def review_security(self, system_design: str, prd_context: str = "") -> str:
        """
        Analisa System Design para ameaças de segurança.
        """
        prompt = f"System: {self.system_prompt}\n\n"
        
        # FASE 4: Injeção de golden example
        prompt += SECURITY_EXAMPLE_FRAGMENT
        
        if prd_context:
            prompt += (
                "PRD (REFERÊNCIA — NÃO repita):\n"
                f"{prd_context[:500]}\n\n"
            )
        prompt += (
            f"SYSTEM DESIGN PARA ANÁLISE:\n{system_design}\n\n"
            "Preencha EXATAMENTE as seções do template de segurança."
        )
        return self.provider.generate(prompt=prompt, role="security_reviewer")
