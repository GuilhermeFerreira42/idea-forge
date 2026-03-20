import pytest
from src.models.model_provider import ModelProvider
from src.agents.critic_agent import CriticAgent
from src.agents.proponent_agent import ProponentAgent
from src.conversation.conversation_manager import ConversationManager

class MockProvider(ModelProvider):
    def generate(self, prompt: str, context: list = None, role: str = "user", **kwargs) -> str:
        if role == "critic":
            return "Critique: The idea lacks scalability."
        elif role == "proponent":
            return "Defense: We will use microservices for scalability."
        return "Mock response"

def test_critic_agent():
    provider = MockProvider()
    critic = CriticAgent(provider)
    history = ConversationManager()
    
    response = critic.analyze("A new social network", history)
    assert "Critique" in response

def test_proponent_agent():
    provider = MockProvider()
    proponent = ProponentAgent(provider)
    
    response = proponent.propose("A new social network", "It lacks scalability")
    assert "Defense" in response
