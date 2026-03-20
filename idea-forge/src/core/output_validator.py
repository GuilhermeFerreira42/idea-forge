"""
output_validator.py — Validador de conformidade de artefatos gerados.

FASE 5.1:
- Adicionado validate_pass() para validação individual de passes
- Adicionado is_placeholder() para detectar outputs "A DEFINIR" em massa
- Adicionado min_chars por tipo de artefato
- Thresholds configuráveis por artifact_type
"""
import re
from typing import Dict, List


class OutputValidator:
    """Valida conformidade de artefatos contra templates esperados."""

    REQUIRED_SECTIONS = {
        "prd": [
            "## Objetivo",
            "## Problema",
            "## Requisitos Funcionais",
            "## Requisitos Não-Funcionais",
            "## Escopo MVP",
            "## Métricas de Sucesso",
            "## Dependências e Riscos",
        ],
        "system_design": [
            "## Arquitetura Geral",
            "## Tech Stack",
            "## Módulos",
            "## Modelo de Dados",
            "## Fluxo de Dados",
            "## ADRs",
            "## Riscos Técnicos",
        ],
        "review": [
            "## Score de Qualidade",
            "## Issues Identificadas",
            "## Verificação de Requisitos",
            "## Sumário",
            "## Recomendação",
        ],
        "security_review": [
            "## Superfície de Ataque",
            "## Ameaças Identificadas",
            "## Requisitos de Segurança Derivados",
            "## Dados Sensíveis",
        ],
        "plan": [
            "## Arquitetura Sugerida",
            "## Módulos Core",
            "## Fases de Implementação",
            "## Riscos e Mitigações",
        ],
    }

    # FASE 5.1: Thresholds mínimos por tipo de artefato
    MIN_CHARS = {
        "prd": 400,
        "system_design": 400,
        "review": 200,
        "security_review": 200,
        "plan": 300,
    }

    # FASE 5.1: Completude mínima para aprovar (0.0 - 1.0)
    MIN_COMPLETENESS = {
        "prd": 0.70,
        "system_design": 0.70,
        "review": 0.60,
        "security_review": 0.50,
        "plan": 0.70,
    }

    def validate(self, content: str, artifact_type: str) -> Dict:
        """Valida artefato completo contra seções obrigatórias."""
        required = self.REQUIRED_SECTIONS.get(artifact_type, [])
        present = []
        missing = []

        if not required:
            return {"valid": True, "note": "No validation rules for this type"}

        if not content or not content.strip():
            return {
                "valid": False,
                "missing_sections": required,
                "present_sections": [],
                "completeness_score": 0.0,
                "density_score": 0.0,
                "has_tables": False,
                "table_count": 0,
                "fail_reasons": ["EMPTY_CONTENT"],
            }

        for section in required:
            pattern = re.compile(re.escape(section), re.IGNORECASE)
            if pattern.search(content):
                present.append(section)
            else:
                missing.append(section)

        completeness = len(present) / len(required)
        density = self._calculate_density(content)
        table_count = content.count("|---|")
        min_chars = self.MIN_CHARS.get(artifact_type, 200)
        min_completeness = self.MIN_COMPLETENESS.get(artifact_type, 0.60)

        # FASE 5.1: Múltiplas condições de falha
        fail_reasons = []
        if len(content.strip()) < min_chars:
            fail_reasons.append(f"TOO_SHORT ({len(content.strip())} < {min_chars})")
        if completeness < min_completeness:
            fail_reasons.append(f"INCOMPLETE ({completeness:.0%} < {min_completeness:.0%})")
        if self.is_placeholder_heavy(content):
            fail_reasons.append("PLACEHOLDER_HEAVY (>50% A DEFINIR)")

        is_valid = len(fail_reasons) == 0

        return {
            "valid": is_valid,
            "missing_sections": missing,
            "present_sections": present,
            "completeness_score": round(completeness, 2),
            "density_score": round(density, 2),
            "has_tables": table_count > 0,
            "table_count": table_count,
            "fail_reasons": fail_reasons,
        }

    def validate_pass(self, content: str, expected_sections: List[str],
                      require_table: bool = True,
                      min_chars: int = 80) -> Dict:
        """
        FASE 5.1: Valida um pass individual da geração seccional.

        Args:
            content: Output do pass
            expected_sections: Lista de headings ## esperados
            require_table: Se True, exige pelo menos 1 tabela (|---|)
            min_chars: Tamanho mínimo do output

        Returns:
            {
                "valid": bool,
                "missing_sections": list,
                "has_table": bool,
                "char_count": int,
                "is_placeholder": bool,
                "fail_reasons": list
            }
        """
        fail_reasons = []

        # Check 1: conteúdo vazio ou muito curto
        if not content or len(content.strip()) < min_chars:
            return {
                "valid": False,
                "missing_sections": expected_sections,
                "has_table": False,
                "char_count": len(content.strip()) if content else 0,
                "is_placeholder": False,
                "fail_reasons": [f"TOO_SHORT ({len(content.strip()) if content else 0} < {min_chars})"],
            }

        # Check 2: seções esperadas presentes
        missing = []
        for section in expected_sections:
            pattern = re.compile(re.escape(section), re.IGNORECASE)
            if not pattern.search(content):
                missing.append(section)

        if missing:
            fail_reasons.append(f"MISSING_SECTIONS: {missing}")

        # Check 3: tabela obrigatória
        has_table = "|---|" in content
        if require_table and not has_table:
            fail_reasons.append("NO_TABLE")

        # Check 4: placeholders excessivos
        is_placeholder = self.is_placeholder_heavy(content)
        if is_placeholder:
            fail_reasons.append("PLACEHOLDER_HEAVY")

        return {
            "valid": len(fail_reasons) == 0,
            "missing_sections": missing,
            "has_table": has_table,
            "char_count": len(content.strip()),
            "is_placeholder": is_placeholder,
            "fail_reasons": fail_reasons,
        }

    def is_placeholder_heavy(self, content: str) -> bool:
        """
        FASE 5.1: Detecta se o output é majoritariamente placeholders.

        Retorna True se mais de 50% das linhas de tabela contêm
        'A DEFINIR', '...', ou células vazias.
        """
        if not content:
            return True

        lines = content.split('\n')
        table_lines = [l for l in lines if l.strip().startswith('|')
                       and '---|' not in l]

        if len(table_lines) >= 2:
            placeholder_count = 0
            for line in table_lines:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if not cells:
                    continue
                placeholder_cells = sum(
                    1 for c in cells
                    if c in ('...', 'A DEFINIR', '', '-')
                    or c.startswith('...')
                )
                if placeholder_cells >= len(cells) / 2:
                    placeholder_count += 1

            if placeholder_count >= len(table_lines) / 2:
                return True

        # Check in bullets/text
        placeholders = ['A DEFINIR', '[...]', '...', '...]']
        lines_with_placeholder = sum(1 for l in lines if any(p in l for p in placeholders))
        if lines_with_placeholder >= len(lines) / 2 and len(lines) > 2:
            return True

        return False

    def _calculate_density(self, content: str) -> float:
        """Calcula razão linhas técnicas / total linhas."""
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        if not lines:
            return 0.0
        technical = 0
        for line in lines:
            if (line.startswith('|') or
                line.startswith('-') or
                line.startswith('##') or
                line.startswith('```') or
                line.startswith('**') or
                (len(line) > 1 and line[0].isdigit() and line[1] in '.)')):
                technical += 1
        return technical / len(lines)
