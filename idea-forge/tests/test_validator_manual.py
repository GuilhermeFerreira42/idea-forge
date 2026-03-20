import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.core.output_validator import OutputValidator

v = OutputValidator()

# Teste 1: PRD completo deve passar
prd_bom = """## Objetivo
- Criar API REST

## Problema
| ID | Problema | Impacto | Evidência |
|---|---|---|---|
| P-01 | Sem API | Alto | Dados manuais |

## Requisitos Funcionais
| ID | Requisito | Critério de Aceite | Prioridade | Complexidade |
|---|---|---|---|---|
| RF-01 | CRUD tarefas | POST retorna 201 | Must | Low |

## Requisitos Não-Funcionais
| ID | Categoria | Requisito | Métrica | Target |
|---|---|---|---|---|
| RNF-01 | Performance | Latência | p95 | <200ms |

## Escopo MVP
**Inclui:** RF-01
**NÃO inclui:** Mobile

## Métricas de Sucesso
| Métrica | Target | Prazo |
|---|---|---|

## Dependências e Riscos
| ID | Tipo | Descrição | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|---|
| R-01 | Risco | DB crash | Baixa | Alto | Backup |
"""

r1 = v.validate(prd_bom, "prd")
print(f"PRD bom - valid: {r1['valid']}, completude: {r1['completeness_score']}, density: {r1['density_score']}")

# Teste 2: PRD incompleto deve falhar
prd_ruim = "## Objetivo\n- Criar app\n\nIsso é um parágrafo narrativo sem tabelas."
r2 = v.validate(prd_ruim, "prd")
print(f"PRD ruim - valid: {r2['valid']}, missing: {r2['missing_sections']}")
