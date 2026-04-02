# -*- coding: utf-8 -*-
import pytest
from src.core.sectional_generator import SectionalGenerator
from src.models.model_provider import ModelProvider

class MockProvider(ModelProvider):
    def generate(self, prompt, role, max_tokens=800):
        return "mock"

def test_filter_section_output_leaking_header():
    generator = SectionalGenerator(MockProvider())
    
    # Caso 1: Vazamento simples
    output = "## Visão do Produto\nTexto da visão.\n## Problema e Solução\nTexto invasor."
    filtered = generator._filter_section_output(output, ["## Visão do Produto"])
    assert "## Visão do Produto" in filtered
    assert "Texto da visão." in filtered
    assert "## Problema e Solução" not in filtered
    assert "Texto invasor." not in filtered

def test_filter_section_output_preamble_ignored():
    generator = SectionalGenerator(MockProvider())
    
    # Caso 2: Preâmbulo deve ser ignorado para garantir que comece no header
    output = "Aqui está a seção solicitada:\n## Visão do Produto\nConteúdo."
    filtered = generator._filter_section_output(output, ["## Visão do Produto"])
    
    assert "## Visão do Produto" in filtered
    assert "Conteúdo." in filtered
    assert "Aqui está a seção" not in filtered

def test_sanitize_placeholders():
    generator = SectionalGenerator(MockProvider())
    
    content = "| Recurso | Status |\n|---|---|\n| API | A DEFINIR |\n| Redis | PENDENTE |"
    sanitized = generator._sanitize_placeholders(content)
    
    assert "A DEFINIR" not in sanitized
    assert "PENDENTE" not in sanitized
    assert sanitized.count("N/A") == 2

def test_filter_section_output_case_and_accent_insensitive():
    generator = SectionalGenerator(MockProvider())
    # Testando com 'Visao' (sem til) combinando com 'Visão' (com til)
    output = "## VISAO DO PRODUTO\nConteudo."
    filtered = generator._filter_section_output(output, ["## Visão do Produto"])
    assert "## VISAO DO PRODUTO" in filtered
    assert "Conteudo." in filtered

def test_filter_multi_section_pass():
    """Fase 9.5.3c: Filtro NÃO deve truncar segunda seção de pass multi-seção."""
    generator = SectionalGenerator(MockProvider())

    output = (
        "## Visão do Produto\nTexto da visão.\n"
        "## Problema e Solução\nTexto do problema.\n"
        "## Público-Alvo\nTexto invasor de outro pass."
    )
    filtered = generator._filter_section_output(
        output, ["## Visão do Produto", "## Problema e Solução"]
    )
    assert "## Visão do Produto" in filtered
    assert "Texto da visão." in filtered
    assert "## Problema e Solução" in filtered
    assert "Texto do problema." in filtered
    # Header de OUTRO pass deve ser removido
    assert "## Público-Alvo" not in filtered
    assert "Texto invasor" not in filtered

def test_filter_multi_section_no_invasor():
    """Fase 9.5.3c: Pass multi-seção sem invasor mantém tudo."""
    generator = SectionalGenerator(MockProvider())

    output = (
        "## Constraints Técnicos\n- Constraint 1\n"
        "## Matriz de Rastreabilidade\n| RF | Seção |\n|---|---|\n| RF-01 | MVP |"
    )
    filtered = generator._filter_section_output(
        output, ["## Constraints Técnicos", "## Matriz de Rastreabilidade"]
    )
    assert "## Constraints Técnicos" in filtered
    assert "## Matriz de Rastreabilidade" in filtered
    assert "RF-01" in filtered
