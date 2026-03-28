import unittest
from src.core.output_validator import OutputValidator

class TestOutputValidatorV2(unittest.TestCase):
    def setUp(self):
        self.validator = OutputValidator()

    def test_validate_pass_success(self):
        content = (
            "## Objetivo\n- Teste de objetivo longo o suficiente para passar no validador seccional\n\n"
            "## Problema\n| ID | Prob | Imp | Sol |\n|---|---|---|---|\n| 1 | P1 | H | S1 |"
        )
        sections = ["## Objetivo", "## Problema"]
        res = self.validator.validate_pass(content, sections, require_table=True, min_chars=50)
        self.assertTrue(res["valid"])

    def test_validate_prd_nexus_sections(self):
        content = (
            "## Objetivo\n- Teste de objetivo extremamente longo para garantir que passe no threshold de caracteres do NEXUS.\n\n"
            "## Problema\n| ID | Prob | Imp | Resolve |\n|---|---|---|---|\n| P-01 | X | Y | Z |\n\n"
            "## Público-Alvo\n| Seg | Perfil | Prio |\n|---|---|---|\n| Dev | Lucas | P0 |\n\n"
            "## Princípios Arquiteturais\n| Princ | Desc | Impl |\n|---|---|---|\n| Local | Tudo local | Zero cloud |\n\n"
            "## Requisitos Funcionais\n| ID | Req | Aceite | Prio | Complex |\n|---|---|---|---|---|\n| RF-01 | X | Y | Must | Low |\n\n"
            "## Requisitos Não-Funcionais\n| ID | Cat | Req | Met | Tgt |\n|---|---|---|---|---|\n| RNF-01 | Perf | Lat | p95 | 200ms |\n\n"
            "## Escopo MVP\n**Inclui:** RF-01\n**NÃO inclui:** Mobile\n\n"
            "## Métricas de Sucesso\n| Met | Tgt | Prazo | Medir |\n|---|---|---|---|\n| Users | 100 | 30d | Analytics |\n\n"
            "## Dependências e Riscos\n| ID | Tipo | Desc | Prob | Imp | Mit |\n|---|---|---|---|---|---|\n| R-01 | Risco | DB | Média | Alto | Backup |\n\n"
            "## Diferenciais\n| Atual | Problema | Supera |\n|---|---|---|\n| Chat GPT | Sem estrutura | Pipeline cognitivo |\n\n"
            "## Constraints Técnicos\n- Linguagem: Python\n"
            "Este texto adicional serve para garantir que o conteúdo total tenha mais de 600 caracteres, "
            "que é o requisito mínimo para o PRD no padrão NEXUS Calibração Fase 7. "
            "A densidade e a completude são essenciais para a aprovação final do artefato gerado pelo IdeaForge."
        )
        res = self.validator.validate(content, "prd")
        self.assertTrue(res["valid"], f"Falha na validação: {res.get('fail_reasons')}")
        self.assertGreaterEqual(res["completeness_score"], 0.75)

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

    def test_validate_prd_final_dedicated_type(self):
        """FASE 8.0a: prd_final usa tipo dedicado com 16 seções NEXUS."""
        content = (
            "## Visão do Produto\n- Codinome: TestApp\n- Declaração: Teste\n\n"
            "## Problema e Solução\n| ID | P | I | R |\n|---|---|---|---|\n| P-01 | X | Y | Z |\n\n"
            "## Público-Alvo\n| Seg | Perfil | Prio |\n|---|---|---|\n| Dev | Lucas | P0 |\n\n"
            "## Princípios Arquiteturais\n| P | D | I |\n|---|---|---|\n| X | Y | Z |\n\n"
            "## Diferenciais\n| A | P | S |\n|---|---|---|\n| X | Y | Z |\n\n"
            "## Requisitos Funcionais\n| ID | R | CA | P | Cx | S |\n|---|---|---|---|---|---|\n| RF-01 | X | Y | Must | Low | OK |\n\n"
            "## Requisitos Não-Funcionais\n| ID | C | R | M | T |\n|---|---|---|---|---|\n| RNF-01 | Perf | Lat | p95 | 200ms |\n\n"
            "## Arquitetura e Tech Stack\n| C | T | J |\n|---|---|---|\n| Backend | FastAPI | Async |\n\n"
            "## ADRs\n| ID | D | AR | C |\n|---|---|---|---|\n| ADR-01 | SQLite | PG | Simplicidade |\n\n"
            "## Análise de Segurança\n| ID | A | C | S | M |\n|---|---|---|---|---|\n| SEC-01 | Spoofing | Auth | Alta | Rate limit |\n\n"
            "## Escopo MVP\n**Inclui:** RF-01\n**NÃO inclui:** Mobile\n\n"
            "## Riscos Consolidados\n| ID | R | F | P | I | M |\n|---|---|---|---|---|---|\n| R-01 | X | PRD | M | A | Backup |\n\n"
            "## Métricas de Sucesso\n| M | T | P | CM |\n|---|---|---|---|\n| Users | 100 | 30d | GA |\n\n"
            "## Plano de Implementação\n| F | D | E | CC |\n|---|---|---|---|\n| F1 | 2s | Core | Tests |\n\n"
            "## Decisões do Debate\n- Adoção de ISR + SWR\n\n"
            "## Constraints Técnicos\n- Linguagem: Python\n- Framework: FastAPI\n"
            "Texto adicional para garantir 800+ caracteres no PRD Final consolidado. " * 3
        )
        res = self.validator.validate(content, "prd_final")
        self.assertTrue(res["valid"], f"Falha: {res.get('fail_reasons')}")
        self.assertGreaterEqual(res["completeness_score"], 0.70)

    def test_prd_final_not_validated_as_prd(self):
        """FASE 8.0a: prd_final com seções NEXUS passa em prd_final mas pode falhar em prd."""
        # Verificar que o tipo prd_final existe e tem seções diferentes do prd
        prd_sections = set(self.validator.REQUIRED_SECTIONS["prd"])
        prd_final_sections = set(self.validator.REQUIRED_SECTIONS["prd_final"])
        # As seções DEVEM ser diferentes (prd tem "## Objetivo", prd_final tem "## Visão do Produto")
        self.assertNotEqual(prd_sections, prd_final_sections)
        self.assertIn("## Visão do Produto", prd_final_sections)
        self.assertNotIn("## Visão do Produto", prd_sections)
        self.assertIn("## Objetivo", prd_sections)
        self.assertNotIn("## Objetivo", prd_final_sections)

if __name__ == "__main__":
    unittest.main()
