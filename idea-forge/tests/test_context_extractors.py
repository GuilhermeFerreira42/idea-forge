# tests/test_context_extractors.py
import pytest
from src.core.context_extractors import (
    extract_for_arquitetura_tech_stack,
    extract_for_plano_implementacao,
    extract_for_decisoes_debate,
    extract_for_guia_replicacao,
    generate_clausula_integridade,
)


def test_extract_tech_stack_respects_limit():
    fake_design = "## Arquitetura Geral\n- Estilo: Micro\n" + "x" * 5000
    fake_design += "\n## Tech Stack\n| Camada | Tech |\n|---|---|\n| App | Node |\n"
    result = extract_for_arquitetura_tech_stack(fake_design)
    # 800 for table + 600 for arq + headers
    assert len(result) <= 2000
    assert "Tech Stack" in result
    assert "Micro" in result


def test_extract_decisoes_debate():
    fake_debate = "Proponente:\nbla bla\n" + "x" * 10000
    fake_debate += "\n## Decisões Aplicáveis (Síntese)\n| Round | Tipo |\n|---|---|\n| R1 | ACEITO |\n"
    result = extract_for_decisoes_debate(fake_debate)
    assert "R1" in result
    assert len(result) <= 2000


def test_extract_plano_implementacao():
    fake_plan = "## Módulos Core\n| Mod | Resp |\n|---|---|\n| Auth | JWT |\n"
    fake_plan += "\n## Fases de Implementação\n| Fase | Duração |\n|---|---|\n| F0 | 5d |\n"
    result = extract_for_plano_implementacao(fake_plan)
    assert "Auth" in result
    assert "F0" in result


def test_extract_guia_replicacao():
    fake_plan = "## Dependências Técnicas\n| Dep | Versão |\n|---|---|\n| Node | 20 |\n"
    fake_plan += "\n## Configurações de Ambiente\n| Var | Default |\n|---|---|\n| PORT | 8080 |\n"
    result = extract_for_guia_replicacao(fake_plan)
    assert "Node" in result
    assert "8080" in result


def test_clausula_integridade_template():
    result = generate_clausula_integridade(
        prd_final_chars=30000,
        total_sections=20,
        failed_sections=0,
        model_name="gpt-oss:20b-cloud",
        generated_at="2026-04-02T12:00:00"
    )
    assert "COMPLETO" in result
    assert "30,000" in result
    assert "gpt-oss:20b-cloud" in result
    assert "Cláusula de Integridade" in result


def test_clausula_integridade_com_falhas():
    result = generate_clausula_integridade(
        prd_final_chars=25000,
        total_sections=20,
        failed_sections=3,
        model_name="test-model",
        generated_at="2026-04-02"
    )
    assert "INCOMPLETO" in result
    assert "3 seções falharam" in result


def test_extract_fallback_when_section_not_found():
    result = extract_for_arquitetura_tech_stack("conteúdo sem headers relevantes")
    assert "Nenhum dado" in result or len(result) > 0
