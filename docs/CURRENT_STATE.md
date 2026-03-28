# CURRENT_STATE — IdeaForge CLI
> Última atualização: Fase 9.0 (Integridade do Conteúdo) | 2026-03-28

## Arquitetura NEXUS v1.2 (Integridade)
- **Padrão**: Blackboard com Grafo de Artefatos (DAG) de 9 tarefas (incluindo TASK_07b).
- **Consolidação**: TASK_07 unifica todos os artefatos em um **PRD Final** (NEXUS 20-seções).
- **Auditoria**: `ConsistencyCheckerAgent` realiza verificação programática (zero-LLM) pós-consolidação.
- **Observabilidade**: Logs estruturados em `.forge/logs/` e relatórios de consistência embutidos no output final.
- **Fail-Safe**: Detecção automática de seções vazias ou requisitos "fantasmas" (RF-XX órfãos).

## Módulos e Contratos Vigentes
| Módulo | Arquivo | Contrato Público | Versão |
|---|---|---|---|
| Blackboard | `blackboard.py` | `set_variable`, `get_variable`, `set_task_status`, `snapshot` | F3 |
| ArtifactStore | `artifact_store.py` | `write`, `read`, `get_context_for_agent` | F3 |
| Planner | `planner.py` | `load_default_dag()`, `execute_pipeline(user_idea)` | F9 |
| Controller | `controller.py` | `run_pipeline(idea)`, `get_artifact_content(name)` | F9 |
| ConsistencyChecker| `consistency_checker_agent.py`| `check_consistency(prd_final)` (sem LLM) | F9 |
| PipelineLogger | `pipeline_logger.py`| `log(task, type)`, `save_artifact(name, content)` | F8 |
| OutputValidator| `output_validator.py`| `validate(content, type)` (NEXUS v1.2: 20 seções, 1000 chars) | F9 |
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
1. **PRD Final NEXUS v1.2**: Exige 20 seções obrigatórias e mínimo de 1000 caracteres.
2. **Audit Check**: O PRD Final deve passar no consistency audit (is_clean=True) ou disparar alertas críticos.
3. **Decisões Estruturadas**: O DebateEngine extrai automaticamente pontos consensuais para o relatório final.
4. **Log Immersion**: Toda execução gera uma run-id única com artifacts e pipeline.jsonl.

## Testes de Certificação
- **Certificação**: 55+ testes unitários e de integração ativos.
- **Consistência**: `tests/test_phase_9_consistency.py` (valida auditoria programática).
- **Validação**: `test_output_validator_v2.py` (cobre schema NEXUS v1.2).
