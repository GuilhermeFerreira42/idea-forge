import pytest
from unittest.mock import patch
from tests.test_agents import MockProvider
from src.core.controller import AgentController

class PipelineMockProvider(MockProvider):
    def generate(self, prompt: str, context: list = None, role: str = "user") -> str:
        if role == "planner":
            return "# Final Plan\nArchitecture: Microservices"
        return super().generate(prompt, context, role)

@patch('src.cli.main.select_model', return_value="llama3")
@patch('src.cli.main.ask_approval', return_value=True)
def test_pipeline_end_to_end(mock_approval, mock_select_model):
    """
    Test the pipeline mocking the user approval to always be True,
    ensuring it runs from start to plan generation without getting stuck.
    """
    provider = PipelineMockProvider()
    
    # Decrease rounds to speed up test execution
    controller = AgentController(provider)
    controller.debate_engine.num_rounds = 1
    
    # Override input within controller loop if any is required, 
    # but here approval is enough to break loop
    with patch('builtins.input', return_value="y"):
        # We need to test the controller directly to avoid sys.exit issues from main.py's CLI prompts
        plan = controller.run_pipeline("A new social network")
    
    assert "# Final Plan" in plan
    assert "Architecture" in plan
