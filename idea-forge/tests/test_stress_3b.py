"""
test_stress_3b.py — Bateria de teste de estresse W3-02.

Fase 9.7 — Onda 3: Testa pipeline completo com modelo Qwen 2.5:3B.

EXECUÇÃO: pytest tests/test_stress_3b.py -v -m integration

PRÉ-REQUISITO: ollama pull qwen2.5:3b
"""

import pytest
import os


def _ollama_model_available(model_name: str) -> bool:
    """Verifica se um modelo está disponível no Ollama local."""
    try:
        import requests
        response = requests.get(
            "http://localhost:11434/api/tags", timeout=5
        )
        response.raise_for_status()
        models = response.json().get("models", [])
        available_names = [m["name"] for m in models]
        return any(model_name in name for name in available_names)
    except Exception:
        return False


@pytest.mark.integration
class TestStress3B:
    """
    Bateria W3-02: Testes com modelo Qwen 2.5:3B.

    Thresholds de aceitação:
    - is_clean: True
    - Taxa de fallback Nível 3 < 30%
    - Completude >= 80% (16/20 seções)
    """

    MODEL_NAME = "qwen2.5:3b"

    def setup_method(self):
        """Verifica pré-requisitos antes de cada teste."""
        if not _ollama_model_available(self.MODEL_NAME):
            pytest.skip(
                f"Modelo '{self.MODEL_NAME}' não disponível no Ollama. "
                f"Execute: ollama pull {self.MODEL_NAME}"
            )

    def test_profile_detected_as_medium(self):
        """Verifica que qwen2.5:3b é detectado como MEDIUM."""
        from src.core.prompt_profiles import PromptProfiles
        range_ = PromptProfiles.detect_range(self.MODEL_NAME)
        assert range_ == "MEDIUM", (
            f"Esperado MEDIUM, obtido {range_}. "
            f"Verificar _MEDIUM_KEYWORDS em prompt_profiles.py."
        )

    def test_profile_no_atomic(self):
        """Perfil MEDIUM não usa decomposição atômica."""
        from src.core.prompt_profiles import PromptProfiles
        profile = PromptProfiles.from_model_name(self.MODEL_NAME)
        assert profile.use_atomic_decomposition is False

    def test_profile_max_output_tokens(self):
        """Perfil MEDIUM tem max_output_tokens=800."""
        from src.core.prompt_profiles import PromptProfiles
        profile = PromptProfiles.from_model_name(self.MODEL_NAME)
        assert profile.max_output_tokens == 800

    @pytest.mark.slow
    def test_full_pipeline_is_clean(self, tmp_path):
        """
        Executa o pipeline completo com qwen2.5:3b e verifica is_clean: True.

        TIMEOUT ESPERADO: 10-20 minutos dependendo do hardware.
        """
        from src.models.ollama_provider import OllamaProvider
        from src.core.controller import AgentController
        from src.agents.consistency_checker_agent import ConsistencyCheckerAgent

        provider = OllamaProvider(
            model_name=self.MODEL_NAME,
            think=False,
            show_thinking=False,
        )

        assert provider.model_range == "MEDIUM", (
            f"OllamaProvider.model_range deveria ser MEDIUM, obtido {provider.model_range}"
        )

        controller = AgentController(provider, think=False)
        controller.agents["human_gate_callback"] = lambda x: "APPROVED"

        idea = (
            "Sistema de gerenciamento de tarefas com IA que prioriza "
            "automaticamente tasks com base em urgência e impacto no projeto."
        )

        report_file = str(tmp_path / "stress_3b_report.md")
        controller.run_pipeline(idea, report_file)

        # Verificar PRD final gerado
        prd_final_art = controller.artifact_store.read("prd_final")
        assert prd_final_art is not None, "prd_final não foi gerado"
        assert len(prd_final_art.content) > 10_000, (
            f"PRD muito curto: {len(prd_final_art.content)} chars. "
            f"Esperado > 10.000 chars."
        )

        # Verificar consistência
        consistency_art = controller.artifact_store.read("consistency_report")
        assert consistency_art is not None, "consistency_report não foi gerado"

        is_clean = "is_clean:** True" in consistency_art.content
        assert is_clean, (
            f"is_clean: False no modelo 3B.\n"
            f"Relatório de consistência:\n{consistency_art.content[:2000]}"
        )

    @pytest.mark.slow
    def test_fallback_level3_rate_below_30_percent(self, tmp_path):
        """
        Verifica que a taxa de fallback Nível 3 é < 30% com modelo 3B.

        THRESHOLD: Máximo 30% das seções recuperadas usam Nível 3.
        """
        from src.models.ollama_provider import OllamaProvider
        from src.core.controller import AgentController

        provider = OllamaProvider(
            model_name=self.MODEL_NAME,
            think=False,
            show_thinking=False,
        )

        controller = AgentController(provider, think=False)
        controller.agents["human_gate_callback"] = lambda x: "APPROVED"

        idea = "Plataforma de e-commerce com recomendação de produtos por IA."
        report_file = str(tmp_path / "stress_3b_fallback_report.md")
        controller.run_pipeline(idea, report_file)

        # Acessar log de recovery
        # O RetryOrchestrator é instanciado dentro de consolidate_prd
        # Verificar via relatório de consistência se há seções falhadas restantes
        consistency_art = controller.artifact_store.read("consistency_report")
        assert consistency_art is not None

        # Contar [GERAÇÃO FALHOU] no PRD final como proxy para Nível 3
        prd_final_art = controller.artifact_store.read("prd_final")
        if prd_final_art:
            total_sections = 20
            failed_sections = prd_final_art.content.count("[GERAÇÃO FALHOU")
            recovered_via_l3 = failed_sections  # Proxy: seções que ainda falharam

            fallback_rate = recovered_via_l3 / total_sections
            assert fallback_rate < 0.30, (
                f"Taxa de fallback Nível 3 muito alta: {fallback_rate:.1%} "
                f"({recovered_via_l3}/{total_sections} seções).\n"
                f"Target: < 30%."
            )
