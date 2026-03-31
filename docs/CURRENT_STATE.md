# CURRENT_STATE — IdeaForge CLI

- [x] **Fase 9.5 — Onda 1 de Expansão**: Injeção de exemplares gold-standard, metas de densidade agressivas (40k-50k chars) e `SectionQualityChecker` programático integrado ao loop de retry.
- [x] **Fase 9.4 — Calibração de Passes Fracos + Fix RF_ORPHAN**: Ajuste fino de `min_chars` (até 900) para expansão do PRD Final (>15k chars) e correção do template do Pass 8 removendo as referências fantasmas de checkout/marketplace.
- [x] **Fase 9.3 — Calibração de Profundidade**: PRD Final recalibrado para 12 passes com exemplos ricos, `max_output_tokens` ampliado para 2500 e prosa técnica explícita.
- [x] **Fase 9.1.1 — Enriquecimento do PRD Final**: Calibração de `input_budget` (3000), detecção de markers de falha `[GERAÇÃO FALHOU]` e exemplos v1.1 de alta profundidade no consolidado.
- [x] **Fase 10.0 — Orquestração de Debate**: DebateStateTracker implementado, rastreando Issues e Resoluções entre rounds.
- [x] **Fase 9.1 — PRD Final Completo (Geração Seccional)**: Transição para 5 passes dedicados no NEXUS Protocol v1.2, eliminando truncamento e elevando threshold de completude para 90%.

## Arquitetura NEXUS v1.3 (Integridade)
- **Padrão**: Blackboard com Grafo de Artefatos (DAG) de 9 tarefas (incluindo TASK_07b).
- **Consolidação**: TASK_07 unifica todos os artefatos em um **PRD Final** via **12 passes granulares** (NEXUS 20-seções).
- **Injeção**: Uso de 12 exemplares curados (OmniPrice gold-standard) para ensinar o nível de detalhe ao modelo por seção.
- **Auditoria de Qualidade**: `SectionQualityChecker` realiza verificação programática de densidade, itens e palavras-chave antes da aceitação de cada seção.
- **Observabilidade**: Logs estruturados em `.forge/logs/` e relatórios de consistência embutidos no output final.
- **Fail-Safe**: Loop de retry acionado automaticamente se uma seção for considerada rasa ou estruturalmente inválida.

## Módulos e Contratos Vigentes
| Módulo | Arquivo | Contrato Público | Versão |
|---|---|---|---|
| Blackboard | `blackboard.py` | `set_variable`, `get_variable`, `set_task_status`, `snapshot` | F3 |
| ArtifactStore | `artifact_store.py` | `write`, `read`, `get_context_for_agent` | F3 |
| Planner | `planner.py` | `load_default_dag()`, `execute_pipeline(user_idea)` | F9 |
| Controller | `controller.py` | `run_pipeline(idea)`, `get_artifact_content(name)` | F9 |
| SectionalGenerator | `sectional_generator.py` | `_execute_pass_with_retry`, `_check_section_quality` | F9.5 |
| QualityChecker | `section_quality_checker.py`| `check_all_sections(prd)`, `check_section_by_type` | F9.5 |
| ProductManagerAgent | `product_manager_agent.py` | `consolidate_prd(artifacts_context)` (12-pass) | F12 |
| ConsistencyChecker| `consistency_checker_agent.py`| `check_consistency(prd_final)` (sem LLM) | F9 |
| DebateStateTracker| `debate_state_tracker.py` | `extract_issues`, `extract_resolutions` (sem LLM) | F10 |
| PipelineLogger | `pipeline_logger.py`| `log(task, type)`, `save_artifact(name, content)` | F8 |
| OutputValidator| `output_validator.py`| `validate(content, type)` (NEXUS v1.2: 20 seções) | F9 |
| ModelProvider | `ollama_provider.py` | `generate(prompt, think)`, `num_predict` (2500/5000) | F7 |

## DAG de Tarefas (NEXUS DAG Expandida)
- **TASK_01**: PM.generate_prd [user_idea] → prd
- **TASK_02**: Critic.review_artifact [prd] → prd_review
- **TASK_03**: System.human_gate [prd, prd_review] → approval (Auto via `--no-gate`)
- **TASK_04**: Architect.design_system [prd, approval] → system_design
- **TASK_04b**: Security.review_security [system_design, prd] → security_review
- **TASK_05**: Debate.run [prd, system_design, security_review] → debate_transcript
- **TASK_06**: PlanGen.generate_plan [prd, system_design, transcript] → development_plan
- **TASK_07**: PM.consolidate_prd [all_artifacts] → prd_final (NEXUS 20-seções)
- **TASK_07b**: ConsistencyChecker.check_consistency [prd_final] → consistency_report (FASE 9.0)

## Invariantes e Quality Gates
1. **PRD Final NEXUS v1.3**: Exige 20 seções obrigatórias e densidade alvo de 40.000-50.000 caracteres.
2. **Quality Check**: Cada seção passa por auditoria programática de `min_chars`, `min_items` e `required_keywords`.
3. **Audit Check**: O PRD Final deve passar no consistency audit (is_clean=True) ou disparar alertas críticos.
4. **Referência Ouro**: Exemplares injetados garantem que o modelo produza impacto mensurável e soluções técnicas concretas.

## Testes de Certificação
- **Certificação**: 125 testes unitários e de integração ativos.
- **Qualidade**: `tests/test_quality_checker.py` (valida auditoria por seção).
- **Consistência**: `tests/test_phase_9_consistency.py` (valida auditoria pós-consolidação).
- **Estrutura**: `tests/test_phase_9_1.py` (valida os 12 passes e referências ouro).
