# CURRENT_STATE — IdeaForge CLI
> Última atualização: Fase 7.1 (NEXUS Consolidation) | 2026-03-27

## Arquitetura NEXUS v1.0 (Consolidação)
- **Padrão**: Blackboard com Grafo de Artefatos (DAG) de 8 tarefas.
- **Consolidação**: TASK_07 unifica PRD, Design, Security, Debate e Plan em um PRD Final.
- **Calibração**: Limites de contexto expandidos (2500 tokens para review/design) e truncamento de 3000 chars para Agente Crítico.
- **Orquestração**: Planner determinístico com **NEXUS Gate** e aprovação automática via `--no-gate`.

## Módulos e Contratos Vigentes
| Módulo | Arquivo | Contrato Público | Versão |
|---|---|---|---|
| Blackboard | `blackboard.py` | `set_variable`, `get_variable`, `set_task_status`, `snapshot` | F3 |
| ArtifactStore | `artifact_store.py` | `write`, `read`, `get_context_for_agent` | F3 |
| Planner | `planner.py` | `load_default_dag()`, `execute_pipeline(user_idea)` | F7 |
| Controller | `controller.py` | `run_pipeline(idea)`, `_generate_final_report` | F7 |
| OutputValidator| `output_validator.py`| `validate(content, type)`, `validate_pass(content, sections)` | F7 |
| SectionalGen | `sectional_generator.py`| `generate_sectional(artifact_type, context)` | F7 |
| ModelProvider | `ollama_provider.py` | `generate(prompt, think)`, `num_predict` (2500/5000) | F7 |
| Agents | `agents/*.py` | PM, Architect, Critic, Security | F7 |
| Engines | `debate`, `planning` | `DebateEngine.run`, `PlanGenerator.generate_plan` | F7 |

## DAG de Tarefas (NEXUS DAG)
- **TASK_01**: PM.generate_prd [user_idea] → prd
- **TASK_02**: Critic.review_artifact [prd] → prd_review
- **TASK_03**: System.human_gate [prd, prd_review] → approval (Pode ser auto via `--no-gate`)
- **TASK_04**: Architect.design_system [prd, approval] → system_design
- **TASK_04b**: Security.review_security [system_design, prd] → security_review
- **TASK_05**: Debate.run [prd, system_design, security_review] → debate_transcript
- **TASK_06**: PlanGen.generate_plan [prd, system_design, transcript] → development_plan

## Invariantes NEXUS (Quality Gates)
1. **Density Threshold**: Mínimo de 0.75 de densidade semântica (tabelas e listas técnicas).
2. **Min Length**: PRDs exigem 600+ caracteres; Design exige 400+; Reviews 200+.
3. **Completeness**: Threshold de 75% para PRDs (exige 8+ de 11 seções mandatórias).
4. **Zero-Knowledge**: Agentes isolados; contexto injetado via ArtifactStore.
5. **No-Gate Logic**: Quando `--no-gate` ativa, aprovações são automáticas (`APPROVED`).

## Configurações de Inferência
- **Tokens**: `num_predict: 2500` (Direct) / `5000` (Reasoning).
- **Temperatura**: `0.1` para consistência técnica.
- **Seccional**: 5 passes para PRD, 2 para Review, 2 para Design, 2 para Plan.

## Testes de Certificação
- **Unitários**: `test_planner.py`, `test_agents.py`, `test_debate.py`, `test_blackboard.py`.
- **Validação**: `test_output_validator_v2.py`, `test_retry_logic.py`.
- **E2E Integration**: `test_pipeline.py` (Mocked NEXUS pipeline).
- **ANSI/Stream**: `test_stream_handler.py`.
