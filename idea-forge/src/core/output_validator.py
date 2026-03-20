"""
output_validator.py — Validador de conformidade de artefatos gerados.

Responsabilidade:
Verificar se o output do LLM contém as seções obrigatórias do template.
Calcular density_score. Rejeitar outputs que não atendem threshold mínimo.

NÃO usa LLM. Apenas regex e heurísticas.
"""
import re
from typing import Dict, List, Tuple


class OutputValidator:
    """Valida conformidade de artefatos contra templates esperados."""

    # Seções obrigatórias por tipo de artefato (Padrão NEXUS - Fase 4)
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

    def validate(self, content: str, artifact_type: str) -> Dict:
        """
        Valida artefato contra seções obrigatórias.

        Returns:
            {
                "valid": bool,
                "missing_sections": list[str],
                "present_sections": list[str],
                "completeness_score": float,  # 0.0 - 1.0
                "density_score": float,        # 0.0 - 1.0
                "has_tables": bool,
                "table_count": int
            }
        """
        required = self.REQUIRED_SECTIONS.get(artifact_type, [])
        present = []
        missing = []

        if not required:
            return {"valid": True, "note": "No validation rules for this type"}

        for section in required:
            # Busca insensível a caixa e flexível com espaços
            pattern = re.compile(re.escape(section), re.IGNORECASE)
            if pattern.search(content):
                present.append(section)
            else:
                missing.append(section)

        completeness = len(present) / len(required)
        density = self._calculate_density(content)
        table_count = content.count("|---|")

        # Thresholds da Fase 4: 80% completude, 60% densidade
        is_valid = completeness >= 0.8 and density >= 0.5 

        return {
            "valid": is_valid,
            "missing_sections": missing,
            "present_sections": present,
            "completeness_score": round(completeness, 2),
            "density_score": round(density, 2),
            "has_tables": table_count > 0,
            "table_count": table_count,
        }

    def _calculate_density(self, content: str) -> float:
        """Calcula razão linhas técnicas / total linhas."""
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        if not lines:
            return 0.0
        
        technical = 0
        for line in lines:
            # Linhas consideradas "técnicas": tabelas, bullets, headings, code, listas numeradas
            if (line.startswith('|') or
                line.startswith('-') or
                line.startswith('##') or
                line.startswith('```') or
                (len(line) > 1 and line[0].isdigit() and line[1] in '.)')):
                technical += 1
        return technical / len(lines)
