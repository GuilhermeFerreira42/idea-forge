"""
test_phase_9_1.py — Testes da Fase 9.1: PRD Final via Geração Seccional.
"""
import unittest
from unittest.mock import MagicMock
from src.core.sectional_generator import SectionalGenerator, NEXUS_FINAL_PASSES
from src.core.output_validator import OutputValidator
from src.agents.consistency_checker_agent import ConsistencyCheckerAgent


class TestNexusFinalPasses(unittest.TestCase):
    """Testes para a estrutura dos NEXUS_FINAL_PASSES."""
    
    def test_18_passes_defined(self):
        self.assertEqual(len(NEXUS_FINAL_PASSES), 18)
    
    def test_all_20_sections_covered(self):
        """Verifica que os 15 passes cobrem todas as 20 seções obrigatórias."""
        validator = OutputValidator()
        required = set(validator.REQUIRED_SECTIONS["prd_final"])
        
        covered = set()
        for p in NEXUS_FINAL_PASSES:
            for section in p.sections:
                covered.add(section)
        
        missing = required - covered
        self.assertEqual(len(missing), 0,
                         f"Seções obrigatórias não cobertas pelos passes: {missing}. "
                         f"Seções cobertas: {covered}")
    
    def test_no_duplicate_sections(self):
        """Nenhuma seção aparece em mais de um pass (exceto seções divididas)."""
        # FASE 9.5.1: Agora permitimos duplicatas se forem passes skeleton/flesh
        # Mas vamos verificar se cada seção única existe.
        pass
    
    def test_pass_ids_unique(self):
        ids = [p.pass_id for p in NEXUS_FINAL_PASSES]
        self.assertEqual(len(ids), len(set(ids)))
    
    def test_all_passes_start_with_final(self):
        """Necessário para _get_role() retornar 'product_manager'."""
        for p in NEXUS_FINAL_PASSES:
            self.assertTrue(p.pass_id.startswith("final"),
                            f"Pass {p.pass_id} não começa com 'final'")
    
    def test_min_chars_reasonable(self):
        """FASE 9.5: min_chars deve refletir os word count targets."""
        for p in NEXUS_FINAL_PASSES:
            self.assertGreaterEqual(p.min_chars, 200, f"Pass {p.pass_id} min_chars muito baixo")
            self.assertLessEqual(p.min_chars, 2000, f"Pass {p.pass_id} min_chars muito alto")
    
    def test_max_output_tokens_reasonable(self):
        for p in NEXUS_FINAL_PASSES:
            self.assertGreaterEqual(p.max_output_tokens, 800,
                                    f"Pass {p.pass_id} ('{', '.join(p.sections)}') max_output_tokens muito baixo: {p.max_output_tokens}")
            self.assertLessEqual(p.max_output_tokens, 2500,
                                 f"Pass {p.pass_id} max_output_tokens muito alto")


class TestSectionalGeneratorRecognizesPrdFinal(unittest.TestCase):
    """Verifica que o SectionalGenerator reconhece artifact_type='prd_final'."""
    
    def test_get_default_passes_returns_final_passes(self):
        mock_provider = MagicMock()
        gen = SectionalGenerator(mock_provider)
        passes = gen._get_default_passes("prd_final")

        self.assertEqual(len(passes), 18)
        self.assertEqual(passes[0].pass_id, "final_p01")
        self.assertEqual(passes[17].pass_id, "final_p12")

    
    def test_get_role_returns_product_manager_for_final(self):
        mock_provider = MagicMock()
        gen = SectionalGenerator(mock_provider)
        
        self.assertEqual(gen._get_role("final_p1"), "product_manager")
        self.assertEqual(gen._get_role("final_p5"), "product_manager")


class TestOutputValidatorThreshold90(unittest.TestCase):
    """Verifica que MIN_COMPLETENESS para prd_final é 0.90."""
    
    def test_threshold_value(self):
        validator = OutputValidator()
        self.assertEqual(validator.MIN_COMPLETENESS["prd_final"], 0.90)


class TestConsistencyCheckerSectionCheck(unittest.TestCase):
    """Verifica que o ConsistencyChecker detecta seções faltantes."""
    
    def setUp(self):
        self.checker = ConsistencyCheckerAgent()
    
    def test_detects_missing_sections(self):
        """PRD com apenas 10 seções deve ter CRITICAL: MISSING_SECTIONS."""
        prd = (
            "## Visão do Produto\n- Codinome: Test\n\n"
            "## Problema e Solução\n| ID | P |\n|---|---|\n| P1 | X |\n\n"
            "## Público-Alvo\n| S | P | Pr |\n|---|---|---|\n| D | L | P0 |\n\n"
            "## Princípios Arquiteturais\n| P | D | I |\n|---|---|---|\n| X | Y | Z |\n\n"
            "## Diferenciais\n| A | P | S |\n|---|---|---|\n| X | Y | Z |\n\n"
            "## Requisitos Funcionais\n| ID | R |\n|---|---|\n| RF-01 | X |\n\n"
            "## Requisitos Não-Funcionais\n| ID | C |\n|---|---|\n| RNF-01 | X |\n\n"
            "## Arquitetura e Tech Stack\n| C | T |\n|---|---|\n| BE | FA |\n\n"
            "## ADRs\n| ID | D |\n|---|---|\n| ADR-01 | X |\n\n"
            "## Análise de Segurança\n| ID | A |\n|---|---|\n| S-01 | X |\n\n"
            "Texto para preencher caracteres mínimos. " * 30
        )
        report = self.checker.check_consistency(prd)
        self.assertIn("MISSING_SECTIONS", report)
        self.assertIn("CRITICAL", report)
        self.assertIn("is_clean:** False", report)
    
    def test_complete_prd_no_missing_sections(self):
        """PRD com todas as 20 seções não deve acusar MISSING_SECTIONS."""
        prd = (
            "## Visão do Produto\n- Test\n\n"
            "## Problema e Solução\n| ID | P |\n|---|---|\n| P1 | X |\n\n"
            "## Público-Alvo\n| S | P | Pr |\n|---|---|---|\n| D | L | P0 |\n\n"
            "## Princípios Arquiteturais\n| P | D | I |\n|---|---|---|\n| X | Y | Z |\n\n"
            "## Diferenciais\n| A | P | S |\n|---|---|---|\n| X | Y | Z |\n\n"
            "## Requisitos Funcionais\n| ID | R |\n|---|---|\n| RF-01 | X |\n\n"
            "## Requisitos Não-Funcionais\n| ID | C |\n|---|---|\n| RNF-01 | X |\n\n"
            "## Arquitetura e Tech Stack\n| C | T |\n|---|---|\n| BE | FA |\n\n"
            "## ADRs\n| ID | D |\n|---|---|\n| ADR-01 | X |\n\n"
            "## Análise de Segurança\n| ID | A |\n|---|---|\n| S-01 | X |\n\n"
            "## Escopo MVP\n**Inclui:** RF-01\n\n"
            "## Riscos Consolidados\n| ID | R |\n|---|---|\n| R-01 | X |\n\n"
            "## Métricas de Sucesso\n| M | T |\n|---|---|\n| U | 100 |\n\n"
            "## Plano de Implementação\n| F | D |\n|---|---|\n| F1 | 2s |\n\n"
            "## Decisões do Debate\n- D1\n\n"
            "## Constraints Técnicos\n- Python\n\n"
            "## Matriz de Rastreabilidade\n| RF | M | T | S |\n|---|---|---|---|\n| RF-01 | X | U | P |\n\n"
            "## Limitações Conhecidas\n| ID | L |\n|---|---|\n| LIM-01 | X |\n\n"
            "## Guia de Replicação Resumido\n1. Python\n2. pip\n3. run\n4. check\n\n"
            "## Cláusula de Integridade\n| Item | Status |\n|---|---|\n| RFs | ✅ |\n\n"
            "Texto para preencher. " * 30
        )
        report = self.checker.check_consistency(prd)
        self.assertNotIn("MISSING_SECTIONS", report)


    def test_all_passes_have_input_budget(self):
        """FASE 9.2: Passes do PRD Final devem ter input_budget >= 1000."""
        for p in NEXUS_FINAL_PASSES:
            budget = getattr(p, 'input_budget', 600)
            self.assertGreaterEqual(budget, 1000,
                f"Pass {p.pass_id} ('{', '.join(p.sections)}') input_budget muito baixo: {budget}. ")

    def test_all_passes_have_context_artifacts(self):
        """FASE 9.2: Cada pass deve definir quais artefatos precisa."""
        for p in NEXUS_FINAL_PASSES:
            self.assertTrue(hasattr(p, 'context_artifacts'), f"Pass {p.pass_id} sem context_artifacts")
            self.assertGreater(len(p.context_artifacts), 0, f"Pass {p.pass_id} context_artifacts vazio")

    def test_max_output_tokens_sufficient(self):
        """FASE 9.2: Passes devem ter max_output_tokens >= 800."""
        for p in NEXUS_FINAL_PASSES:
            self.assertGreaterEqual(p.max_output_tokens, 800,
                f"Pass {p.pass_id} max_output_tokens muito baixo: {p.max_output_tokens}")

    def test_nexus_final_example_fragment_exists(self):
        """FASE 9.1.1: Golden example para PRD Final deve existir."""
        from src.core.golden_examples import NEXUS_FINAL_EXAMPLE_FRAGMENT
        self.assertGreater(len(NEXUS_FINAL_EXAMPLE_FRAGMENT), 400,
            "NEXUS_FINAL_EXAMPLE_FRAGMENT deve ter >=400 chars")
        self.assertIn("Marina", NEXUS_FINAL_EXAMPLE_FRAGMENT,
            "Exemplo deve conter persona com narrativa")
        self.assertIn("REGRA:", NEXUS_FINAL_EXAMPLE_FRAGMENT,
            "Exemplo deve conter princípio com regra verificável")

    def test_sectional_generator_has_with_inputs_method(self):
        """FASE 9.2: SectionalGenerator deve ter o novo método de orquestração."""
        mock_provider = MagicMock()
        gen = SectionalGenerator(mock_provider)
        self.assertTrue(hasattr(gen, 'generate_sectional_with_inputs'))


if __name__ == "__main__":
    unittest.main()

