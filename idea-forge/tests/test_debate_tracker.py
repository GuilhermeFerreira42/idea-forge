"""
test_debate_tracker.py — Testes para o DebateStateTracker (Fase 10.0).
"""
import pytest
from src.debate.debate_state_tracker import DebateStateTracker, IssueRecord


# ═══════════════════════════════════════════════════════════
# TESTES DE PARSING DE ISSUES DO CRITIC
# ═══════════════════════════════════════════════════════════

class TestExtractIssuesFromTable:
    """Testes de extração de issues de tabelas Markdown."""

    def test_extract_6_column_table(self):
        tracker = DebateStateTracker()
        critique = (
            "## Issues Identificadas\n"
            "| ID | Severidade | Categoria | Localização | Descrição | Sugestão |\n"
            "|---|---|---|---|---|---|\n"
            "| ISS-01 | HIGH | SECURITY | Seção Auth | Senha sem hash | Usar bcrypt |\n"
            "| ISS-02 | MED | COMPLETENESS | Seção Riscos | Falta risco infra | Adicionar riscos |\n"
            "| ISS-03 | LOW | CONSISTENCY | Tech Stack | Redis sem módulo | Remover ou adicionar |\n"
        )
        new_ids = tracker.extract_issues_from_critique(critique, round_num=1)
        
        assert len(new_ids) == 3
        assert "ISS-01" in new_ids
        assert "ISS-02" in new_ids
        assert "ISS-03" in new_ids
        assert tracker.issues["ISS-01"].severity == "HIGH"
        assert tracker.issues["ISS-01"].category == "SECURITY"
        assert tracker.issues["ISS-02"].severity == "MED"
        assert tracker.issues["ISS-03"].round_raised == 1

    def test_extract_4_column_table(self):
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | Falha de autenticação |\n"
        )
        new_ids = tracker.extract_issues_from_critique(critique, round_num=2)
        
        assert len(new_ids) == 1
        assert tracker.issues["ISS-01"].severity == "HIGH"
        assert tracker.issues["ISS-01"].round_raised == 2

    def test_extract_with_medium_spelled_out(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | MEDIUM | CORRECTNESS | Lógica errada |\n"
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        
        assert len(new_ids) == 1
        assert tracker.issues["ISS-01"].severity == "MED"

    def test_no_duplicate_registration(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | HIGH | SECURITY | Falha auth |\n"
        
        ids_r1 = tracker.extract_issues_from_critique(critique, 1)
        ids_r2 = tracker.extract_issues_from_critique(critique, 2)
        
        assert len(ids_r1) == 1
        assert len(ids_r2) == 0
        assert len(tracker.issues) == 1

    def test_similar_description_dedup(self):
        tracker = DebateStateTracker()
        critique1 = "| ISS-01 | HIGH | SECURITY | Senha de usuário armazenada sem hashing |\n"
        critique2 = "| ISS-05 | HIGH | SECURITY | Senha de usuário armazenada sem hashing |\n"
        
        ids1 = tracker.extract_issues_from_critique(critique1, 1)
        ids2 = tracker.extract_issues_from_critique(critique2, 2)
        
        assert len(ids1) == 1
        assert len(ids2) == 0  # Mesma descrição, ID diferente → dedup


class TestExtractIssuesFromBullets:
    """Testes de extração fallback via bullets."""

    def test_bracket_severity_pattern(self):
        tracker = DebateStateTracker()
        critique = (
            "## Issues\n"
            "- [HIGH] Falta de autenticação no endpoint de admin\n"
            "- [LOW] Documentação de API incompleta\n"
        )
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        
        assert len(new_ids) == 2
        high_issues = [i for i in tracker.issues.values() if i.severity == "HIGH"]
        low_issues = [i for i in tracker.issues.values() if i.severity == "LOW"]
        assert len(high_issues) == 1
        assert len(low_issues) == 1

    def test_colon_severity_pattern(self):
        tracker = DebateStateTracker()
        critique = "- HIGH: Dados sensíveis sem criptografia\n"
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        
        assert len(new_ids) == 1
        assert tracker.issues[new_ids[0]].severity == "HIGH"

    def test_no_issues_in_plain_text(self):
        tracker = DebateStateTracker()
        critique = "A arquitetura parece boa. Continuar assim."
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        
        assert len(new_ids) == 0

    def test_empty_critique(self):
        tracker = DebateStateTracker()
        assert tracker.extract_issues_from_critique("", 1) == []
        assert tracker.extract_issues_from_critique(None, 1) == []


# ═══════════════════════════════════════════════════════════
# TESTES DE RESOLUÇÃO DE ISSUES
# ═══════════════════════════════════════════════════════════

class TestExtractResolutions:
    """Testes de detecção de resoluções na resposta do Proponent."""

    def test_resolve_by_explicit_id(self):
        tracker = DebateStateTracker()
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | Sem hash de senha |\n", 1
        )
        
        defense = (
            "## Pontos Aceitos\n"
            "- ISS-01: Concordamos em usar bcrypt para hash de senhas\n"
            "## Defesa Técnica\n"
            "- Restante da arquitetura está sólida\n"
        )
        resolved = tracker.extract_resolutions_from_defense(defense, 1)
        
        assert "ISS-01" in resolved
        assert tracker.issues["ISS-01"].status == "ACCEPTED"
        assert tracker.issues["ISS-01"].round_resolved == 1

    def test_resolve_by_description_match(self):
        tracker = DebateStateTracker()
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | Senha de usuário sem hashing no banco |\n", 1
        )
        
        defense = (
            "## Pontos Aceitos\n"
            "- A questão da senha de usuário sem hashing é válida, vamos corrigir\n"
        )
        resolved = tracker.extract_resolutions_from_defense(defense, 1)
        
        assert "ISS-01" in resolved
        assert tracker.issues["ISS-01"].status == "ACCEPTED"

    def test_no_resolve_without_pontos_aceitos(self):
        tracker = DebateStateTracker()
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | Problema grave |\n", 1
        )
        
        defense = (
            "## Defesa Técnica\n"
            "- ISS-01 não é um problema real, o sistema já cobre isso\n"
        )
        resolved = tracker.extract_resolutions_from_defense(defense, 1)
        
        # Sem seção "Pontos Aceitos", o issue permanece OPEN
        assert len(resolved) == 0
        assert tracker.issues["ISS-01"].status == "OPEN"

    def test_empty_defense(self):
        tracker = DebateStateTracker()
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | X |\n", 1
        )
        assert tracker.extract_resolutions_from_defense("", 1) == []
        assert tracker.extract_resolutions_from_defense(None, 1) == []

    def test_partial_resolution(self):
        """Apenas alguns issues são resolvidos, outros permanecem OPEN."""
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | Sem autenticação |\n"
            "| ISS-02 | MED | COMPLETENESS | Falta documentação |\n"
            "| ISS-03 | LOW | CONSISTENCY | Naming inconsistente |\n"
        )
        tracker.extract_issues_from_critique(critique, 1)
        
        defense = (
            "## Pontos Aceitos\n"
            "- ISS-01: Vamos adicionar JWT\n"
            "- ISS-03: Vamos padronizar nomenclatura\n"
            "## Defesa Técnica\n"
            "- ISS-02: A documentação será feita na v2\n"
        )
        resolved = tracker.extract_resolutions_from_defense(defense, 1)
        
        assert "ISS-01" in resolved
        assert "ISS-03" in resolved
        assert "ISS-02" not in resolved
        assert tracker.issues["ISS-01"].status == "ACCEPTED"
        assert tracker.issues["ISS-02"].status == "OPEN"
        assert tracker.issues["ISS-03"].status == "ACCEPTED"


# ═══════════════════════════════════════════════════════════
# TESTES DE QUERIES
# ═══════════════════════════════════════════════════════════

class TestTrackerQueries:
    """Testes para métodos de consulta do tracker."""

    def _setup_tracker_with_mixed_issues(self):
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | Sem auth |\n"
            "| ISS-02 | MED | COMPLETENESS | Falta doc |\n"
            "| ISS-03 | LOW | CONSISTENCY | Naming |\n"
        )
        tracker.extract_issues_from_critique(critique, 1)
        
        defense = "## Pontos Aceitos\n- ISS-03: OK\n"
        tracker.extract_resolutions_from_defense(defense, 1)
        
        return tracker

    def test_get_open_issues(self):
        tracker = self._setup_tracker_with_mixed_issues()
        open_issues = tracker.get_open_issues()
        
        assert len(open_issues) == 2
        # HIGH deve vir primeiro (ordenação por severidade)
        assert open_issues[0].severity == "HIGH"
        assert open_issues[1].severity == "MED"

    def test_get_resolved_issues(self):
        tracker = self._setup_tracker_with_mixed_issues()
        resolved = tracker.get_resolved_issues()
        
        assert len(resolved) == 1
        assert resolved[0].issue_id == "ISS-03"

    def test_has_blocking_issues_true(self):
        tracker = self._setup_tracker_with_mixed_issues()
        assert tracker.has_blocking_issues() is True

    def test_has_blocking_issues_false(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | LOW | CONSISTENCY | Minor |\n"
        tracker.extract_issues_from_critique(critique, 1)
        
        assert tracker.has_blocking_issues() is False

    def test_has_blocking_false_when_resolved(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | HIGH | SECURITY | Crítico |\n"
        tracker.extract_issues_from_critique(critique, 1)
        assert tracker.has_blocking_issues() is True
        
        defense = "## Pontos Aceitos\n- ISS-01: Corrigido\n"
        tracker.extract_resolutions_from_defense(defense, 1)
        assert tracker.has_blocking_issues() is False

    def test_empty_tracker(self):
        tracker = DebateStateTracker()
        assert tracker.get_open_issues() == []
        assert tracker.get_resolved_issues() == []
        assert tracker.has_blocking_issues() is False


# ═══════════════════════════════════════════════════════════
# TESTES DE PROMPT GENERATION
# ═══════════════════════════════════════════════════════════

class TestPromptGeneration:
    """Testes para geração de prompts contextuais."""

    def test_open_issues_prompt_with_issues(self):
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | Sem autenticação no endpoint |\n"
            "| ISS-02 | MED | COMPLETENESS | Documentação ausente |\n"
        )
        tracker.extract_issues_from_critique(critique, 1)
        
        prompt = tracker.get_open_issues_prompt()
        
        assert "NÃO repita" in prompt
        assert "ISS-01" in prompt
        assert "ISS-02" in prompt
        assert "HIGH" in prompt
        assert "SECURITY" in prompt
        assert "Total de issues abertos: 2" in prompt

    def test_open_issues_prompt_empty(self):
        tracker = DebateStateTracker()
        prompt = tracker.get_open_issues_prompt()
        
        assert "Nenhum issue aberto" in prompt

    def test_issues_for_proponent_with_issues(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | HIGH | SECURITY | Sem auth |\n"
        tracker.extract_issues_from_critique(critique, 1)
        
        prompt = tracker.get_issues_for_proponent()
        
        assert "ISS-01" in prompt
        assert "DEVE ENDEREÇAR" in prompt
        assert "PRIORITÁRIO" in prompt  # HIGH issues marcados como prioritários

    def test_issues_for_proponent_empty(self):
        tracker = DebateStateTracker()
        prompt = tracker.get_issues_for_proponent()
        
        assert "Todos os issues" in prompt or "resolvidos" in prompt


# ═══════════════════════════════════════════════════════════
# TESTES DE CONSOLIDATION SUMMARY
# ═══════════════════════════════════════════════════════════

class TestConsolidationSummary:
    """Testes para o sumário de consolidação."""

    def test_summary_with_mixed_states(self):
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | Sem auth |\n"
            "| ISS-02 | MED | COMPLETENESS | Falta doc |\n"
        )
        tracker.extract_issues_from_critique(critique, 1)
        
        defense = "## Pontos Aceitos\n- ISS-02: Vamos documentar\n"
        tracker.extract_resolutions_from_defense(defense, 1)
        
        summary = tracker.get_consolidation_summary()
        
        assert "Estado Final do Debate" in summary
        assert "Issues Resolvidos" in summary
        assert "Issues NÃO Resolvidos" in summary
        assert "ISS-01" in summary
        assert "ISS-02" in summary
        assert "⚠️ SIM" in summary  # has_blocking = True (ISS-01 HIGH OPEN)

    def test_summary_all_resolved(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | LOW | CONSISTENCY | Minor |\n"
        tracker.extract_issues_from_critique(critique, 1)
        
        defense = "## Pontos Aceitos\n- ISS-01: OK\n"
        tracker.extract_resolutions_from_defense(defense, 1)
        
        summary = tracker.get_consolidation_summary()
        
        assert "Todos os issues foram resolvidos" in summary
        assert "✅ NÃO" in summary  # has_blocking = False

    def test_summary_empty_tracker(self):
        tracker = DebateStateTracker()
        summary = tracker.get_consolidation_summary()
        
        assert "Total de issues rastreados:** 0" in summary

    def test_summary_contains_stats(self):
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | A |\n"
            "| ISS-02 | MED | CORRECTNESS | B |\n"
            "| ISS-03 | LOW | CONSISTENCY | C |\n"
        )
        tracker.extract_issues_from_critique(critique, 1)
        
        summary = tracker.get_consolidation_summary()
        
        assert "Total de issues rastreados:** 3" in summary
        assert "Resolvidos/Aceitos:** 0" in summary
        assert "Ainda abertos:** 3" in summary


# ═══════════════════════════════════════════════════════════
# TESTES DE MULTI-ROUND
# ═══════════════════════════════════════════════════════════

class TestMultiRoundTracking:
    """Testes simulando múltiplas rodadas de debate."""

    def test_two_round_flow(self):
        tracker = DebateStateTracker()
        
        # Round 1: Critic levanta 2 issues
        critique_r1 = (
            "| ISS-01 | HIGH | SECURITY | Sem autenticação |\n"
            "| ISS-02 | MED | COMPLETENESS | Sem testes |\n"
        )
        new_r1 = tracker.extract_issues_from_critique(critique_r1, 1)
        assert len(new_r1) == 2
        assert len(tracker.get_open_issues()) == 2
        
        # Round 1: Proponent resolve ISS-01
        defense_r1 = "## Pontos Aceitos\n- ISS-01: Vamos adicionar JWT\n"
        resolved_r1 = tracker.extract_resolutions_from_defense(defense_r1, 1)
        assert "ISS-01" in resolved_r1
        assert len(tracker.get_open_issues()) == 1
        
        # Round 2: Critic levanta 1 novo issue (NÃO repete ISS-01 ou ISS-02)
        critique_r2 = (
            "| ISS-03 | HIGH | CORRECTNESS | Lógica de cálculo errada |\n"
        )
        new_r2 = tracker.extract_issues_from_critique(critique_r2, 2)
        assert len(new_r2) == 1
        assert "ISS-03" in new_r2
        
        # Estado final: ISS-01 resolvido, ISS-02 e ISS-03 abertos
        assert len(tracker.get_open_issues()) == 2
        assert len(tracker.get_resolved_issues()) == 1
        assert tracker.has_blocking_issues() is True  # ISS-03 é HIGH

    def test_three_round_progressive_resolution(self):
        tracker = DebateStateTracker()
        
        # Round 1
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | Auth |\n"
            "| ISS-02 | HIGH | CORRECTNESS | Logic |\n", 1
        )
        assert tracker.has_blocking_issues() is True
        
        # Round 1 defense
        tracker.extract_resolutions_from_defense(
            "## Pontos Aceitos\n- ISS-01: Corrigido\n", 1
        )
        assert tracker.has_blocking_issues() is True  # ISS-02 still HIGH OPEN
        
        # Round 2
        tracker.extract_issues_from_critique(
            "| ISS-03 | LOW | CONSISTENCY | Minor |\n", 2
        )
        
        # Round 2 defense
        tracker.extract_resolutions_from_defense(
            "## Pontos Aceitos\n- ISS-02: Lógica corrigida\n- ISS-03: OK\n", 2
        )
        
        # Todos resolvidos
        assert tracker.has_blocking_issues() is False
        assert len(tracker.get_open_issues()) == 0
        assert len(tracker.get_resolved_issues()) == 3


# ═══════════════════════════════════════════════════════════
# TESTES DE GET_STATS
# ═══════════════════════════════════════════════════════════

class TestGetStats:
    """Testes para o método get_stats."""

    def test_stats_empty(self):
        tracker = DebateStateTracker()
        stats = tracker.get_stats()
        
        assert stats["total"] == 0
        assert stats["open"] == 0
        assert stats["resolved"] == 0
        assert stats["has_blocking"] is False
        assert stats["rounds_tracked"] == 0

    def test_stats_after_activity(self):
        tracker = DebateStateTracker()
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | X |\n"
            "| ISS-02 | LOW | CONSISTENCY | Y |\n", 1
        )
        tracker.extract_resolutions_from_defense(
            "## Pontos Aceitos\n- ISS-02: OK\n", 1
        )
        
        stats = tracker.get_stats()
        assert stats["total"] == 2
        assert stats["open"] == 1
        assert stats["resolved"] == 1
        assert stats["has_blocking"] is True
        assert stats["rounds_tracked"] == 1


# ═══════════════════════════════════════════════════════════
# TESTES DE EDGE CASES E RESILIÊNCIA
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    """Testes de degradação graciosa."""

    def test_malformed_table_no_crash(self):
        tracker = DebateStateTracker()
        critique = (
            "| sem | formato | correto |\n"
            "| ISS-INVALID | XYZ | | broken |\n"
            "Texto livre sem estrutura\n"
        )
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        # Deve retornar lista vazia (graceful degradation), não crashar
        assert isinstance(new_ids, list)

    def test_special_chars_in_description(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | HIGH | SECURITY | Falha com chars: <script>alert('xss')</script> |\n"
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        
        assert len(new_ids) == 1

    def test_very_long_description_truncated(self):
        tracker = DebateStateTracker()
        long_desc = "A" * 500
        critique = f"| ISS-01 | HIGH | SECURITY | {long_desc} |\n"
        tracker.extract_issues_from_critique(critique, 1)
        
        assert len(tracker.issues["ISS-01"].description) <= 200

    def test_auto_id_generation_skips_existing(self):
        tracker = DebateStateTracker()
        # Registrar ISS-01 via tabela
        tracker.extract_issues_from_critique("| ISS-01 | HIGH | SECURITY | X |\n", 1)
        
        # Registrar via bullet (auto-ID) — deve gerar ISS-02, não ISS-01
        tracker.extract_issues_from_critique("- [MED] Outro problema diferente do primeiro\n", 2)
        
        assert "ISS-01" in tracker.issues
        assert "ISS-02" in tracker.issues
        assert len(tracker.issues) == 2

    def test_pipe_in_description_handled(self):
        """Pipe characters na descrição não quebram o parser."""
        tracker = DebateStateTracker()
        critique = "| ISS-01 | HIGH | SECURITY | Input com | chars estranhos |\n"
        # O regex pode capturar parcialmente, mas não deve crashar
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        assert isinstance(new_ids, list)
