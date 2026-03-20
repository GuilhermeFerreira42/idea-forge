from src.models.model_provider import ModelProvider
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, PLAN_TEMPLATE, STYLE_CONTRACT
)

class PlanGenerator:
    """
    Transforma o resultado do debate em um plano técnico estruturado.
    Opera sob SOP com Schema Enforcement (Fase 3.1).
    """
    
    def __init__(self, provider: ModelProvider):
        self.provider = provider
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
        
        FASE 3.1: Template tabular forçado.
        """
        print("\n📋 Gerando Plano de Desenvolvimento Técnico...")
        
        prompt = (
            f"System: {self.system_prompt}\n\n"
            f"PRD e Referências:\n{first_input[:1500]}\n\n"
        )
        
        if context:
            prompt += f"Contexto do Debate/Design:\n{context[:1000]}\n\n"
        
        prompt += (
            "Preencha EXATAMENTE as seções do template. "
            "Não adicione seções extras."
        )
        
        return self.provider.generate(prompt=prompt, role="planner")
