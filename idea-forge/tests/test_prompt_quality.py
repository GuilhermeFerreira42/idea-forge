import pytest
import re
from src.core.planner import Planner

def calculate_density_score(text: str) -> float:
    """
    Calcula a densidade técnica: (Número de tabelas + bullets) / (Total de linhas narrativas).
    Score ideal > 0.85
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return 0.0
    
    technical_lines = 0
    narrative_lines = 0
    
    for line in lines:
        # Check for table markers or bullet points or headings
        if line.startswith('|') or line.startswith('- ') or line.startswith('## ') or re.match(r'^\d+\.', line):
            technical_lines += 1
        else:
            # Narrative if it's not a common markdown structure
            narrative_lines += 1
            
    total = technical_lines + narrative_lines
    return technical_lines / total if total > 0 else 0.0

def test_post_processing_strips_chat_noise():
    planner = Planner(None, None, {})
    noisy_text = "Certamente! Aqui está o seu PRD:\n\n## Objetivo\n- Criar app."
    clean_text = planner._post_process_output(noisy_text)
    
    assert "Certamente" not in clean_text
    assert "Aqui está" not in clean_text
    assert clean_text.startswith("## Objetivo")

def test_post_processing_removes_think_tags():
    planner = Planner(None, None, {})
    text_with_think = "<think>\nReasoning here...\n</think>\n## Objetivo\n- Teste."
    clean_text = planner._post_process_output(text_with_think)
    
    assert "<think>" not in clean_text
    assert "Reasoning here" not in clean_text
    assert clean_text == "## Objetivo\n- Teste."

def test_density_score_heurisitc():
    # Technical text (100% density)
    tech_text = "## Header\n- Bullet 1\n| Table | Row |\n|---|---|\n- Bullet 2"
    assert calculate_density_score(tech_text) == 1.0
    
    # Narrative text (Low density)
    narrative = "Olá, este é um documento longo.\nEle contém muitos parágrafos.\nNão tem tabelas nem nada."
    assert calculate_density_score(narrative) < 0.2

@pytest.mark.parametrize("agent_type, content, expected_min_score", [
    ("prd", "## Objetivo\n- App\n## Requisitos\n| ID | RF |\n|---|---|\n| 01 | Login |", 0.85),
    ("review", "## Lacunas\n- Faltou banco\n## Riscos\n| R | S |\n|---|---|", 0.85),
])
def test_density_targets(agent_type, content, expected_min_score):
    score = calculate_density_score(content)
    assert score >= expected_min_score, f"Density score for {agent_type} is too low: {score}"
