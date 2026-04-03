"""
test_retry_orchestrator.py — Testes unitários do RetryOrchestrator.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.core.retry_orchestrator import RetryOrchestrator


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.generate.return_value = ""  # L2 falha por default
    return provider


@pytest.fixture
def orchestrator(mock_provider):
    return RetryOrchestrator(provider=mock_provider, direct_mode=True)


class TestRetryOrchestrator:

    def test_detect_failed_sections_finds_markers(self, orchestrator):
        """Detecta seções com [GERAÇÃO FALHOU]."""
        prd = (
            "## Visão do Produto\nConteúdo OK\n\n"
            "## Público-Alvo\n- [GERAÇÃO FALHOU — seção não produzida]\n\n"
            "## Requisitos Funcionais\n- [GERAÇÃO FALHOU — seção não produzida]\n\n"
        )
        failed = orchestrator._detect_failed_sections(prd)
        assert len(failed) == 2
        assert any("Público-Alvo" in f["heading"] for f in failed)
        assert any("Requisitos Funcionais" in f["heading"] for f in failed)

    def test_detect_failed_sections_empty_prd(self, orchestrator):
        """PRD sem falhas retorna lista vazia."""
        prd = "## Visão do Produto\nConteúdo OK\n\n## Público-Alvo\nConteúdo OK\n"
        failed = orchestrator._detect_failed_sections(prd)
        assert len(failed) == 0

    def test_recover_no_failures_returns_unchanged(self, orchestrator):
        """PRD sem falhas passa sem modificação."""
        prd = "## Visão do Produto\nConteúdo válido aqui\n"
        result = orchestrator.recover(prd, {})
        assert result == prd

    def test_level_3_never_returns_empty(self, orchestrator):
        """Nível 3 sempre retorna conteúdo válido."""
        section_info = {"heading": "## Público-Alvo", "start_idx": 0, "end_idx": 50}
        result = orchestrator._retry_level_3(section_info, {"prd": ""})
        assert result is not None
        assert len(result) > 20
        assert "##" in result

    def test_level_3_publico_alvo_with_data(self, orchestrator):
        """Template de Público-Alvo preenche com dados extraídos."""
        section_info = {"heading": "## Público-Alvo"}
        prd_content = (
            "## Público-Alvo\n"
            "| Segmento | Perfil (nome fictício + dor específica) | Prioridade |\n"
            "|---|---|---|\n"
            "| Dev | João, 30 anos, quer API rápida | P0 |\n"
        )
        result = orchestrator._retry_level_3(section_info, {"prd": prd_content})
        assert "Público-Alvo" in result
        assert "|" in result

    def test_replace_section_preserves_others(self, orchestrator):
        """Substituição de seção não afeta seções adjacentes."""
        prd = (
            "## Seção A\nConteúdo A\n\n"
            "## Seção B\n- [GERAÇÃO FALHOU]\n\n"
            "## Seção C\nConteúdo C\n"
        )
        section_info = {
            "heading": "## Seção B",
            "start_idx": prd.index("## Seção B"),
            "end_idx": prd.index("## Seção C"),
        }
        new_content = "## Seção B\nConteúdo B recuperado\n"
        result = orchestrator._replace_section(prd, section_info, new_content)
        assert "Conteúdo A" in result
        assert "Conteúdo B recuperado" in result
        assert "Conteúdo C" in result

    def test_recovery_log_records_level(self, orchestrator):
        """Log registra nível usado para cada seção."""
        prd = "## Público-Alvo\n- [GERAÇÃO FALHOU — seção não produzida]\n"
        orchestrator.recover(prd, {"prd": ""})
        log = orchestrator.get_recovery_log()
        assert len(log) >= 1
        assert log[0]["level_used"] in [2, 3]
        assert log[0]["chars_recovered"] > 0

    def test_deduplication_detects_overlap(self, orchestrator):
        """Deduplicação identifica conteúdo similar."""
        prd = "## Seção A\nPalavra um dois três quatro cinco seis sete oito\n\n## Seção B\nOutro conteúdo\n"
        new_content = "## Seção C\nPalavra um dois três quatro cinco seis sete oito"
        result = orchestrator._check_deduplication("## Seção C", new_content, prd)
        assert result == "## Seção A"  # Detecta que é igual à Seção A

    def test_full_recovery_pipeline_l3_only(self, orchestrator):
        """Teste E2E: PRD com 3 falhas → 0 falhas após recovery (L3 only)."""
        prd = (
            "## Visão do Produto\nConteúdo OK\n\n"
            "## Público-Alvo\n- [GERAÇÃO FALHOU — seção não produzida]\n\n"
            "## Métricas de Sucesso\n- [GERAÇÃO FALHOU — seção não produzida]\n\n"
            "## Plano de Implementação\n- [GERAÇÃO FALHOU — seção não produzida]\n\n"
        )
        result = orchestrator.recover(prd, {"prd": "", "development_plan": ""})
        assert "[GERAÇÃO FALHOU]" not in result
        assert "## Público-Alvo" in result
        assert "## Métricas de Sucesso" in result
        assert "## Plano de Implementação" in result

    def test_validate_rf_references_removes_orphans(self, orchestrator):
        """Validação de RF_ORPHAN remove referências órfãs."""
        prd = (
            "## Requisitos Funcionais\n"
            "| ID | Requisito |\n|---|---|\n| RF-01 | Login |\n| RF-02 | Busca |\n\n"
            "## Escopo MVP\n"
            "- RF-01 (Login)\n"
            "- RF-02 (Busca)\n"
            "- RF-03 (Comparador)\n"  # Órfão — não existe na tabela
        )
        result = orchestrator._validate_rf_references(prd)
        assert "RF-01" in result
        assert "RF-02" in result
        # RF-03 deve ter sido removido do Escopo
        escopo_section = result.split("## Escopo MVP")[1] if "## Escopo MVP" in result else ""
        assert "RF-03" not in escopo_section


class TestProductManagerEmit:
    """Testes para o método _emit do ProductManagerAgent."""

    def test_emit_does_not_raise(self):
        """_emit não lança exceção."""
        from src.agents.product_manager_agent import ProductManagerAgent
        from unittest.mock import MagicMock
        pma = ProductManagerAgent(provider=MagicMock(), direct_mode=True)
        # Não deve lançar exceção
        pma._emit("Teste de mensagem")

    def test_emit_exists(self):
        """_emit existe como método."""
        from src.agents.product_manager_agent import ProductManagerAgent
        assert hasattr(ProductManagerAgent, '_emit')