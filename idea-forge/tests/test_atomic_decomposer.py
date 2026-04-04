"""
test_atomic_decomposer.py — Testes unitários para AtomicTaskDecomposer (W3-04).

Fase 9.7 — Onda 3.
"""

import pytest
from unittest.mock import MagicMock, call
from src.core.atomic_task_decomposer import AtomicTaskDecomposer, AtomicCallResult
from src.core.prompt_profiles import PROFILE_SMALL, PROFILE_LARGE


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    return provider


@pytest.fixture
def decomposer(mock_provider):
    return AtomicTaskDecomposer(provider=mock_provider, profile=PROFILE_SMALL)


class TestInit:
    def test_raises_if_not_atomic_profile(self, mock_provider):
        """Não pode ser instanciado com perfil que não usa decomposição atômica."""
        with pytest.raises(ValueError, match="use_atomic_decomposition=False"):
            AtomicTaskDecomposer(provider=mock_provider, profile=PROFILE_LARGE)

    def test_accepts_small_profile(self, mock_provider):
        d = AtomicTaskDecomposer(provider=mock_provider, profile=PROFILE_SMALL)
        assert d.profile.model_range == "SMALL"


class TestDecomposeTablePass:
    def test_calls_provider_once_per_row(self, decomposer, mock_provider):
        """Deve chamar provider.generate() exatamente target_row_count vezes."""
        mock_provider.generate.return_value = "| RF-01 | Login | POST 201 | Must | Low |"

        rows = decomposer.decompose_table_pass(
            section_heading="## Requisitos Funcionais",
            columns=["ID", "Requisito", "Critério", "Prioridade", "Complexidade"],
            context="Projeto de teste",
            target_row_count=3,
            system_directive="Gere uma linha.",
        )

        assert mock_provider.generate.call_count == 3

    def test_returns_only_successful_rows(self, decomposer, mock_provider):
        """Linhas com resposta vazia não devem ser incluídas."""
        mock_provider.generate.side_effect = [
            "| RF-01 | Login | POST 201 | Must | Low |",  # OK
            "",  # FALHOU
            "| RF-03 | Busca | GET 200 | Should | Medium |",  # OK
        ]

        rows = decomposer.decompose_table_pass(
            section_heading="## Requisitos Funcionais",
            columns=["ID", "Requisito", "Critério", "Prioridade", "Complexidade"],
            context="Projeto de teste",
            target_row_count=3,
            system_directive="Gere uma linha.",
        )

        assert len(rows) == 2
        assert "RF-01" in rows[0]
        assert "RF-03" in rows[1]

    def test_clamps_target_to_max_20(self, decomposer, mock_provider):
        """target_row_count é clampado a 20."""
        mock_provider.generate.return_value = "| X | Y |"

        rows = decomposer.decompose_table_pass(
            section_heading="## Riscos Consolidados",
            columns=["ID", "Risco"],
            context="ctx",
            target_row_count=50,  # Acima do máximo
            system_directive="cmd",
        )

        assert mock_provider.generate.call_count == 20

    def test_clamps_target_to_min_1(self, decomposer, mock_provider):
        """target_row_count é clampado a 1."""
        mock_provider.generate.return_value = "| X | Y |"

        decomposer.decompose_table_pass(
            section_heading="## Métricas de Sucesso",
            columns=["Métrica", "Target"],
            context="ctx",
            target_row_count=0,  # Abaixo do mínimo
            system_directive="cmd",
        )

        assert mock_provider.generate.call_count == 1

    def test_raises_on_invalid_heading(self, decomposer):
        with pytest.raises(ValueError, match="'## '"):
            decomposer.decompose_table_pass(
                section_heading="Requisitos Funcionais",  # Sem ##
                columns=["A", "B"],
                context="ctx",
                target_row_count=2,
                system_directive="cmd",
            )

    def test_raises_on_single_column(self, decomposer):
        with pytest.raises(ValueError, match="pelo menos 2"):
            decomposer.decompose_table_pass(
                section_heading="## Test",
                columns=["SóUma"],
                context="ctx",
                target_row_count=2,
                system_directive="cmd",
            )

    def test_uses_profile_max_output_tokens(self, decomposer, mock_provider):
        """Deve passar profile.max_output_tokens como max_tokens ao provider."""
        mock_provider.generate.return_value = "| A | B |"

        decomposer.decompose_table_pass(
            section_heading="## Test Section",
            columns=["A", "B"],
            context="ctx",
            target_row_count=1,
            system_directive="cmd",
        )

        # Verificar que max_tokens foi passado como 400 (PROFILE_SMALL)
        call_kwargs = mock_provider.generate.call_args
        assert call_kwargs.kwargs.get("max_tokens") == 400

    def test_provider_exception_treated_as_failure(self, decomposer, mock_provider):
        """Exceção do provider é capturada como falha de linha."""
        mock_provider.generate.side_effect = [
            Exception("Timeout"),
            "| RF-02 | Válido | OK | Must | Low |",
        ]

        rows = decomposer.decompose_table_pass(
            section_heading="## Requisitos Funcionais",
            columns=["ID", "Req", "CA", "Prio", "Cx"],
            context="ctx",
            target_row_count=2,
            system_directive="cmd",
        )

        assert len(rows) == 1
        assert "RF-02" in rows[0]


class TestAssembleTable:
    def test_produces_valid_markdown(self, decomposer):
        result = decomposer.assemble_table(
            heading="## Requisitos Funcionais",
            columns=["ID", "Requisito"],
            rows=["| RF-01 | Login |", "| RF-02 | Busca |"],
        )

        assert "## Requisitos Funcionais" in result
        assert "| ID | Requisito |" in result
        assert "|---|---|" in result
        assert "| RF-01 | Login |" in result
        assert "| RF-02 | Busca |" in result

    def test_empty_rows_returns_placeholder(self, decomposer):
        result = decomposer.assemble_table(
            heading="## Requisitos Funcionais",
            columns=["ID", "Requisito"],
            rows=[],
        )

        assert "## Requisitos Funcionais" in result
        assert "não disponíveis" in result

    def test_output_starts_with_heading(self, decomposer):
        result = decomposer.assemble_table(
            heading="## Análise de Segurança",
            columns=["ID", "Ameaça"],
            rows=["| S-01 | Spoofing |"],
        )
        assert result.startswith("## Análise de Segurança")


class TestDecomposeParagraphPass:
    def test_generates_one_bullet_per_label(self, decomposer, mock_provider):
        mock_provider.generate.return_value = "- RF-01: Sistema deve autenticar via JWT"

        bullets = decomposer.decompose_paragraph_pass(
            section_heading="## Escopo MVP",
            bullet_labels=["RF-01", "RF-02", "RF-03"],
            context="ctx",
            system_directive="cmd",
        )

        assert mock_provider.generate.call_count == 3

    def test_empty_response_excluded(self, decomposer, mock_provider):
        mock_provider.generate.side_effect = [
            "- RF-01: Conteúdo válido",
            "",  # Falha
        ]

        bullets = decomposer.decompose_paragraph_pass(
            section_heading="## Escopo MVP",
            bullet_labels=["RF-01", "RF-02"],
            context="ctx",
            system_directive="cmd",
        )

        assert len(bullets) == 1


class TestAssembleBullets:
    def test_produces_bullet_section(self, decomposer):
        result = decomposer.assemble_bullets(
            heading="## Escopo MVP",
            bullets=["- RF-01: Login", "- RF-02: Busca"],
        )

        assert "## Escopo MVP" in result
        assert "- RF-01: Login" in result
        assert "- RF-02: Busca" in result

    def test_empty_bullets_returns_placeholder(self, decomposer):
        result = decomposer.assemble_bullets(
            heading="## Escopo MVP",
            bullets=[],
        )

        assert "não disponíveis" in result


class TestGetColumnsForSection:
    def test_known_section(self):
        cols = AtomicTaskDecomposer.get_columns_for_section("## Requisitos Funcionais")
        assert cols is not None
        assert "ID" in cols

    def test_unknown_section(self):
        cols = AtomicTaskDecomposer.get_columns_for_section("## Seção Desconhecida")
        assert cols is None

    def test_partial_match(self):
        cols = AtomicTaskDecomposer.get_columns_for_section("## Análise de Segurança")
        assert cols is not None


class TestIsBulletSection:
    def test_escopo_mvp_is_bullet(self):
        assert AtomicTaskDecomposer.is_bullet_section("## Escopo MVP") is True

    def test_requisitos_is_not_bullet(self):
        assert AtomicTaskDecomposer.is_bullet_section("## Requisitos Funcionais") is False
