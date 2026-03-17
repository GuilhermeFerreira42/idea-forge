from src.models.model_provider import ModelProvider
from src.conversation.conversation_manager import ConversationManager

class CriticAgent:
    """
    Analisa ideias e encontra problemas, lacunas e vulnerabilidades estruturais.
    """
    
    def __init__(self, provider: ModelProvider):
        self.provider = provider
        self.system_prompt = (
            "Você é um Arquiteto de Software Sênior altamente analítico, conhecido por suas críticas rigorosas. "
            "Seu trabalho é analisar ideias de projetos/startups e encontrar lacunas estruturais, componentes "
            "ausentes, requisitos pouco claros e possíveis pontos de falha. "
            "NÃO resolva os problemas. Faça perguntas incisivas e aponte os riscos. "
            "Seja direto e técnico, evite introduções prolixas. Seja pragmático."
        )

    def analyze(self, idea: str, history: ConversationManager) -> str:
        """
        Analyze the idea and return a critique based on history.
        """
        prompt = (
            f"System: {self.system_prompt}\n\n"
            f"History Context:\n{history.get_context_string()}\n\n"
            f"Analyze this specific concept/idea:\n{idea}\n\n"
            "Provide your critique highlighting gaps and asking technical questions:"
        )
        
        response = self.provider.generate(prompt=prompt, context=history.get_history(), role="critic")
        return response
