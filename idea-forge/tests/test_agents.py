import pytest
from src.models.model_provider import ModelProvider
from src.agents.critic_agent import CriticAgent
from src.agents.proponent_agent import ProponentAgent
from src.conversation.conversation_manager import ConversationManager

class MockProvider(ModelProvider):
    def generate(self, prompt: str, context: list = None, role: str = "user", **kwargs) -> str:
        if role == "critic":
            return (
                "## Score de Qualidade\n8/10\n\n## Issues Identificadas\n- Falta escalabilidade horizontal\n\n"
                "## Verificação de Requisitos\n- RF01: Ok\n\n## Sumário\nBom plano.\n\n## Recomendação\nProsseguir.\n"
                "Texto longo para passar na validação de duzentos caracteres do NEXUS " * 3
            )
        elif role == "proponent":
            return "Defense: Usaremos microserviços e Redis para garantir a escalabilidade horizontal necessária. " * 5
        
        # Fallback para artefatos densos (PRD, Design, etc)
        nexus_placeholder = (
            "## Objetivo\n## Problema\n## Público-Alvo\n## Princípios Arquiteturais\n## Requisitos Funcionais\n"
            "## Requisitos Não-Funcionais\n## Escopo MVP\n## Métricas de Sucesso\n## Dependências e Riscos\n"
            "## Diferenciais\n## Constraints Técnicos\n"
            "## Arquitetura Geral\n## Tech Stack\n## Módulos\n## Modelo de Dados\n## Fluxo de Dados\n## ADRs\n## Riscos Técnicos\n"
            "## Arquitetura Sugerida\n## Módulos Core\n## Fases de Implementação\n## Riscos e Mitigações\n"
            "## Superfície de Ataque\n## Ameaças Identificadas\n## Requisitos de Segurança Derivados\n## Dados Sensíveis\n"
            "Este é um mock denso para passar na validação NEXUS. " * 20
        )
        return nexus_placeholder

def test_critic_agent():
    provider = MockProvider()
    critic = CriticAgent(provider)
    history = ConversationManager()
    
    response = critic.analyze("A new social network", history)
    assert "Score de Qualidade" in response

def test_proponent_agent():
    provider = MockProvider()
    proponent = ProponentAgent(provider)
    
    response = proponent.propose("A new social network", "It lacks scalability")
    assert "Defense" in response
