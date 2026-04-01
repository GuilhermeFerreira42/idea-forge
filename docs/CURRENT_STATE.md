# CURRENT_STATE — IdeaForge CLI

- [x] **Fase 9.5.1 — Onda 1 Corrigida**: Implementação de 18 passes no Consolidador, injeção de Exemplares Lean (estruturais) e automação total da CLI.
- [x] **Fase 9.5 — Onda 1 de Expansão**: Injeção de exemplares gold-standard e `SectionQualityChecker` (validado e recalibrado na 9.5.1).
- [x] **Fase 10.0 — Orquestração de Debate**: DebateStateTracker rastreando Issues e Resoluções entre rounds.
- [x] **Fase 9.1 — PRD Final Completo (Geração Seccional)**: Transição para orquestração sequencial eliminando truncamento.

## Arquitetura NEXUS v1.4 (Integridade Expandida)
- **Padrão**: Blackboard com Grafo de Artefatos (DAG) de 9 tarefas.
- **Consolidação**: TASK_07 (Consolidador) utiliza **18 passes granulares** com técnica *Skeleton-then-Flesh* para seções críticas.
- **Injeção**: Uso de exemplares curados "Lean" (~400 chars) para guiar o formato sem induzir alucinações de IDs ou dados específicos.
- **Automação**: CLI suporta argumentos `--model` e `--idea`, eliminando interatividade em ambientes de CI/Automação.
- **Fail-Safe**: `MAX_RETRIES_PER_PASS = 3` com bypass de qualidade em passes tipo *Skeleton*.
- **Observabilidade**: Logs estruturados em `.forge/logs/` com relatórios de consistência pós-geração.

## Módulos e Contratos Vigentes
| Módulo | Arquivo | Contrato Público | Versão |
|---|---|---|---|
| Blackboard | `blackboard.py` | `set_variable`, `get_variable`, `snapshot` | F3 |
| ArtifactStore | `artifact_store.py` | `write`, `read`, `get_context_for_agent` | F3 |
| Planner | `planner.py` | `execute_pipeline(user_idea)` | F9 |
| SectionalGenerator | `sectional_generator.py` | `generate_sectional` (18-pass NEXUS) | F9.5.1 |
| QualityChecker | `section_quality_checker.py`| `check_section_by_type` | F9.5 |
| ProductManagerAgent | `product_manager_agent.py` | `consolidate_prd` (18-pass) | F12 |
| ConsistencyChecker| `consistency_checker_agent.py`| `check_consistency` (Audit sem LLM) | F9 |
| DebateStateTracker| `debate_state_tracker.py` | `extract_issues`, `extract_resolutions` | F10 |
| OutputValidator| `output_validator.py`| `validate_pass` (Hard rules: 20 seções) | F9 |
| ModelProvider | `ollama_provider.py` | `generate(prompt, think, max_tokens)` | F7 |

## DAG de Tarefas (NEXUS DAG)
- **TASK_01-06**: Fluxo de geração, crítica, design, segurança e debate.
- **TASK_07**: PM.consolidate_prd [all_artifacts] → prd_final (18 passes).
- **TASK_07b**: ConsistencyChecker.check_consistency [prd_final] → audit_report.

## Invariantes e Quality Gates
1. **Densidade NEXUS**: Meta de 35.000-50.000 caracteres para o PRD Final.
2. **Quality Gate**: Seções críticas (Riscos, RFs, Arquitetura) exigem sub-passes de expansão.
3. **Audit Gate**: O PRD Final deve passar no consistency audit (is_clean=True).
4. **Context Control**: `input_budget` fixo de 3000 chars para máxima precisão no consolidado.

## Testes de Certificação
- **Regressão**: 124 testes unitários e de integração ativos (`pytest tests/`).
- **Orquestração**: `tests/test_phase_9_1.py` valida a estrutura de 18 passes.
- **Resiliência**: `tests/test_retry_logic.py` valida o limite de 3 retries.
