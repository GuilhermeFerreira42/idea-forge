"""
test_stress_1b.py — Bateria de teste de estresse W3-03.

Fase 9.7 — Onda 3: Testa pipeline completo com modelo 1B-1.5B.

EXECUÇÃO: pytest tests/test_stress_1b.py -v -m integration

PRÉ-REQUISITO: ollama pull qwen2.5:1.5b  OU  ollama pull gemma3:1b
"""

import pytest


def _ollama_model_available(model_name: str) -> bool:
    """Verifica se um modelo está disponível no Ollama local."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        available_names = [m["name"] for m in models]
        return any(model_name in name for name in available_names)
    except Exception:
        return False


def _get_available_1b_model() -> str:
    """Retorna o primeiro modelo 1B disponível, ou None."""
    candidates = ["qwen2.5:1.5b", "qwen2.5:1b", "gemma3:1b", "tinyllama"]
    for model in candidates:
        if _ollama_model_available(model):
            return model
    return None


@pytest.mark.integration
class TestStress1B:
    """
    Bateria W3-03: Testes com modelo 1B-1.5B.

    Thresholds de aceitação (RELAXADOS para modelos 1B):
    - Completude >= 75% (15/20 seções — qualidade textual pode ser menor)
    - Nenhum crash ou AttributeError no pipeline
    - PRD_FINAL tem len > 5.000 chars
    - Modo atômico ativado para seções com tabela
    """

    def setup_method(self):
        """Detecta modelo disponível ou pula."""
        self.model_name = _get_available_1b_model()
        if self.model_name is None:
            pytest.skip(
                "Nenhum modelo 1B disponível no Ollama. "
                "Execute: ollama pull qwen2.5:1.5b"
            )

    def test_profile_detected_as_small(self):
        """Verifica que modelo 1B é detectado como SMALL."""
        from src.core.prompt_profiles import PromptProfiles
        range_ = PromptProfiles.detect_range(self.model_name)
        assert range_ == "SMALL", (
            f"Esperado SMALL para '{self.model_name}', obtido {range_}."
        )

    def test_profile_uses_atomic(self):
        """Perfil SMALL usa decomposição atômica."""
        from src.core.prompt_profiles import PromptProfiles
        profile = PromptProfiles.from_model_name(self.model_name)
        assert profile.use_atomic_decomposition is True

    def test_profile_max_output_tokens_400(self):
        """Perfil SMALL tem max_output_tokens=400."""
        from src.core.prompt_profiles import PromptProfiles
        profile = PromptProfiles.from_model_name(self.model_name)
        assert profile.max_output_tokens == 400

    def test_should_use_atomic_for_table_pass(self):
        """_should_use_atomic retorna True para pass com tabela + perfil SMALL."""
        from src.core.prompt_profiles import PROFILE_SMALL
        from src.core.sectional_generator import SectionalGenerator, SectionPass
        from unittest.mock import MagicMock

        gen = SectionalGenerator(MagicMock())

        pass_with_table = SectionPass(
            pass_id="final_p04",
            sections=["## Requisitos Funcionais"],
            template="",
            example="",
            instruction="",
            require_table=True,
        )

        assert gen._should_use_atomic(pass_with_table, PROFILE_SMALL) is True

    def test_should_not_use_atomic_for_no_table_pass(self):
        """_should_use_atomic retorna False para pass sem tabela."""
        from src.core.prompt_profiles import PROFILE_SMALL
        from src.core.sectional_generator import SectionalGenerator, SectionPass
        from unittest.mock import MagicMock

        gen = SectionalGenerator(MagicMock())

        pass_no_table = SectionPass(
            pass_id="final_p01",
            sections=["## Visão do Produto"],
            template="",
            example="",
            instruction="",
            require_table=False,
        )

        assert gen._should_use_atomic(pass_no_table, PROFILE_SMALL) is False

    @pytest.mark.slow
    def test_full_pipeline_structurally_complete(self, tmp_path):
        """
        Executa pipeline completo com modelo 1B e verifica completude estrutural.

        THRESHOLD RELAXADO: completude >= 75% (qualidade textual não avaliada).
        PRD_FINAL deve ter len > 5.000 chars (densidade mínima aceitável).

        TIMEOUT ESPERADO: 20-40 minutos para modelo 1B.
        """
        from src.models.ollama_provider import OllamaProvider
        from src.core.controller import AgentController
        from src.core.output_validator import OutputValidator

        provider = OllamaProvider(
            model_name=self.model_name,
            think=False,
            show_thinking=False,
        )

        assert provider.model_range == "SMALL", (
            f"OllamaProvider.model_range deveria ser SMALL, obtido {provider.model_range}"
        )

        controller = AgentController(provider, think=False)
        controller.agents["human_gate_callback"] = lambda x: "APPROVED"

        idea = (
            "Aplicativo de monitoramento de saúde pessoal com análise "
            "de dados biométricos e alertas preventivos."
        )

        report_file = str(tmp_path / "stress_1b_report.md")

        # Pipeline NÃO deve lançar exceção
        controller.run_pipeline(idea, report_file)

        # Verificar que PRD final foi gerado
        prd_final_art = controller.artifact_store.read("prd_final")
        assert prd_final_art is not None, "prd_final não foi gerado"
        assert len(prd_final_art.content) > 5_000, (
            f"PRD muito curto para modelo 1B: {len(prd_final_art.content)} chars. "
            f"Esperado > 5.000 chars (modo atômico deve garantir estrutura mínima)."
        )

        # Verificar completude estrutural >= 75%
        validator = OutputValidator()
        validation = validator.validate(prd_final_art.content, "prd_final")
        completeness = validation.get("completeness_score", 0)

        assert completeness >= 0.75, (
            f"Completude estrutural abaixo de 75%: {completeness:.1%}. "
            f"Seções presentes: {validation.get('present_sections', [])}.\n"
            f"Seções ausentes: {validation.get('missing_sections', [])}."
        )

        # Verificar que pipeline não crashou com AttributeError
        # (presença de prd_final já garante isso, mas ser explícito)
        assert "AttributeError" not in prd_final_art.content

    @pytest.mark.slow
    def test_atomic_decomposer_invoked_for_table_sections(self, tmp_path):
        """
        Verifica que o modo atômico foi ativado para seções com tabela.

        Proxy: logs do terminal contêm "[ATOMIC]" — impossível verificar
        diretamente sem injetar spy. Verificamos via estrutura do PRD.
        """
        from src.models.ollama_provider import OllamaProvider
        from src.core.controller import AgentController

        provider = OllamaProvider(
            model_name=self.model_name,
            think=False,
            show_thinking=False,
        )

        controller = AgentController(provider, think=False)
        controller.agents["human_gate_callback"] = lambda x: "APPROVED"

        idea = "Plataforma de cursos online com gamificação e IA adaptativa."
        report_file = str(tmp_path / "stress_1b_atomic_report.md")
        controller.run_pipeline(idea, report_file)

        # Se modo atômico funcionou, a seção de RFs deve ter tabela
        prd_final_art = controller.artifact_store.read("prd_final")
        if prd_final_art:
            # Verificar que há pelo menos alguma tabela no PRD
            assert "|---|" in prd_final_art.content, (
                "Nenhuma tabela encontrada no PRD com modelo 1B. "
                "O modo atômico deveria ter gerado tabelas linha a linha."
            )
