# DECISION_LOG — IdeaForge CLI

## Formato
`[FASE] | [TIPO] | [DECISÃO] | [MOTIVO] | [ARQUIVOS IMPACTADOS]`

Tipos: ADD (novo), MOD (modificado), DEL (removido), FREEZE (congelado), RULE (regra)

---

### Fase 1 — Visibilidade do Pensamento
F1 | ADD | `StreamHandler` | Separar tokens de pensamento do conteúdo final | `stream_handler.py`
F1 | MOD | `OllamaProvider` | Suporte a streaming com retorno estruturado | `ollama_provider.py`
F1 | RULE | Thinking Separation | Evitar poluição de metadados de raciocínio em relatórios | `controller.py`

### Fase 2 — Supressão de Reasoning
F2 | MOD | `OllamaProvider` | Payload options {think: false} explícito | `ollama_provider.py`
F2 | RULE | Direct Directive | Prompt injection para forçar modelos de reasoning a ser direto | `ollama_provider.py`
F2 | ADD | `SilentProgressIndicator` | Prover feedback visual (spinner) quando thinking está oculto | `stream_handler.py`

### Fase 3 — Migração Blackboard
F3 | ADD | `Blackboard` & `ArtifactStore` | Estado global persistente e versionado | `blackboard.py`, `artifact_store.py`
F3 | ADD | `Planner` (DAG) | Orquestração não-linear baseada em dependências | `planner.py`
F3 | RULE | Zero-Knowledge | Agentes recebem contexto via injeção de parâmetros | `planner.py`, `agents/*.py`

### Fase 3.1 — Operação Limpeza
F3.1 | ADD | `prompt_templates.py` | Forçar formatos técnicos (tabelas/bullets) | `prompt_templates.py`
F3.1 | RULE | Density Enforcement | Exigir razão técnica/narrativa alta (Density ≥ 0.85) | `agents/*.py`
F3.1 | MOD | `ArtifactStore` | `usage_hint` para context framing seletivo | `artifact_store.py`

### Fase 4 — Padrão NEXUS
F4 | ADD | `OutputValidator` | Verificação programática de conformidade de seção | `output_validator.py`
F4 | ADD | `SecurityReviewerAgent` | Especialista em análise STRIDE de segurança | `security_reviewer_agent.py`
F4 | MOD | DAG Multi-Task | Expansão para 7 tasks (incluindo security) | `planner.py`
F4 | RULE | Quality Scoring | Atribuição de score numérico (0-100) para artefatos | `output_validator.py`

### Fase 5 — Geração Seccional
F5 | ADD | `SectionalGenerator` | Geração multi-pass para superar limites de tokens | `sectional_generator.py`
F5 | MOD | Agentes Core | Integração de PM e Architect com modo seccional | `product_manager_agent.py`, `architect_agent.py`
F5 | RULE | Sectional Fallback | Garantir continuidade via single-pass se multi-pass falhar | `sectional_generator.py`

### Fase 7 — NEXUS Calibration
F7 | MOD | `OllamaProvider` | num_predict: 2500 (direct) / 5000 (reasoning) | `ollama_provider.py`
F7 | ADD | NEXUS Templates | Tabelas mandatórias em PRD, Design, Plan, Review | `prompt_templates.py`
F7 | MOD | Sectional Passes | Recalibração de passes seccionais para alta densidade | `sectional_generator.py`
F7 | MOD | `OutputValidator` | Thresholds aumentados (PRD 600 chars, completeness 0.75) | `output_validator.py`
F7 | ADD | `--no-gate` | Flag para automação síncrona sem interrupção humana | `main.py`, `controller.py`
F7 | MOD | `AgentController` | Relatório final com Executive Summary e NEXUS Metrics | `controller.py`
F7 | RULE | Technical First | Priorizar tabelas comparativas sobre prosa narrativa | `prompt_templates.py`, `golden_examples.py`

### Fase 7.1 — Consolidação NEXUS + Fix Critic
F7.1 | MOD | `TASK_CONFIGS` | `max_tokens` review 2500, design 2500, run 1500, plan 2500 | `planner.py`
F7.1 | MOD | `CriticAgent` | `artifact_content[:3000]` para análise completa do PRD | `critic_agent.py`
F7.1 | ADD | `NEXUS_CONSOLIDATION_TEMPLATE` | Template de síntese final unificando artefatos | `prompt_templates.py`
F7.1 | ADD | `consolidate_prd()` | Novo método para geração do PRD Final consolidado | `product_manager_agent.py`
F7.1 | ADD | `TASK_07` | Consolidação final como oitava tarefa do pipeline | `planner.py`
F7.1 | MOD | `AgentController` | Retorno de `prd_final` e relatório com PRD no topo | `controller.py`
F7.1 | RULE | Single-Call Consolidation | Forçar síntese em chamada única para máxima coerência final | `product_manager_agent.py`

### Fase 8 — Estabilização e Observabilidade
F8 | ADD | `PipelineLogger` | Rastreamento estruturado em JSONL e arquivamento individual | `pipeline_logger.py`
F8 | MOD | `AgentController` | Integração de fail-safe logging e run-id por execução | `controller.py`
F8 | MOD | `OutputValidator` | Schema `prd_final` com 16 seções NEXUS e 800 chars min | `output_validator.py`
F8 | ADD | `get_artifact_content` | Interface limpa para recuperação de texto de artefatos | `controller.py`
F8 | ADD | Isolated PRD File | Geração de `PRD_FINAL_*.md` na raiz para acesso rápido | `main.py`

### Fase 9 — Integridade do Conteúdo
F9 | ADD | `ConsistencyCheckerAgent` | Auditoria programática (zero-LLM) do PRD Final | `consistency_checker_agent.py`
F9 | MOD | `NEXUS_CONSOLIDATION_TEMPLATE` | Expansão para 20 seções (v1.2) com Rastreabilidade e Cláusulas | `prompt_templates.py`
F9 | MOD | `OutputValidator` | Thresholds aumentados (1000 chars) e novas seções obrigatórias | `output_validator.py`
F9 | MOD | `DebateEngine` | Extração automática de decisões estruturadas para o relatório | `debate_engine.py`
F9 | ADD | `TASK_07b` | Nova task de auditoria na DAG para garantir integridade final | `planner.py`
F9 | RULE | Programmatic Guardrails | Priorizar verificações determinísticas sobre novas chamadas LLM | `consistency_checker_agent.py`

### Fase 10 — Orquestração Inteligente do Debate
F10 | ADD | `DebateStateTracker` | Rastreamento programático de issues (OPEN/ACCEPTED/DEFERRED) entre rodadas | `debate_state_tracker.py`
F10 | MOD | `DebateEngine` | Integração do tracker para injeção de contexto estruturado nos agentes | `debate_engine.py`
F10 | MOD | Agentes (Critic/Proponent) | Expansão de limites de truncamento e novas regras de não-repetição (9-10) | `critic_agent.py`, `proponent_agent.py`
F10 | RULE | State-Driven Debate | Priorizar o tratamento de issues pendentes sobre novas críticas em rodadas avançadas | `debate_engine.py`
