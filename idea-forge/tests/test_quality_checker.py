
import unittest
from src.core.section_quality_checker import SectionQualityChecker

class TestSectionQualityChecker(unittest.TestCase):
    def setUp(self):
        self.checker = SectionQualityChecker()

    def test_check_section_by_type_short(self):
        # Visão do Produto requires 200 chars
        content = "Curto"
        feedback = self.checker.check_section_by_type("## Visão do Produto", content)
        self.assertTrue(any("apenas 5 chars" in f for f in feedback))

    def test_check_section_by_type_missing_keywords(self):
        # Visão do Produto requires 'codinome' and 'visão'
        content = "A" * 250
        feedback = self.checker.check_section_by_type("## Visão do Produto", content)
        self.assertTrue(any("keyword obrigatória 'codinome' não encontrada" in f for f in feedback))

    def test_check_section_by_type_missing_items(self):
        # Problema e Solução requires 5 items matching P-\d+
        content = "## Problema e Solução\n" + "A" * 1600
        feedback = self.checker.check_section_by_type("## Problema e Solução", content)
        self.assertTrue(any("apenas 0 itens encontrados" in f for f in feedback))

    def test_check_section_by_type_pass(self):
        content = "## Visão do Produto\nCodinome: Forge. Nossa visão é expandir." + "A" * 200
        feedback = self.checker.check_section_by_type("## Visão do Produto", content)
        self.assertEqual(len(feedback), 0)

    def test_split_sections(self):
        prd = "## Visão do Produto\nContent 1\n## Problema e Solução\nContent 2"
        sections = self.checker._split_sections(prd)
        self.assertIn("## Visão do Produto", sections)
        self.assertIn("## Problema e Solução", sections)
        self.assertEqual(sections["## Visão do Produto"], "Content 1")

if __name__ == "__main__":
    unittest.main()
