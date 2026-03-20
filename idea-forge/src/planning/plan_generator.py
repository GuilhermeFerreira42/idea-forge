from src.models.model_provider import ModelProvider
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, PLAN_TEMPLATE, STYLE_CONTRACT
)
from src.core.sectional_generator import SectionalGenerator

class PlanGenerator:
    """
    Transforma o resultado do debate em um plano técnico estruturado.
    Opera sob SOP com Schema Enforcement (Fase 3.1).
    """
    
    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self.system_prompt = (
            "Você é um Tech Lead. "
            "Saída APENAS em Markdown estruturado, sem prosa.\n\n"
            f"{PLAN_TEMPLATE}\n"
            f"{ANTI_PROLIXITY_DIRECTIVE}\n"
            f"{STYLE_CONTRACT}"
        )

    def generate_plan(self, prd_system_security: str, context: str = "") -> str:
        """
        FASE 5.1: Geração de Plano de Desenvolvimento seccional (2 passes).
        """
        generator = SectionalGenerator(
            provider=self.provider, 
            direct_mode=self.direct_mode
        )
        
        result = generator.generate_sectional(
            artifact_type="plan",
            user_input=prd_system_security,
            context=context
        )
        
        if result and len(result) > 200:
            return result
            
        # Fallback: chamada única
        return self._generate_single_pass(prd_system_security, context)

    def _generate_single_pass(self, prd_system_security: str, context: str) -> str:
        """Fallback de plano em chamada única."""
        from src.core.golden_examples import PLAN_EXAMPLE_FRAGMENT
        
        prompt = (
            f"System: {self.system_prompt}\n\n"
            f"INPUTS (PRD + DESIGN + SECURITY):\n{prd_system_security}\n\n"
        )
        if context:
            prompt += f"CONTEXTO ADICIONAL:\n{context}\n\n"
            
        prompt += PLAN_EXAMPLE_FRAGMENT
        prompt += "\nPreencha EXATAMENTE as seções do template de plano acima."
        
        return self.provider.generate(prompt=prompt, role="planner")
