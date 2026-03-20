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

### Fase 5.1 — Hard Gate + Retry por Pass
F5.1 | ADD | Hard Gate | Bloquear artefatos vazios ou curtos no Planner | `planner.py`
F5.1 | MOD | Retry Mechanism | Implementar 2 retries por pass com prompt corretivo | `sectional_generator.py`
F5.1 | MOD | Placeholder Detection | Rejeitar outputs com excesso de "A DEFINIR" | `output_validator.py`
F5.1 | ADD | Unit Tests v2 | Testes de validação e retry para garantir robustez | `tests/test_output_validator_v2.py`, `tests/test_retry_logic.py`
F5.1 | RULE | Corrective Prompting | Injetar motivos de falha no retry para guiar o modelo | `sectional_generator.py`
