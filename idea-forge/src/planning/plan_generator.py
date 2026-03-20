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

    def generate_plan(self, first_input: str, context: str = "") -> str:
        """
        Gera plano técnico a partir do PRD e debate.
        
        FASE 5: Geração seccional.
        """
        generator = SectionalGenerator(
            provider=self.provider, 
            direct_mode=self.direct_mode
        )
        
        result = generator.generate_sectional(
            artifact_type="plan",
            user_input=first_input,
            context=context,
        )
        
        if result and len(result) > 200:
            return result
        
        return self._generate_single_pass(first_input, context)

    def _generate_single_pass(self, first_input: str, context: str = "") -> str:
        """Geração em chamada única (fallback)."""
        print("\n📋 Gerando Plano de Desenvolvimento Técnico (Fallback)...")
        
        prompt = f"System: {self.system_prompt}\n\n"
        prompt += f"INPUT:\n{first_input[:1500]}\n\n"
        
        if context:
            prompt += f"CONTEXTO:\n{context[:1000]}\n\n"
        
        prompt += "Preencha EXATAMENTE as seções do template acima."
        
        return self.provider.generate(prompt=prompt, role="planner")
