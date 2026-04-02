import pytest
from src.agents.critic_agent import _summarize_prd_for_critic

def test_summarize_prd_respects_token_limit():
    """Garante que o resumo não excede o limite de tokens."""
    # PRD fake de 35k chars
    fake_prd = "## Visão do Produto\n" + "x" * 10000 + "\n"
    fake_prd += "## Problema e Solução\n" + "y" * 10000 + "\n"
    fake_prd += "## Escopo (MVP)\n" + "z" * 10000 + "\n"
    
    # 800 tokens ≈ 3200 chars
    summary = _summarize_prd_for_critic(fake_prd, max_tokens=800)
    
    # Header check
    assert "## Visão do Produto" in summary
    assert "## Problema e Solução" in summary
    assert "## Escopo (MVP)" in summary
    
    # Length check (800 tokens * 4 chars/token + some margin for headers)
    assert len(summary) <= 4000
    assert "..." in summary  # Deve ter truncado

def test_summarize_prd_fallback_on_no_sections():
    """Garante fallback quando seções não são detectadas."""
    plain_text = "Este é um PRD sem formatação markdown de seções. " * 100
    summary = _summarize_prd_for_critic(plain_text, max_tokens=200)
    
    assert "RESUMO TRUNCADO" in summary
    assert len(summary) <= 900 # 200 * 4 + margin

def test_summarize_prd_extraction_precision():
    """Garante que extrai o texto correto entre seções."""
    prd = """## Visão do Produto
Esta é a visão.
## Problema e Solução
Este é o problema.
## Outra Seção
Não deve vir."""
    
    summary = _summarize_prd_for_critic(prd, max_tokens=500)
    assert "Esta é a visão." in summary
    assert "Este é o problema." in summary
    assert "## Outra Seção" not in summary
