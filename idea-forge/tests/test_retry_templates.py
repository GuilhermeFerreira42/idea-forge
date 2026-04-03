"""
test_retry_templates.py — Testes dos templates estáticos Nível 3.
"""
import pytest
import src.core.retry_templates as templates


# Lista de todas as funções de template (20 total)
ALL_TEMPLATE_FUNCTIONS = [
    templates.template_visao_produto,
    templates.template_problema_solucao,
    templates.template_publico_alvo,
    templates.template_principios,
    templates.template_diferenciais,
    templates.template_requisitos_funcionais,
    templates.template_rnfs,
    templates.template_arquitetura,
    templates.template_adrs,
    templates.template_seguranca,
    templates.template_escopo_mvp,
    templates.template_riscos,
    templates.template_metricas,
    templates.template_plano,
    templates.template_decisoes_debate,
    templates.template_constraints,
    templates.template_rastreabilidade,
    templates.template_limitacoes,
    templates.template_guia_replicacao,
    templates.template_clausula,
]


class TestRetryTemplates:

    def test_each_template_returns_valid_markdown(self):
        """Todos os 20 templates retornam Markdown com heading ##."""
        for fn in ALL_TEMPLATE_FUNCTIONS:
            result = fn({})
            assert "##" in result, f"{fn.__name__} não contém heading ##"

    def test_each_template_handles_empty_data(self):
        """Templates funcionam com dict vazio."""
        for fn in ALL_TEMPLATE_FUNCTIONS:
            result = fn({})
            assert len(result) > 20, f"{fn.__name__} retornou < 20 chars com dict vazio"

    def test_each_template_never_returns_empty(self):
        """Nenhum template retorna string vazia."""
        for fn in ALL_TEMPLATE_FUNCTIONS:
            result = fn({})
            assert result.strip(), f"{fn.__name__} retornou string vazia"

    def test_template_publico_alvo_has_table(self):
        """Template de Público-Alvo contém tabela com |---|."""
        result = templates.template_publico_alvo({})
        assert "|---|" in result

    def test_template_publico_alvo_with_data(self):
        """Template de Público-Alvo preenche com dados extraídos."""
        data = {"personas": [
            {"segmento": "Dev", "perfil": "João, 30, quer API rápida", "prioridade": "P0"}
        ]}
        result = templates.template_publico_alvo(data)
        assert "João" in result
        assert "P0" in result

    def test_template_rfs_has_minimum_rows(self):
        """Template de RFs gera pelo menos 1 linha de dados."""
        result = templates.template_requisitos_funcionais({})
        # Contar linhas de tabela (excluindo header e separator)
        table_lines = [l for l in result.split("\n")
                       if l.strip().startswith("|") and "---|" not in l and "ID" not in l]
        assert len(table_lines) >= 1

    def test_template_rastreabilidade_uses_rf_data(self):
        """Template de Rastreabilidade usa RFs extraídos."""
        data = {"rfs": [
            {"id": "RF-01", "req": "Login", "criterio": "200 OK", "prioridade": "Must", "complexidade": "Low"},
            {"id": "RF-02", "req": "Busca", "criterio": "Lista JSON", "prioridade": "Must", "complexidade": "Medium"},
        ]}
        result = templates.template_rastreabilidade(data)
        assert "RF-01" in result
        assert "RF-02" in result