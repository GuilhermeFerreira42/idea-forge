# CURRENT_STATE — IdeaForge CLI
> Última atualização: Fase 5.1 | 2026-03-20

## Arquitetura Ativa
- **Padrão**: Blackboard com Grafo de Artefatos (DAG).
- **Orquestração**: Planner determinístico com **Hard Gate** (validação bloqueante).
- **Estado**: Persistência reativa em `.forge/` (JSON).
- **Inference**: Ollama (Local) com Reasoning Suppression e Geração Seccional (Multi-pass).
- **Robustez**: Lógica de **Retry por Pass** (até 2 tentativas) com prompts corretivos.

## Módulos e Contratos Vigentes
| Módulo | Arquivo | Contrato Público | Desde |
|---|---|---|---|
| Blackboard | `blackboard.py` | `set_variable`, `get_variable`, `set_task_status`, `snapshot` | F3 |
| ArtifactStore | `artifact_store.py` | `write(name, content, type)`, `read(name, version)`, `get_context_for_agent` | F3 |
| Planner | `planner.py` | `load_default_dag()`, `execute_pipeline(user_idea)` | F4 |
| Controller | `controller.py` | `run_pipeline(initial_idea)` | F1 |
| StreamHandler | `stream_handler.py` | `process_ollama_stream(iterator) -> StreamResult` | F1 |
| OutputValidator| `output_validator.py`| `validate(content, type)`, `validate_pass(content, sections)` | F5.1 |
| SectionalGen | `sectional_generator.py`| `generate_sectional(artifact_type, context) -> str` | F5 |
| ModelProvider | `model_provider.py` | `generate(prompt, **kwargs) -> str`, `generate_with_thinking` | F1 |
| OllamaProvider | `ollama_provider.py` | `generate(prompt, max_tokens, think) -> str` | F1 |
| PM Agent | `product_manager_agent.py`| `generate_prd(idea, context) -> str` | F5.1 |
| Architect Agent| `architect_agent.py` | `design_system(prd, context) -> str` | F5.1 |
| Critic Agent | `critic_agent.py` | `review_artifact(content, type) -> str` | F5.1 |
| Security Agent | `security_reviewer_agent.py`| `review_security(system_design, prd) -> str` | F5.1 |
| Debate Engine | `debate_engine.py` | `run(refined_idea) -> transcript` | F1 |
| Plan Generator | `plan_generator.py` | `generate_plan(input, context) -> str` | F5.1 |

## DAG de Tarefas Padrão
- TASK_01: PM.generate_prd [user_idea] → prd (requires: [])
- TASK_02: Critic.review_artifact [prd] → prd_review (requires: T01)
- TASK_03: System.human_gate [prd, prd_review] → approval (requires: T02)
- TASK_04: Architect.design_system [prd, approval] → system_design (requires: T03)
- TASK_04b: Security.review_security [system_design, prd] → security_review (requires: T04)
- TASK_05: Debate.run [prd, system_design, security_review] → debate_transcript (requires: T04b)
- TASK_06: PlanGen.generate_plan [prd, system_design, transcript] → development_plan (requires: T05)

## Invariantes Globais (Muro de Arrimo)
1. **Hard Gate Enforcement**: Artefatos sem seções obrigatórias ou vazios são BLOQUEADOS (`[GERAÇÃO FALHOU]`).
2. **Zero-Knowledge Primary**: Agente nunca lê o Blackboard diretamente, apenas via parâmetros injetados.
3. **Artifact Immutability**: Uma vez escrito, um artefato (versão X) nunca é alterado; cria-se versão X+1.
4. **Thinking Separation**: Tokens de raciocínio nunca poluem o artefato final (`content`).
5. **Portuguese Output**: 100% da interação e artefatos devem ser em Português.
6. **Semantic Compression**: Formatos tabulares/bullets preferidos (Density ≥ 0.7).
7. **Pass-level Retry**: Seções individuais de artefatos core têm até 2 retries automáticos em caso de falha.

## Restrições Técnicas Ativas
- **Inference**: `temperature=0.1` (direct), `num_predict=1500`.
- **Modo Direto**: Injeção de `DIRECT_MODE_SUFFIX` e `think=false` no Ollama.
- **Sectional**: Geração em múltiplos passes (2-4 seções por artefato core).
- **Validation**: Schema enforcement agressivo via `OutputValidator`.

## Testes de Regressão
- `tests/test_stream_handler.py` (Streaming & Parser)
- `tests/test_planner.py` (DAG & Execution Flow)
- `tests/test_output_validator_v2.py` (Hard Gate & Placeholder Detection)
- `tests/test_retry_logic.py` (Sectional Retry Mechanism)
