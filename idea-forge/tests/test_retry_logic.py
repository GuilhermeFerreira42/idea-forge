import unittest
from unittest.mock import MagicMock, patch
from src.core.sectional_generator import SectionalGenerator, SectionPass

class TestRetryLogic(unittest.TestCase):
    def setUp(self):
        self.mock_provider = MagicMock()
        self.generator = SectionalGenerator(self.mock_provider)

    def test_execute_pass_with_retry_success_first_time(self):
        section_pass = SectionPass(
            "test_p1", ["## S1"], "## S1", "", "Inst", min_chars=10, require_table=False
        )
        self.mock_provider.generate.return_value = "## S1\nConteúdo válido"
        
        res = self.generator._execute_pass_with_retry(
            section_pass, "input", "ctx", "", 1, 1
        )
        
        self.assertIsNotNone(res)
        self.assertEqual(self.mock_provider.generate.call_count, 1)

    def test_execute_pass_with_retry_success_after_failure(self):
        section_pass = SectionPass(
            "test_p1", ["## S1"], "## S1", "", "Inst", min_chars=10, require_table=False
        )
        # Primeira falha (vazio), segunda sucesso
        self.mock_provider.generate.side_effect = [
            "", 
            "## S1\nAgora vai"
        ]
        
        res = self.generator._execute_pass_with_retry(
            section_pass, "input", "ctx", "", 1, 1
        )
        
        self.assertIsNotNone(res)
        self.assertEqual(self.mock_provider.generate.call_count, 2)

    def test_execute_pass_failed_after_all_retries(self):
        section_pass = SectionPass(
            "test_p1", ["## S1"], "## S1", "", "Inst", min_chars=10, require_table=False
        )
        # Falha constante
        self.mock_provider.generate.return_value = "Nada a ver"
        
        res = self.generator._execute_pass_with_retry(
            section_pass, "input", "ctx", "", 1, 1
        )
        
        self.assertIsNone(res)
        # 1 original + 1 retry = 2 calls (FASE 9.6)
        self.assertEqual(self.mock_provider.generate.call_count, 2)

    def test_section_pass_accepts_input_budget(self):
        """FASE 9.1.1: SectionPass deve aceitar input_budget."""
        sp = SectionPass(
            "test", ["## S1"], "## S1", "", "Inst",
            min_chars=10, require_table=False, input_budget=3000
        )
        self.assertEqual(sp.input_budget, 3000)

    def test_section_pass_default_input_budget(self):
        """FASE 9.1.1: SectionPass sem input_budget deve ter default 1000 (FASE 9.6)."""
        sp = SectionPass(
            "test", ["## S1"], "## S1", "", "Inst",
            min_chars=10, require_table=False
        )
        self.assertEqual(sp.input_budget, 1000)

if __name__ == "__main__":
    unittest.main()

