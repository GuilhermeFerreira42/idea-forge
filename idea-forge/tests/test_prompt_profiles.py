"""
test_prompt_profiles.py — Testes unitários para PromptProfiles (W3-01).

Fase 9.7 — Onda 3.
"""

import pytest
from src.core.prompt_profiles import (
    PromptProfiles,
    PromptProfile,
    PROFILE_SMALL,
    PROFILE_MEDIUM,
    PROFILE_LARGE,
)


class TestDetectRange:
    """Testes de detecção de faixa por nome de modelo."""

    # --- Modelos SMALL ---
    def test_qwen_1b(self):
        assert PromptProfiles.detect_range("qwen2.5:1b") == "SMALL"

    def test_qwen_1_5b(self):
        assert PromptProfiles.detect_range("qwen2.5:1.5b") == "SMALL"

    def test_gemma3_1b(self):
        assert PromptProfiles.detect_range("gemma3:1b") == "SMALL"

    def test_gemma_2b(self):
        assert PromptProfiles.detect_range("gemma:2b") == "SMALL"

    def test_tinyllama(self):
        assert PromptProfiles.detect_range("tinyllama:latest") == "SMALL"

    def test_phi3_mini(self):
        assert PromptProfiles.detect_range("phi3:mini") == "SMALL"

    # --- Modelos MEDIUM ---
    def test_qwen_3b(self):
        assert PromptProfiles.detect_range("qwen2.5:3b") == "MEDIUM"

    def test_llama_3b(self):
        assert PromptProfiles.detect_range("llama3.2:3b") == "MEDIUM"

    def test_mistral_7b(self):
        assert PromptProfiles.detect_range("mistral:7b") == "MEDIUM"

    def test_gemma_7b(self):
        assert PromptProfiles.detect_range("gemma:7b") == "MEDIUM"

    # --- Modelos LARGE ---
    def test_gpt_oss_20b(self):
        assert PromptProfiles.detect_range("gpt-oss:20b-cloud") == "LARGE"

    def test_llama3_70b(self):
        assert PromptProfiles.detect_range("llama3:70b") == "LARGE"

    def test_qwen_72b(self):
        assert PromptProfiles.detect_range("qwen2.5:72b") == "LARGE"

    def test_generic_unknown(self):
        assert PromptProfiles.detect_range("some-custom-model") == "LARGE"

    # --- Edge cases ---
    def test_empty_string(self):
        assert PromptProfiles.detect_range("") == "LARGE"

    def test_none(self):
        assert PromptProfiles.detect_range(None) == "LARGE"

    def test_small_not_detected_as_medium(self):
        """qwen2.5:1.5b contém '1.5b' → SMALL, não deve cair em MEDIUM."""
        result = PromptProfiles.detect_range("qwen2.5:1.5b")
        assert result == "SMALL"
        assert result != "MEDIUM"

    def test_case_insensitive(self):
        assert PromptProfiles.detect_range("QWEN2.5:1B") == "SMALL"
        assert PromptProfiles.detect_range("Gemma3:1B") == "SMALL"


class TestGetProfile:
    """Testes do factory de perfis."""

    def test_small_profile(self):
        profile = PromptProfiles.get_profile("SMALL")
        assert profile is PROFILE_SMALL

    def test_medium_profile(self):
        profile = PromptProfiles.get_profile("MEDIUM")
        assert profile is PROFILE_MEDIUM

    def test_large_profile(self):
        profile = PromptProfiles.get_profile("LARGE")
        assert profile is PROFILE_LARGE

    def test_invalid_range_raises(self):
        with pytest.raises(ValueError, match="inválido"):
            PromptProfiles.get_profile("XLARGE")

    def test_from_model_name_shortcut(self):
        profile = PromptProfiles.from_model_name("qwen2.5:3b")
        assert profile.model_range == "MEDIUM"
        assert profile is PROFILE_MEDIUM


class TestProfileValues:
    """Testes dos valores concretos dos perfis."""

    def test_small_max_output_tokens(self):
        assert PROFILE_SMALL.max_output_tokens == 400

    def test_small_uses_atomic(self):
        assert PROFILE_SMALL.use_atomic_decomposition is True

    def test_small_system_mode_few_shot(self):
        assert PROFILE_SMALL.system_prompt_mode == "FEW_SHOT"

    def test_medium_no_atomic(self):
        assert PROFILE_MEDIUM.use_atomic_decomposition is False

    def test_medium_system_mode_hybrid(self):
        assert PROFILE_MEDIUM.system_prompt_mode == "HYBRID"

    def test_large_max_output_tokens(self):
        """Perfil LARGE preserva comportamento pré-fase 9.7."""
        assert PROFILE_LARGE.max_output_tokens == 2500

    def test_large_retry_max_tokens(self):
        """Nível 2 original usava max_tokens=1500."""
        assert PROFILE_LARGE.retry_max_tokens == 1500

    def test_large_system_mode_full_sop(self):
        assert PROFILE_LARGE.system_prompt_mode == "FULL_SOP"

    def test_large_no_atomic(self):
        assert PROFILE_LARGE.use_atomic_decomposition is False

    def test_large_input_budget_preserves_current(self):
        """input_budget_override=3000 equivale ao input_budget dos SectionPass atuais."""
        assert PROFILE_LARGE.input_budget_override == 3000

    def test_invariant_max_output_ge_retry(self):
        """Invariante: max_output_tokens >= retry_max_tokens para todos os perfis."""
        for profile in [PROFILE_SMALL, PROFILE_MEDIUM, PROFILE_LARGE]:
            assert profile.max_output_tokens >= profile.retry_max_tokens, (
                f"{profile.model_range}: max_output_tokens "
                f"({profile.max_output_tokens}) < retry_max_tokens "
                f"({profile.retry_max_tokens})"
            )

    def test_invariant_atomic_implies_small_output(self):
        """Invariante: use_atomic_decomposition==True implica max_output_tokens<=400."""
        for profile in [PROFILE_SMALL, PROFILE_MEDIUM, PROFILE_LARGE]:
            if profile.use_atomic_decomposition:
                assert profile.max_output_tokens <= 400

    def test_profiles_are_frozen(self):
        """Perfis são imutáveis."""
        with pytest.raises(Exception):  # FrozenInstanceError
            PROFILE_SMALL.max_output_tokens = 999
