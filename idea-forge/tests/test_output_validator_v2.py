import unittest
from src.core.output_validator import OutputValidator

class TestOutputValidatorV2(unittest.TestCase):
    def setUp(self):
        self.validator = OutputValidator()

    def test_validate_pass_success(self):
        content = "## Objetivo\n- Teste\n\n## Problema\n| ID | Prob |\n|---|---|\n| 1 | P1 |"
        sections = ["## Objetivo", "## Problema"]
        res = self.validator.validate_pass(content, sections, require_table=True, min_chars=50)
        self.assertTrue(res["valid"])

    def test_validate_pass_missing_section(self):
        content = "## Objetivo\n- Teste"
        sections = ["## Objetivo", "## Problema"]
        res = self.validator.validate_pass(content, sections, min_chars=10) # Reduzir min_chars para focar em seções
        self.assertFalse(res["valid"])
        self.assertTrue(any("MISSING_SECTIONS" in r for r in res["fail_reasons"]))

    def test_validate_pass_too_short(self):
        content = "## Objetivo\n- Hi"
        sections = ["## Objetivo"]
        res = self.validator.validate_pass(content, sections, min_chars=100)
        self.assertFalse(res["valid"])
        self.assertTrue(any("TOO_SHORT" in r for r in res["fail_reasons"]))

    def test_validate_pass_no_table(self):
        content = "## Objetivo\n- Teste\n\n## Problema\nSem tabela"
        sections = ["## Objetivo", "## Problema"]
        res = self.validator.validate_pass(content, sections, require_table=True, min_chars=10)
        self.assertFalse(res["valid"])
        self.assertIn("NO_TABLE", res["fail_reasons"])

    def test_is_placeholder_heavy(self):
        # Case 1: Bullets
        content = "## Objetivo\n- A DEFINIR\n- A DEFINIR\n- A DEFINIR"
        self.assertTrue(self.validator.is_placeholder_heavy(content))
        
        # Case 2: Table
        content = "## Problema\n| ID | Res |\n|---|---|\n| 1 | ... |\n| 2 | ... |"
        self.assertTrue(self.validator.is_placeholder_heavy(content))
        
        content = "## Objetivo\n- Algo concreto aqui\n- Outra coisa real"
        self.assertFalse(self.validator.is_placeholder_heavy(content))

    def test_hard_gate_validation_empty(self):
        content = ""
        res = self.validator.validate(content, "prd")
        self.assertFalse(res["valid"])
        self.assertIn("EMPTY_CONTENT", res["fail_reasons"])

if __name__ == "__main__":
    unittest.main()
