"""
test_phase_9_consistency.py — Testes de Verificação da Fase 9.0/9.1.
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
            "| RF-01 | Login do usuário no sistema |\n\n"
            "## Escopo\n"
            "O projeto inclui RF-01 e RF-02."
        )
        report = self.checker.check_consistency(prd_content)
        self.assertIn("RF-02", report)
        self.assertIn("CRITICAL: RF_ORPHAN", report)

    def test_02_clean_prd(self):
        """Verifica se um PRD consistente passa sem erros."""
        prd_content = (
            "## Visão do Produto\n- Codinome: Project Nexus Forge\n- Visão: Unificar processos.\n\n"
            "## Problema e Solução\n| ID | Problema | Impacto | Resolução |\n|---|---|---|---|\n| P-01 | Falta de dados | Alto | Criar pipeline |\n\n"
            "## Público-Alvo\n| Segmento | Perfil | Prioridade |\n|---|---|---|\n| Developer | Senior | P0 |\n\n"
            "## Princípios Arquiteturais\n| Princípio | Descrição | Implicação |\n|---|---|---|\n| Simplicity | Keep it simple | Easy maintenance |\n\n"
            "## Diferenciais\n| Atual | Problema | Supera |\n|---|---|---|\n| Manual | Lento | Automatizado |\n\n"
            "## Requisitos Funcionais\n| ID | Requisito | Aceite |\n|---|---|---|\n| RF-01 | Login | Auth OK |\n| RF-02 | Logout | Session End |\n\n"
            "## Requisitos Não-Funcionais\n| ID | Categoria | Requisito | Métrica | Target |\n|---|---|---|---|---|\n| RNF-01 | Perf | Latência | Tempo | <200ms |\n\n"
            "## Arquitetura e Tech Stack\n| Camada | Tech | Justificativa |\n|---|---|---|\n| Backend | FastAPI | Async support |\n\n"
            "## ADRs\n| ID | Decisão | Alternativa | Razão |\n|---|---|---|---|\n| ADR-01 | SQLite | Postgres | Simplicity |\n\n"
            "## Análise de Segurança\n| ID | Ameaça | Componente | Mitigação |\n|---|---|---|---|\n| S-01 | Spoofing | Identity | JWT |\n\n"
            "## Escopo MVP\n**Inclui:** RF-01 e RF-02. **NÃO inclui:** IA Generativa.\n\n"
            "## Riscos Consolidados\n| ID | Risco | Fonte | Mitigação |\n|---|---|---|---|\n| R-01 | API Offline | External | Retry policy |\n\n"
            "## Métricas de Sucesso\n| Métrica | Target | Prazo | Medição |\n|---|---|---|---|\n| Uptime | 99.9% | Mensal | Monitoring |\n\n"
            "## Plano de Implementação\n| Fase | Duração | Entrega | Status |\n|---|---|---|---|\n| F-01 | 2 weeks | Core MVP | Planned |\n\n"
            "## Decisões do Debate\n- Decidido usar Docker para padronização do ambiente.\n\n"
            "## Constraints Técnicos\n- Deve rodar em Python 3.10 ou superior.\n\n"
            "## Matriz de Rastreabilidade\n| RF-ID | Módulo | Teste | Status |\n|---|---|---|---|\n| RF-01 | Auth | test_01 | OK |\n\n"
            "## Limitações Conhecidas\n| ID | Limite | Impacto | Solução |\n|---|---|---|---|\n| L-01 | No Mobile | Niche | v2 roadmap |\n\n"
            "## Guia de Replicação Resumido\n1. Clonar repo. 2. Instalar deps. 3. Rodar main.\n\n"
            "## Cláusula de Integridade\n| Item | Validação | Status |\n|---|---|---|\n| RFs | Checked | ✅ |\n\n"
            "Este texto adicional serve para garantir que o PRD tenha o tamanho mínimo de 1000 caracteres exigido para o prd_final. " * 5
        )
        report = self.checker.check_consistency(prd_content)
        if "**is_clean:** True" not in report:
            self.fail(f"Report not clean (missing **is_clean:** True):\n{report}")
        self.assertIn("**is_clean:** True", report)
        self.assertIn("**checks_executados:** 6", report)

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
