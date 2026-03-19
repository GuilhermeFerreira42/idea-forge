import pytest
from src.agents.product_manager_agent import ProductManagerAgent
from src.agents.architect_agent import ArchitectAgent
from src.models.model_provider import ModelProvider

class MockProvider:
    def generate(self, prompt, role, context=None):
        if role == "product_manager":
            return "# PRD Output"
        if role == "architect":
            return "# System Design Output"
        return "Generic Output"

def test_product_manager_agent():
    provider = MockProvider()
    agent = ProductManagerAgent(provider)
    prd = agent.generate_prd("My Idea", "Some context")
    assert "# PRD Output" in prd

def test_architect_agent():
    provider = MockProvider()
    agent = ArchitectAgent(provider)
    design = agent.design_system("PRD CONTENT", "Some context")
    assert "# System Design Output" in design

def test_agents_direct_mode():
    provider = MockProvider()
    pm = ProductManagerAgent(provider, direct_mode=True)
    arch = ArchitectAgent(provider, direct_mode=True)
    
    assert "Respond directly without internal reasoning blocks" in pm.system_prompt
    assert "Respond directly without internal reasoning blocks" in arch.system_prompt
