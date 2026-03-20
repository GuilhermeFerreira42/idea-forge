# CURRENT_STATE — IdeaForge CLI
> Última atualização: Fase 5 | 2026-03-20

## Arquitetura Ativa
- **Padrão**: Blackboard com Grafo de Artefatos (DAG).
- **Orquestração**: Planner determinístico via `execute_pipeline`.
- **Estado**: Persistência reativa em `.forge/` (JSON).
- **Inference**: Ollama (Local) com suporte a Reasoning Suppression e Sectional Generation (Multi-pass).
- **Streaming**: StreamHandler com separação de Thinking/Content e Progressive Spinner.

## Módulos e Contratos Vigentes
| Módulo | Arquivo | Contrato Público | Desde |
|---|---|---|---|
| Blackboard | `blackboard.py` | `set_variable`, `get_variable`, `set_task_status`, `snapshot` | F3 |
| ArtifactStore | `artifact_store.py` | `write(name, content, type)`, `read(name, version)`, `get_context_for_agent` | F3 |
| Planner | `planner.py` | `load_default_dag()`, `execute_pipeline(user_idea)` | F4 |
| Controller | `controller.py` | `run_pipeline(initial_idea)` | F1 |
| StreamHandler | `stream_handler.py` | `process_ollama_stream(iterator) -> StreamResult` | F1 |
| OutputValidator| `output_validator.py`| `validate(content, type) -> dict` (valid, score, density) | F4 |
| SectionalGen | `sectional_generator.py`| `generate_sectional(artifact_type, context) -> str` | F5 |
| ModelProvider | `model_provider.py` | `generate(prompt, **kwargs) -> str`, `generate_with_thinking` | F1 |
| OllamaProvider | `ollama_provider.py` | `generate(prompt, max_tokens, think) -> str` | F1 |
| PM Agent | `product_manager_agent.py`| `generate_prd(idea, context) -> str` | F3 |
| Architect Agent| `architect_agent.py` | `design_system(prd, context) -> str` | F3 |
| Critic Agent | `critic_agent.py` | `review_artifact(content, type) -> str` | F1 |
| Security Agent | `security_reviewer_agent.py`| `review_security(system_design, prd) -> str` | F4 |
| Debate Engine | `debate_engine.py` | `run(refined_idea) -> transcript` | F1 |
| Plan Generator | `plan_generator.py` | `generate_plan(input, context) -> str` | F3 |

## DAG de Tarefas Padrão
- TASK_01: PM.generate_prd [user_idea] → prd (requires: [])
- TASK_02: Critic.review_artifact [prd] → prd_review (requires: T01)
- TASK_03: System.human_gate [prd, prd_review] → approval (requires: T02)
- TASK_04: Architect.design_system [prd, approval] → system_design (requires: T03)
- TASK_04b: Security.review_security [system_design, prd] → security_review (requires: T04)
- TASK_05: Debate.run [prd, system_design, security_review] → debate_transcript (requires: T04b)
- TASK_06: PlanGen.generate_plan [prd, system_design, transcript] → development_plan (requires: T05)

## Invariantes Globais (nunca violar)
1. **Zero-Knowledge Primary**: Agente nunca lê o Blackboard diretamente, apenas via parâmetros injetados.
2. **Offline-First**: Nenhuma dependência de APIs externas (apenas Ollama local + requests).
3. **Artifact Immutability**: Uma vez escrito, um artefato (versão X) nunca é alterado; cria-se versão X+1.
4. **Thinking Separation**: Tokens de raciocínio nunca poluem o artefato final (`content`).
5. **Schema Enforcement**: Todo output deve passar pelo `OutputValidator` com density ≥ 0.6.
6. **Portuguese Output**: 100% da interação e artefatos devem ser em Português.
7. **Context Budgeting**: Injeção de contexto limitada a 1500 tokens por task.
8. **Semantic Compression**: Formatos tabulares/bullets preferidos sobre prosa narrativa.

## Restrições Técnicas Ativas
- **Inference**: `temperature=0.1` (direct), `temperature=0.7` (thinking), `num_predict=1200`.
- **Modo Direto**: Injeção de `DIRECT_RESPONSE_DIRECTIVE` e `think=false` no Ollama.
- **Sectional**: Geração em múltiplos passes (4 seções por artefato core).
- **Post-processing**: Regex para remoção de preâmbulos ("Certamente", "Aqui está").

## Testes Obrigatórios
- `tests/test_stream_handler.py` (Streaming & Parser)
- `tests/test_blackboard.py` (Estado)
- `tests/test_planner.py` (DAG & Execution)
- `tests/test_new_agents.py` (PM & Architect)
- `tests/test_sectional_mock.py` (Sectional logic)
