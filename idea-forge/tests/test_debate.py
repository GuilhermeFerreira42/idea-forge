import pytest
from tests.test_agents import MockProvider
from src.agents.critic_agent import CriticAgent
from src.agents.proponent_agent import ProponentAgent
from src.debate.debate_engine import DebateEngine

def test_debate_engine_execution():
    provider = MockProvider()
    critic = CriticAgent(provider)
    proponent = ProponentAgent(provider)
    
    # Run a 2-round debate for testing speed
    engine = DebateEngine(proponent, critic, rounds=2)
    result = engine.run("A new social network")
    
    assert "Proponente:" in result
    assert "Crítico:" in result
    assert "Defense" in result
    assert "Score de Qualidade" in result
    
    # Engine records (2 rounds * 2 agents) + 1 final decisions summary
    assert len(engine.debate_transcript) == 5
    assert "## Decisões Aplicáveis (Síntese)" in result
