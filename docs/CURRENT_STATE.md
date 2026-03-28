# CURRENT_STATE — IdeaForge CLI
> Última atualização: Fase 8.0 (Estabilização e Observabilidade) | 2026-03-28

## Arquitetura NEXUS v1.1 (Observabilidade)
- **Padrão**: Blackboard com Grafo de Artefatos (DAG) de 8 tarefas.
- **Consolidação**: TASK_07 unifica todos os artefatos em um **PRD Final** (NEXUS 16-seções).
- **Observabilidade**: Sistema de logs estruturados (JSONL) em `.forge/logs/` via `PipelineLogger`.
- **Persistência**: Geração automática de `PRD_FINAL_{timestamp}.md` na raiz e sumário de execução.
- **Fail-Safe**: Invariante de logging não-bloqueante (falha no I/O de log não para o pipeline).

## Módulos e Contratos Vigentes
| Módulo | Arquivo | Contrato Público | Versão |
|---|---|---|---|
| Blackboard | `blackboard.py` | `set_variable`, `get_variable`, `set_task_status`, `snapshot` | F3 |
| ArtifactStore | `artifact_store.py` | `write`, `read`, `get_context_for_agent` | F3 |
| Planner | `planner.py` | `load_default_dag()`, `execute_pipeline(user_idea)` | F8 |
| Controller | `controller.py` | `run_pipeline(idea)`, `get_artifact_content(name)` | F8 |
| PipelineLogger | `pipeline_logger.py`| `log(task, type)`, `save_artifact(name, content)` | F8 |
| OutputValidator| `output_validator.py`| `validate(content, type)` (inclui `prd_final`) | F8 |
| SectionalGen | `sectional_generator.py`| `generate_sectional(artifact_type, context)` | F7 |
| ModelProvider | `ollama_provider.py` | `generate(prompt, think)`, `num_predict` (2500/5000) | F7 |
| Agents | `agents/*.py` | PM, Architect, Critic, Security | F7.1 |

## DAG de Tarefas (NEXUS DAG)
- **TASK_01**: PM.generate_prd [user_idea] → prd
- **TASK_02**: Critic.review_artifact [prd] → prd_review
- **TASK_03**: System.human_gate [prd, prd_review] → approval (Auto via `--no-gate`)
- **TASK_04**: Architect.design_system [prd, approval] → system_design
- **TASK_04b**: Security.review_security [system_design, prd] → security_review
- **TASK_05**: Debate.run [prd, system_design, security_review] → debate_transcript
- **TASK_06**: PlanGen.generate_plan [prd, system_design, transcript] → development_plan
- **TASK_07**: PM.consolidate_prd [all_artifacts] → prd_final (NEXUS 16-seções)

## Invariantes e Quality Gates
1. **PRD Final NEXUS**: Exige 16 seções obrigatórias e mínimo de 800 caracteres.
2. **Density Threshold**: Mínimo de 0.70 de densidade semântica para o consolidado.
3. **Draft Completeness**: PRDs iniciais exigem 75% (8/11 seções), Consolidado exige 70% (12/16 seções).
4. **Log Immersion**: Toda execução gera uma run-id única com artifacts e pipeline.jsonl.
5. **No-Gate Automation**: `--no-gate` garante fluxo assíncrono total e persiste PRD Final isolado.

## Configurações de Inferência
- **Tokens**: `num_predict: 2500` (Direct) / `5000` (Reasoning).
- **Temperatura**: `0.1` para consistência técnica.
- **Contexto**: Budget de 3000 tokens para Agente Crítico e Consolidação.

## Testes de Certificação
- **Certificação**: 50+ testes unitários e de integração ativos.
- **Validação**: `test_output_validator_v2.py` (cobre novos schemas NEXUS).
- **Planner/Logs**: `test_planner.py` (valida mapeamento de tipos e logging).
