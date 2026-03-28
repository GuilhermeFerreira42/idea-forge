"""
test_phase_9_consistency.py — Testes de Verificação da Fase 9.0.
"""

import unittest
from src.agents.consistency_checker_agent import ConsistencyCheckerAgent
from src.debate.debate_engine import DebateEngine

class TestPhase9(unittest.TestCase):
    def setUp(self):
        self.checker = ConsistencyCheckerAgent()

    def test_01_orphan_rf_detection(self):
        """Verifica se o auditor detecta RFs referenciados mas não definidos."""
        prd_content = (
            "## Requisitos Funcionais\n"
            "| ID | Requisito |\n"
            "|---|---|\n"
            "| RF-01 | Login |\n\n"
            "## Escopo\n"
            "O projeto inclui RF-01 e RF-02."
        )
        report = self.checker.check_consistency(prd_content)
        self.assertIn("RF-02", report)
        self.assertIn("CRITICAL: RF_ORPHAN", report)

    def test_02_clean_prd(self):
        """Verifica se um PRD consistente passa sem erros."""
        prd_content = (
            "## Objetivo\n"
            "O objetivo deste sistema é permitir o gerenciamento de tarefas complexas de forma eficiente e segura.\n\n"
            "## Requisitos Funcionais\n"
            "| ID | Requisito |\n"
            "|---|---|\n"
            "| RF-01 | Login |\n"
            "| RF-02 | Logout |\n\n"
            "## Escopo MVP\n"
            "Inclui RF-01 e RF-02.\n\n"
            "## Requisitos Não-Funcionais\n"
            "| ID | Categoria | Requisito | Métrica | Target |\n"
            "| RNF-01 | Performance | Latência | Tempo | <200ms |\n"
        )
        report = self.checker.check_consistency(prd_content)
        if "**is_clean:** True" not in report:
            self.fail(f"Report not clean (missing **is_clean:** True):\n{report}")
        self.assertIn("**is_clean:** True", report)

    def test_03_failed_section_detection(self):
        """Verifica detecção de marcadores de falha."""
        prd_content = (
            "## Visão do Produto\n"
            "O SISTEMA GERAÇÃO FALHOU nesta seção.\n"
        )
        report = self.checker.check_consistency(prd_content)
        self.assertIn("CRITICAL: FAILED_SECTIONS", report)

    def test_04_debate_decision_extraction(self):
        """Verifica se o DebateEngine extrai decisões corretamente."""
        engine = DebateEngine(None, None, rounds=1)
        engine.debate_transcript = [
            (
                "Proponente: Olá.\n"
                "## Pontos Aceitos\n"
                "- Usar FastAPI em vez de Flask\n"
            ),
            "Crítico: Concordo.",
            (
                "Proponente: Melhorias.\n"
                "## Melhorias Propostas\n"
                "| Área | Mudança | Justificativa |\n"
                "| Segurança | Adicionar Rate Limit | Evitar brute force |\n"
            )
        ]
        
        report = engine._extract_decisions_from_transcript()
        self.assertIn("FastAPI", report)
        self.assertIn("Rate Limit", report)

if __name__ == "__main__":
    unittest.main()
