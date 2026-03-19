from src.models.model_provider import ModelProvider

class PlanGenerator:
    """
    Transforma o resultado do debate em um plano técnico estruturado.
    """
    
    def __init__(self, provider: ModelProvider):
        self.provider = provider
        self.system_prompt = (
            "You are a Technical Lead and Project Manager. "
            "Your job is to read a debate transcript between technical agents "
            "and synthesize a final, actionable 'Development Plan'. "
            "The plan MUST include:\n"
            "- Suggested Architecture\n"
            "- Core Modules / Components\n"
            "- Implementation Phases (Step-by-step)\n"
            "- Technical Responsibilities and Risks"
        )

    def generate_plan(self, first_input: str, context: str = "") -> str:
        """
        Generate final development plan markdown based on the debate outcome and artifacts.
        first_input: Usually the PRD.
        context: Context from System Design and Debate Transcript.
        """
        print("\n⏳ Gerando Plano de Desenvolvimento Técnico Consolidado...")
        
        prompt = (
            f"System: {self.system_prompt}\n\n"
            f"Main Concept (PRD):\n{first_input}\n\n"
            f"Context (Architecture & Debate):\n{context}\n\n"
            "Produce the final Markdown development plan:"
        )
        
        response = self.provider.generate(prompt=prompt, role="planner")
        return response
