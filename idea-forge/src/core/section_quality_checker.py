"""
section_quality_checker.py — Verificador programático de qualidade por seção.

FASE 9.5: Extensão do ConsistencyChecker para garantir densidade mínima.
Opera SEM LLM — verificação puramente programática.
"""
import re
from typing import Dict, List, Tuple


class SectionQualityChecker:
    """Verifica se cada seção do PRD Final atinge os thresholds mínimos de qualidade."""

    SECTION_RULES = {
        "## Visão do Produto": {
            "min_chars": 200,
            "min_items": 0,
            "item_pattern": None,
            "required_keywords": ["codinome", "visão"],
        },
        "## Problema e Solução": {
            "min_chars": 1500,
            "min_items": 5,
            "item_pattern": r"\|\s*P-\d+\s*\|",
            "required_keywords": [],
        },
        "## Público-Alvo": {
            "min_chars": 600,
            "min_items": 3,
            "item_pattern": r"\|\s*\w+.*\|\s*P[012]\s*\|",
            "required_keywords": [],
        },
        "## Princípios Arquiteturais": {
            "min_chars": 1200,
            "min_items": 5,
            "item_pattern": r"REGRA:",
            "required_keywords": ["REGRA"],
        },
        "## Diferenciais": {
            "min_chars": 600,
            "min_items": 3,
            "item_pattern": r"\|.*\|.*\|.*\|",
            "required_keywords": [],
        },
        "## Requisitos Funcionais": {
            "min_chars": 1500,
            "min_items": 8,
            "item_pattern": r"\|\s*RF-\d+\s*\|",
            "required_keywords": [],
        },
        "## Requisitos Não-Funcionais": {
            "min_chars": 1000,
            "min_items": 8,
            "item_pattern": r"\|\s*RNF-\d+\s*\|",
            "required_keywords": [],
        },
        "## Arquitetura e Tech Stack": {
            "min_chars": 1500,
            "min_items": 3,
            "item_pattern": r"\|.*\|.*\|.*\|",
            "required_keywords": [],
        },
        "## ADRs": {
            "min_chars": 800,
            "min_items": 4,
            "item_pattern": r"ADR-\d+",
            "required_keywords": ["Alternativa", "Consequências"],
        },
        "## Análise de Segurança": {
            "min_chars": 800,
            "min_items": 5,
            "item_pattern": r"\|\s*SEC-\d+\s*\|",
            "required_keywords": [],
        },
        "## Escopo MVP": {
            "min_chars": 400,
            "min_items": 0,
            "item_pattern": None,
            "required_keywords": ["Inclui", "NÃO"],
        },
        "## Riscos Consolidados": {
            "min_chars": 1200,
            "min_items": 6,
            "item_pattern": r"\|\s*R-\d+\s*\|",
            "required_keywords": ["Workaround"],
        },
        "## Métricas de Sucesso": {
            "min_chars": 600,
            "min_items": 5,
            "item_pattern": r"\|.*\|.*\|.*\|",
            "required_keywords": [],
        },
        "## Plano de Implementação": {
            "min_chars": 800,
            "min_items": 3,
            "item_pattern": r"\|\s*\d+\s*\||\|\s*Fase\s",
            "required_keywords": [],
        },
        "## Constraints Técnicos": {
            "min_chars": 300,
            "min_items": 0,
            "item_pattern": None,
            "required_keywords": ["Linguagem", "Framework"],
        },
        "## Matriz de Rastreabilidade": {
            "min_chars": 400,
            "min_items": 4,
            "item_pattern": r"\|\s*RF-\d+\s*\|",
            "required_keywords": [],
        },
        "## Limitações Conhecidas": {
            "min_chars": 600,
            "min_items": 4,
            "item_pattern": r"\|\s*LIM-\d+\s*\|",
            "required_keywords": ["Workaround"],
        },
        "## Guia de Replicação": {
            "min_chars": 600,
            "min_items": 0,
            "item_pattern": None,
            "required_keywords": [],
        },
        "## Cláusula de Integridade": {
            "min_chars": 200,
            "min_items": 5,
            "item_pattern": r"\|.*\|.*\|",
            "required_keywords": [],
        },
    }

    def check_all_sections(self, prd_final: str) -> Dict:
        """
        Verifica todas as seções do PRD Final contra as regras definidas.
        Retorna dict com resultados e feedback por seção.
        """
        if not prd_final or len(prd_final.strip()) < 100:
            return {
                "passed": False,
                "total_sections_checked": 0,
                "failed_sections": [],
                "feedback": ["PRD insuficiente para auditoria de qualidade."],
            }

        sections = self._split_sections(prd_final)
        failed = []
        all_feedback = []

        for heading, rules in self.SECTION_RULES.items():
            content = sections.get(heading, "")
            section_feedback = self._check_section(heading, content, rules)
            if section_feedback:
                failed.append(heading)
                all_feedback.extend(section_feedback)

        return {
            "passed": len(failed) == 0,
            "total_sections_checked": len(self.SECTION_RULES),
            "sections_passed": len(self.SECTION_RULES) - len(failed),
            "failed_sections": failed,
            "feedback": all_feedback,
        }

    def check_section_by_type(self, section_heading: str, content: str) -> List[str]:
        """
        Verifica uma seção individual. Retorna lista de feedbacks (vazia = OK).
        Usado pelo SectionalGenerator no loop de retry.
        """
        rules = self.SECTION_RULES.get(section_heading)
        if not rules:
            return []
        return self._check_section(section_heading, content, rules)

    def _check_section(self, heading: str, content: str, rules: Dict) -> List[str]:
        """Verifica uma seção contra suas regras. Retorna feedbacks."""
        feedback = []

        if not content.strip():
            feedback.append(f"{heading}: seção VAZIA ou ausente.")
            return feedback

        # Check 1: comprimento mínimo
        if len(content.strip()) < rules["min_chars"]:
            feedback.append(
                f"{heading}: apenas {len(content.strip())} chars "
                f"(mínimo {rules['min_chars']}). Expanda com mais detalhes."
            )

        # Check 2: contagem de itens
        if rules["min_items"] > 0 and rules["item_pattern"]:
            count = len(re.findall(rules["item_pattern"], content, re.IGNORECASE))
            if count < rules["min_items"]:
                feedback.append(
                    f"{heading}: apenas {count} itens encontrados "
                    f"(mínimo {rules['min_items']}). Adicione mais itens."
                )

        # Check 3: keywords obrigatórias
        for kw in rules.get("required_keywords", []):
            if kw.lower() not in content.lower():
                feedback.append(
                    f"{heading}: keyword obrigatória '{kw}' não encontrada."
                )

        return feedback

    def _split_sections(self, text: str) -> Dict[str, str]:
        """Divide o PRD Final em seções pelo heading ##."""
        sections = {}
        parts = re.split(r'(?=^## )', text, flags=re.MULTILINE)
        for part in parts:
            if not part.strip():
                continue
            lines = part.strip().splitlines()
            heading = lines[0].strip()
            content = "\n".join(lines[1:]).strip()
            # Normalizar heading para matching
            for rule_heading in self.SECTION_RULES:
                if rule_heading.lower() in heading.lower():
                    sections[rule_heading] = content
                    break
            else:
                sections[heading] = content
        return sections

    def get_feedback_for_retry(self, section_heading: str, content: str) -> str:
        """
        Gera instrução de retry formatada para injeção no prompt do SectionalGenerator.
        """
        feedbacks = self.check_section_by_type(section_heading, content)
        if not feedbacks:
            return ""
        instruction = "\n⚠️ QUALIDADE INSUFICIENTE. Corrija:\n"
        for fb in feedbacks:
            instruction += f"- {fb}\n"
        return instruction
