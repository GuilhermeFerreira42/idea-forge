# Blueprint Técnico — Fase 8.0: Estabilização e Observabilidade

**Versão:** 1.0
**Fase:** 8.0 (dividida em 8.0a + 8.0b)
**Baseline:** Fase 7.1 (NEXUS Consolidation)
**Autor:** Arquiteto de Software Sênior — IdeaForge CLI

---

## 1. OVERVIEW

### Objetivo Mensurável

Tornar o PRD Final um produto entregável isolado com validação específica e dar visibilidade total ao pipeline via logs estruturados, sem alterar a DAG nem os contratos públicos dos agentes.

### Matriz de Rastreabilidade Falha → Sub-fase

| Falha ID | Descrição | Sub-fase | Prioridade |
|---|---|---|---|
| F-01 | PRD Final embutido no relatório geral, sem arquivo separado | **8.0a** | P0 |
| F-02 | `prd_final` validado como tipo `prd` genérico (11 seções) em vez de tipo dedicado (16 seções) | **8.0a** | P0 |
| F-03 | Ausência de logs estruturados — todo output vai para `sys.stdout` com ANSI | **8.0b** | P0 |
| F-04 | Template `NEXUS_CONSOLIDATION_TEMPLATE` desatualizado | **Fase 9.0** | Fora de escopo |
| F-05 | Debate sem rastreamento de estado | **Fase 10.0** | Fora de escopo |

### Critérios de Aceite Binários

| ID | Critério | Sub-fase | Verificação |
|---|---|---|---|
| AC-01 | Execução com `--no-gate` gera arquivo `PRD_FINAL_{timestamp}.md` no diretório raiz | 8.0a | `os.path.exists(prd_final_filename)` |
| AC-02 | Conteúdo do arquivo `PRD_FINAL_*.md` é idêntico a `artifact_store.read("prd_final").content` | 8.0a | Comparação string |
| AC-03 | `OutputValidator.validate(content, "prd_final")` retorna `valid=False` se faltar `## Visão do Produto` | 8.0a | Teste unitário |
| AC-04 | Mapeamento `_get_artifact_tag_for_validator` retorna `"prd_final"` para artefato `prd_final` (não `"prd"`) | 8.0a | Teste unitário |
| AC-05 | Diretório `.forge/logs/{run_id}/` é criado durante execução | 8.0b | `os.path.isdir()` |
| AC-06 | Arquivo `pipeline.jsonl` contém pelo menos 1 evento `TASK_START` e 1 evento `TASK_END` por task executada | 8.0b | Parse do JSONL |
| AC-07 | Cada artefato é salvo individualmente em `.forge/logs/{run_id}/artifacts/{name}.md` | 8.0b | `os.path.exists()` |
| AC-08 | Se `PipelineLogger` falhar na inicialização, o pipeline executa normalmente e gera PRD Final | 8.0b | Teste com mock de falha de I/O |
| AC-09 | Todos os 48+ testes existentes continuam passando sem modificação | Ambas | `pytest` exit code 0 |

### Invariante de Segurança (Fail-Safe)

```
SE logger == None OU logger.log() lança exceção:
    → Pipeline continua operando normalmente
    → PRD Final continua sendo salvo (8.0a funciona independente de 8.0b)
    → Nenhum artefato é perdido
```

---

## 2. ARCHITECTURE

### Diagrama de Fluxo — Fase 8.0

```mermaid
flowchart TD
    subgraph "Pipeline Existente (Inalterado)"
        T01[TASK_01: PM.generate_prd]
        T02[TASK_02: Critic.review_artifact]
        T03[TASK_03: System.human_gate]
        T04[TASK_04: Architect.design_system]
        T04b[TASK_04b: Security.review_security]
        T05[TASK_05: Debate.run]
        T06[TASK_06: PlanGen.generate_plan]
        T07[TASK_07: PM.consolidate_prd]
    end

    subgraph "8.0a — PRD Final Isolado"
        SAVE_PRD[main.py: Salvar PRD_FINAL_{ts}.md]
        VALIDATE[OutputValidator: tipo prd_final com 16 seções]
        MAPPING[planner.py: prd_final → prd_final não prd]
    end

    subgraph "8.0b — PipelineLogger"
        LOGGER[PipelineLogger]
        JSONL[pipeline.jsonl]
        ARTS[artifacts/*.md]
        SUMMARY[pipeline_summary.md]
    end

    T01 --> T02 --> T03 --> T04 --> T04b --> T05 --> T06 --> T07

    T07 -->|"artefato prd_final"| SAVE_PRD
    T07 -->|"validação"| VALIDATE
    VALIDATE ---|"mapeamento corrigido"| MAPPING

    T01 -.->|"log TASK_START/END"| LOGGER
    T02 -.->|"log TASK_START/END"| LOGGER
    T03 -.->|"log TASK_START/END"| LOGGER
    T04 -.->|"log TASK_START/END"| LOGGER
    T04b -.->|"log TASK_START/END"| LOGGER
    T05 -.->|"log TASK_START/END"| LOGGER
    T06 -.->|"log TASK_START/END"| LOGGER
    T07 -.->|"log TASK_START/END"| LOGGER

    LOGGER --> JSONL
    LOGGER --> ARTS
    LOGGER --> SUMMARY

    style SAVE_PRD fill:#2d6a2e,color:#fff
    style VALIDATE fill:#2d6a2e,color:#fff
    style MAPPING fill:#2d6a2e,color:#fff
    style LOGGER fill:#1a4a6e,color:#fff
    style JSONL fill:#1a4a6e,color:#fff
    style ARTS fill:#1a4a6e,color:#fff
    style SUMMARY fill:#1a4a6e,color:#fff
```

**Legenda:**
- Linhas sólidas `→` = Fluxo de dados obrigatório (8.0a)
- Linhas tracejadas `-.->` = Fluxo de observabilidade opcional (8.0b, fail-safe)

### Fronteiras de Falha

| Cenário | Comportamento |
|---|---|
| Logger não inicializado (`self.logger = None`) | Planner ignora todas as chamadas de log. Pipeline opera idêntico à Fase 7.1. |
| `logger.log()` lança `OSError` | `try/except` silencia o erro. Task continua. Evento perdido mas pipeline intacto. |
| `logger.save_artifact()` lança exceção | Artefato NÃO é salvo em `.forge/logs/` mas PERMANECE no ArtifactStore e no relatório `.md`. |
| Escrita de `PRD_FINAL_{ts}.md` falha | `try/except` em `main.py`. Mensagem de aviso no terminal. Pipeline não aborta. |
| Diretório `.forge/logs/` sem permissão de escrita | Logger falha na inicialização → `self.logger = None` → pipeline opera normal. |

### Contratos de Interface — Novos Métodos

**`AgentController.get_artifact_content(name: str) -> str`**

```python
def get_artifact_content(self, name: str) -> str:
    """
    FASE 8.0a: Retorna conteúdo textual de um artefato pelo nome.
    
    Args:
        name: Nome do artefato (ex: "prd_final", "prd", "system_design")
    
    Returns:
        Conteúdo string do artefato, ou string vazia se não existir.
    
    Contrato:
        - Nunca lança exceção
        - Retorna "" para artefatos inexistentes
        - Retorna versão mais recente se houver múltiplas
    """
```

**`PipelineLogger.__init__(run_id: str, log_dir: str = ".forge/logs")`**

```python
def __init__(self, run_id: str, log_dir: str = ".forge/logs"):
    """
    FASE 8.0b: Inicializa logger para uma execução do pipeline.
    
    Args:
        run_id: Identificador único da execução (timestamp)
        log_dir: Diretório raiz para logs (default: .forge/logs)
    
    Contrato:
        - Cria diretório {log_dir}/{run_id}/ e {log_dir}/{run_id}/artifacts/
        - Se a criação falhar, lança OSError (capturada pelo Controller)
    
    Estrutura criada:
        .forge/logs/{run_id}/
        ├── pipeline.jsonl
        ├── pipeline_summary.md
        └── artifacts/
            ├── prd.md
            ├── prd_review.md
            └── ...
    """
```

**`PipelineLogger.log(task_id: str, event_type: str, agent: str = "", data: Dict[str, Any] = None) -> None`**

```python
def log(self, task_id: str, event_type: str, agent: str = "",
        data: Dict[str, Any] = None) -> None:
    """
    Persiste evento como uma linha JSON no arquivo pipeline.jsonl.
    
    Args:
        task_id: ID da task (ex: "TASK_01", "TASK_07")
        event_type: Tipo do evento (TASK_START, TASK_END, VALIDATION, ERROR)
        agent: Nome do agente responsável (ex: "product_manager")
        data: Payload livre com detalhes do evento
    
    Contrato:
        - Append atômico ao arquivo (uma linha por chamada)
        - Nunca lança exceção para o chamador (try/except interno)
        - Se escrita falhar, evento é adicionado apenas ao buffer em memória
    """
```

**`PipelineLogger.save_artifact(name: str, content: str, created_by: str = "") -> str`**

```python
def save_artifact(self, name: str, content: str, created_by: str = "") -> str:
    """
    Salva artefato individual como arquivo .md separado.
    
    Args:
        name: Nome do artefato (ex: "prd", "system_design")
        content: Conteúdo Markdown completo
        created_by: Agente que criou (ex: "architect")
    
    Returns:
        Path absoluto do arquivo salvo, ou "" se falhar.
    
    Contrato:
        - Arquivo salvo em {artifacts_dir}/{name}.md
        - Se escrita falhar, retorna "" (não lança exceção)
        - Registra evento ARTIFACT_PERSISTED via self.log()
    """
```

**`PipelineLogger.log_validation(task_id: str, artifact_type: str, validation_result: Dict, content_preview: str = "") -> None`**

```python
def log_validation(self, task_id: str, artifact_type: str,
                   validation_result: Dict, content_preview: str = "") -> None:
    """
    Registra resultado de validação de artefato.
    
    Contrato:
        - Chama self.log() internamente (mesmo comportamento fail-safe)
        - content_preview truncado a 200 chars
    """
```

**`PipelineLogger.finalize(blackboard_snapshot: Dict = None) -> str`**

```python
def finalize(self, blackboard_snapshot: Dict = None) -> str:
    """
    Gera arquivo pipeline_summary.md com timeline e métricas.
    
    Returns:
        Path do diretório da execução, ou "" se falhar.
    
    Contrato:
        - Chamado uma vez ao final do pipeline
        - Se falhar, não afeta o resultado do pipeline
    """
```

**`Planner.__init__` — Parâmetro Adicional**

```python
def __init__(self, blackboard: Blackboard,
             artifact_store: ArtifactStore,
             agents: Dict[str, Any],
             provider: Any = None,
             think: bool = False,
             logger: Any = None) -> None:  # FASE 8.0b: default None
```

**Verificação C-001:** O parâmetro `logger` tem `default=None`. Todos os 48 testes existentes que instanciam `Planner` sem `logger` continuam funcionando sem alteração.

---

## 3. TECH SPECS

### 3.1 Estrutura de Dados — PipelineEvent (JSON Schema)

Cada linha do arquivo `pipeline.jsonl` segue este schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PipelineEvent",
  "type": "object",
  "required": ["timestamp", "run_id", "task_id", "event_type"],
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 com timezone local"
    },
    "run_id": {
      "type": "string",
      "description": "ID da execução (formato: YYYYMMDD_HHMMSS)"
    },
    "task_id": {
      "type": "string",
      "enum": ["TASK_01", "TASK_02", "TASK_03", "TASK_04", "TASK_04b",
               "TASK_05", "TASK_06", "TASK_07", "PIPELINE", "ARTIFACT_SAVE"],
      "description": "Identificador da task ou evento de sistema"
    },
    "event_type": {
      "type": "string",
      "enum": ["TASK_START", "TASK_END", "VALIDATION", "ERROR",
               "ARTIFACT_PERSISTED", "PIPELINE_START", "PIPELINE_END"],
      "description": "Tipo do evento"
    },
    "agent": {
      "type": "string",
      "description": "Nome do agente responsável (vazio para eventos de sistema)"
    },
    "data": {
      "type": "object",
      "description": "Payload livre específico por event_type",
      "properties": {
        "status": { "type": "string" },
        "valid": { "type": "boolean" },
        "completeness": { "type": "number" },
        "density": { "type": "number" },
        "table_count": { "type": "integer" },
        "fail_reasons": { "type": "array", "items": { "type": "string" } },
        "missing_sections": { "type": "array", "items": { "type": "string" } },
        "content_preview": { "type": "string", "maxLength": 200 },
        "error": { "type": "string" },
        "name": { "type": "string" },
        "path": { "type": "string" },
        "chars": { "type": "integer" }
      }
    }
  }
}
```

**Exemplo de linha JSONL (TASK_START):**

```json
{"timestamp": "2026-03-28T14:30:01.123456", "run_id": "20260328_143000", "task_id": "TASK_01", "event_type": "TASK_START", "agent": "product_manager", "data": {}}
```

**Exemplo de linha JSONL (VALIDATION):**

```json
{"timestamp": "2026-03-28T14:30:45.789", "run_id": "20260328_143000", "task_id": "TASK_01", "event_type": "VALIDATION", "agent": "", "data": {"artifact_type": "prd", "valid": true, "completeness": 0.82, "density": 0.91, "table_count": 8, "fail_reasons": [], "missing_sections": ["## Diferenciais"], "content_preview": "## Objetivo\n- Centralizar ofertas..."}}
```

**Exemplo de linha JSONL (ERROR):**

```json
{"timestamp": "2026-03-28T14:31:02.456", "run_id": "20260328_143000", "task_id": "TASK_05", "event_type": "ERROR", "agent": "debate_engine", "data": {"error": "Connection timeout to Ollama API"}}
```

### 3.2 Seções Obrigatórias — Tipo `prd_final` no OutputValidator

As 16 seções correspondem exatamente às seções do `NEXUS_CONSOLIDATION_TEMPLATE` atual (Fase 7.1). Na Fase 9.0 o template será expandido para 18, e o validador acompanhará.

```python
"prd_final": [
    "## Visão do Produto",
    "## Problema e Solução",
    "## Público-Alvo",
    "## Princípios Arquiteturais",
    "## Diferenciais",
    "## Requisitos Funcionais",
    "## Requisitos Não-Funcionais",
    "## Arquitetura e Tech Stack",
    "## ADRs",
    "## Análise de Segurança",
    "## Escopo MVP",
    "## Riscos Consolidados",
    "## Métricas de Sucesso",
    "## Plano de Implementação",
    "## Decisões do Debate",
    "## Constraints Técnicos",
],
```

**Thresholds para `prd_final`:**

```python
MIN_CHARS["prd_final"] = 800       # PRD Final é mais denso que PRD base (600)
MIN_COMPLETENESS["prd_final"] = 0.70  # 70% de 16 seções = mínimo 11 presentes
```

**Justificativa do threshold 0.70:** O `NEXUS_CONSOLIDATION_TEMPLATE` atual produz ~14 seções consistentemente (conforme output observado). Exigir 100% bloquearia pipelines válidos quando o modelo omite 1-2 seções de menor importância. O threshold de 0.70 (11/16) garante que todas as seções estruturais críticas estejam presentes enquanto tolera omissões em seções secundárias como "Decisões do Debate" ou "Constraints Técnicos".

### 3.3 Regras de Fallback

| Operação | Falha Possível | Comportamento de Fallback |
|---|---|---|
| Escrita de `PRD_FINAL_{ts}.md` em `main.py` | `OSError`, `PermissionError` | `try/except` imprime aviso no terminal. Pipeline não aborta. PRD Final permanece acessível via `controller.get_artifact_content("prd_final")` e no relatório consolidado. |
| Inicialização do `PipelineLogger` em `controller.py` | `OSError` ao criar diretório | `self.logger = None`. Todo código downstream faz `if self.logger:` antes de chamar. |
| `logger.log()` falha durante escrita | `OSError` no append ao JSONL | Exceção capturada internamente. Evento adicionado apenas ao `self._events` em memória. Próximos logs tentam escrever normalmente. |
| `logger.save_artifact()` falha | `OSError` na escrita do `.md` | Retorna `""`. Artefato permanece no ArtifactStore normalmente. |
| `logger.finalize()` falha | `OSError` ao gerar sumário | Retorna `""`. Pipeline já terminou — resultado não é afetado. |

---

## 4. PLANO DE IMPLEMENTAÇÃO SEQUENCIAL

### Passo 1: Sub-fase 8.0a — PRD Final Isolado + Validação Correta

**Objetivo:** Após este passo, o sistema gera `PRD_FINAL_{timestamp}.md` como arquivo separado e valida o `prd_final` contra suas seções específicas.

**Pré-requisito:** Nenhum (pode ser implementado imediatamente sobre a Fase 7.1).

#### 1.1 Modificar `src/core/output_validator.py`

**Mudanças:**

```python
# ═══ ADIÇÕES ao dict REQUIRED_SECTIONS ═══

REQUIRED_SECTIONS = {
    # ... seções existentes "prd", "system_design", "review", etc. INTACTAS ...
    
    # FASE 8.0a: Tipo dedicado para PRD Final consolidado
    "prd_final": [
        "## Visão do Produto",
        "## Problema e Solução",
        "## Público-Alvo",
        "## Princípios Arquiteturais",
        "## Diferenciais",
        "## Requisitos Funcionais",
        "## Requisitos Não-Funcionais",
        "## Arquitetura e Tech Stack",
        "## ADRs",
        "## Análise de Segurança",
        "## Escopo MVP",
        "## Riscos Consolidados",
        "## Métricas de Sucesso",
        "## Plano de Implementação",
        "## Decisões do Debate",
        "## Constraints Técnicos",
    ],
}

# ═══ ADIÇÕES aos dicts MIN_CHARS e MIN_COMPLETENESS ═══

MIN_CHARS = {
    # ... existentes intactos ...
    "prd_final": 800,  # FASE 8.0a
}

MIN_COMPLETENESS = {
    # ... existentes intactos ...
    "prd_final": 0.70,  # FASE 8.0a
}
```

**Nenhum método existente é alterado.** Apenas dados adicionados aos dicionários de configuração.

#### 1.2 Modificar `src/core/planner.py`

**Mudança única** — método `_get_artifact_tag_for_validator`:

```python
def _get_artifact_tag_for_validator(self, task: TaskDefinition) -> str:
    """Mapeia task_id/output_artifact para o tipo esperado pelo OutputValidator."""
    mapping = {
        "prd": "prd",
        "system_design": "system_design",
        "prd_review": "review",
        "security_review": "security_review",
        "development_plan": "plan",
        "prd_final": "prd_final",  # FASE 8.0a: Era "prd" — agora usa validação específica
    }
    return mapping.get(task.output_artifact, "document")
```

**Diff exato:** Linha `"prd_final": "prd"` → `"prd_final": "prd_final"`.

#### 1.3 Modificar `src/core/controller.py`

**Mudança 1** — Adicionar método público `get_artifact_content`:

```python
def get_artifact_content(self, name: str) -> str:
    """
    FASE 8.0a: Retorna conteúdo de um artefato pelo nome.
    Nunca lança exceção. Retorna "" para artefatos inexistentes.
    """
    art = self.artifact_store.read(name)
    return art.content if art else ""
```

**Posição:** Após o método `_generate_final_report`, antes do final da classe.

**Mudança 2** — No `_generate_final_report`, corrigir o `type_map`:

```python
# Localizar a linha existente:
#     "prd": "prd", "prd_final": "prd",
# Substituir por:
type_map = {
    "prd": "prd", "prd_final": "prd_final",  # FASE 8.0a: Era "prd"
    "system_design": "system_design",
    "prd_review": "review", "security_review": "security_review",
    "development_plan": "plan"
}
```

#### 1.4 Modificar `src/cli/main.py`

**Mudança** — Após a linha `final_plan = controller.run_pipeline(idea, report_filename)`, adicionar:

```python
    try:
        final_plan = controller.run_pipeline(idea, report_filename)
        
        # ═══ FASE 8.0a: Salvar PRD Final em arquivo separado ═══
        prd_final_content = controller.get_artifact_content("prd_final")
        if prd_final_content and len(prd_final_content.strip()) > 200:
            prd_final_filename = f"PRD_FINAL_{timestamp}.md"
            try:
                with open(prd_final_filename, "w", encoding="utf-8") as f:
                    f.write(f"# PRD FINAL — Padrão NEXUS\n\n")
                    f.write(f"**Ideia:** {idea[:200]}\n\n")
                    f.write(f"**Modelo:** {selected_model}\n\n")
                    f.write(f"**Gerado em:** {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
                    f.write("---\n\n")
                    f.write(prd_final_content)
                print(f"\n✅ PRD Final salvo em: {prd_final_filename}")
            except OSError as e:
                print(f"\n⚠️ Não foi possível salvar PRD Final em arquivo: {e}")
        # ═══ FIM DA MUDANÇA 8.0a ═══
        
        print("\n" + "=" * 50)
        # ... restante existente ...
```

**Posição exata:** Entre `final_plan = controller.run_pipeline(...)` e `print("\n" + "=" * 50)`.

#### 1.5 Testes da Sub-fase 8.0a

**Modificar** `tests/test_output_validator_v2.py` — Adicionar 2 métodos:

```python
def test_validate_prd_final_dedicated_type(self):
    """FASE 8.0a: prd_final usa tipo dedicado com 16 seções NEXUS."""
    content = (
        "## Visão do Produto\n- Codinome: TestApp\n- Declaração: Teste\n\n"
        "## Problema e Solução\n| ID | P | I | R |\n|---|---|---|---|\n| P-01 | X | Y | Z |\n\n"
        "## Público-Alvo\n| Seg | Perfil | Prio |\n|---|---|---|\n| Dev | Lucas | P0 |\n\n"
        "## Princípios Arquiteturais\n| P | D | I |\n|---|---|---|\n| X | Y | Z |\n\n"
        "## Diferenciais\n| A | P | S |\n|---|---|---|\n| X | Y | Z |\n\n"
        "## Requisitos Funcionais\n| ID | R | CA | P | Cx | S |\n|---|---|---|---|---|---|\n| RF-01 | X | Y | Must | Low | OK |\n\n"
        "## Requisitos Não-Funcionais\n| ID | C | R | M | T |\n|---|---|---|---|---|\n| RNF-01 | Perf | Lat | p95 | 200ms |\n\n"
        "## Arquitetura e Tech Stack\n| C | T | J |\n|---|---|---|\n| Backend | FastAPI | Async |\n\n"
        "## ADRs\n| ID | D | AR | C |\n|---|---|---|---|\n| ADR-01 | SQLite | PG | Simplicidade |\n\n"
        "## Análise de Segurança\n| ID | A | C | S | M |\n|---|---|---|---|---|\n| SEC-01 | Spoofing | Auth | Alta | Rate limit |\n\n"
        "## Escopo MVP\n**Inclui:** RF-01\n**NÃO inclui:** Mobile\n\n"
        "## Riscos Consolidados\n| ID | R | F | P | I | M |\n|---|---|---|---|---|---|\n| R-01 | X | PRD | M | A | Backup |\n\n"
        "## Métricas de Sucesso\n| M | T | P | CM |\n|---|---|---|---|\n| Users | 100 | 30d | GA |\n\n"
        "## Plano de Implementação\n| F | D | E | CC |\n|---|---|---|---|\n| F1 | 2s | Core | Tests |\n\n"
        "## Decisões do Debate\n- Adoção de ISR + SWR\n\n"
        "## Constraints Técnicos\n- Linguagem: Python\n- Framework: FastAPI\n"
        "Texto adicional para garantir 800+ caracteres no PRD Final consolidado. " * 3
    )
    res = self.validator.validate(content, "prd_final")
    self.assertTrue(res["valid"], f"Falha: {res.get('fail_reasons')}")
    self.assertGreaterEqual(res["completeness_score"], 0.70)

def test_prd_final_not_validated_as_prd(self):
    """FASE 8.0a: prd_final com seções NEXUS passa em prd_final mas pode falhar em prd."""
    # Verificar que o tipo prd_final existe e tem seções diferentes do prd
    prd_sections = set(self.validator.REQUIRED_SECTIONS["prd"])
    prd_final_sections = set(self.validator.REQUIRED_SECTIONS["prd_final"])
    # As seções DEVEM ser diferentes (prd tem "## Objetivo", prd_final tem "## Visão do Produto")
    self.assertNotEqual(prd_sections, prd_final_sections)
    self.assertIn("## Visão do Produto", prd_final_sections)
    self.assertNotIn("## Visão do Produto", prd_sections)
    self.assertIn("## Objetivo", prd_sections)
    self.assertNotIn("## Objetivo", prd_final_sections)
```

**Modificar** `tests/test_planner.py` — Adicionar 1 método:

```python
def test_prd_final_validator_mapping():
    """FASE 8.0a: Verifica que prd_final é mapeado para tipo prd_final, não prd."""
    bb = Blackboard()
    store = ArtifactStore(bb, persist_dir=".tmp_planner")
    planner = Planner(bb, store, agents={})
    planner.load_default_dag()
    
    task_07 = [t for t in planner.dag if t.task_id == "TASK_07"][0]
    tag = planner._get_artifact_tag_for_validator(task_07)
    assert tag == "prd_final", f"Esperado 'prd_final', obtido '{tag}'"
```

**Checkpoint de validação da Sub-fase 8.0a:**

```bash
# Executar APENAS os testes relevantes para 8.0a antes de prosseguir
pytest tests/test_output_validator_v2.py tests/test_planner.py -v --tb=short

# Resultado esperado: Todos passam, incluindo os 2 novos
```

---

### Passo 2: Sub-fase 8.0b — PipelineLogger

**Objetivo:** Implementar logging estruturado JSONL com salvamento individual de artefatos.

**Pré-requisito:** Sub-fase 8.0a concluída (testes passando).

#### 2.1 Novo Arquivo: `src/core/pipeline_logger.py`

```python
"""
pipeline_logger.py — Logger estruturado para execuções do pipeline IdeaForge.

FASE 8.0b:
- Captura eventos do pipeline em formato JSONL (um JSON por linha)
- Salva artefatos individuais em disco como arquivos .md separados
- Gera sumário legível ao final da execução
- TODA operação de I/O está em try/except — falha no log ≠ falha no pipeline

Contrato:
    Input: Eventos do pipeline (task_id, event_type, agent, data)
    Output: Arquivo .jsonl + artefatos .md + sumário .md

NÃO contém lógica de negócio. NÃO conhece agentes. Apenas persiste eventos.
"""

import os
import json
import datetime
from typing import Dict, Any, List


class PipelineLogger:
    """Logger JSONL para rastreamento estruturado de execuções."""
    
    def __init__(self, run_id: str, log_dir: str = ".forge/logs"):
        """
        Inicializa logger. Cria diretórios necessários.
        Lança OSError se não conseguir criar diretórios (capturada pelo Controller).
        """
        self.run_id = run_id
        self.run_dir = os.path.join(log_dir, run_id)
        self.artifacts_dir = os.path.join(self.run_dir, "artifacts")
        self.log_path = os.path.join(self.run_dir, "pipeline.jsonl")
        self.summary_path = os.path.join(self.run_dir, "pipeline_summary.md")
        self._events: List[Dict[str, Any]] = []
        
        # Esta é a ÚNICA operação que pode lançar exceção para o chamador
        os.makedirs(self.artifacts_dir, exist_ok=True)
    
    def log(self, task_id: str, event_type: str, agent: str = "",
            data: Dict[str, Any] = None) -> None:
        """
        Persiste evento como linha JSONL.
        NUNCA lança exceção para o chamador.
        """
        event = {
            "timestamp": datetime.datetime.now().isoformat(),
            "run_id": self.run_id,
            "task_id": task_id,
            "event_type": event_type,
            "agent": agent,
            "data": data or {}
        }
        self._events.append(event)
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            pass  # Evento salvo em memória, escrita em disco falhou silenciosamente
    
    def log_validation(self, task_id: str, artifact_type: str,
                       validation_result: Dict, content_preview: str = "") -> None:
        """Registra resultado de validação com preview truncado."""
        self.log(
            task_id=task_id,
            event_type="VALIDATION",
            data={
                "artifact_type": artifact_type,
                "valid": validation_result.get("valid", False),
                "completeness": validation_result.get("completeness_score", 0),
                "density": validation_result.get("density_score", 0),
                "table_count": validation_result.get("table_count", 0),
                "fail_reasons": validation_result.get("fail_reasons", []),
                "missing_sections": validation_result.get("missing_sections", []),
                "content_preview": content_preview[:200] if content_preview else ""
            }
        )
    
    def save_artifact(self, name: str, content: str, created_by: str = "") -> str:
        """
        Salva artefato individual como .md.
        Retorna path do arquivo, ou "" se falhar.
        NUNCA lança exceção para o chamador.
        """
        filepath = os.path.join(self.artifacts_dir, f"{name}.md")
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {name.upper().replace('_', ' ')}\n\n")
                if created_by:
                    f.write(f"**Criado por:** {created_by}\n\n---\n\n")
                f.write(content)
        except OSError:
            filepath = ""
        
        self.log(
            task_id="ARTIFACT_SAVE",
            event_type="ARTIFACT_PERSISTED",
            agent=created_by,
            data={"name": name, "path": filepath, "chars": len(content)}
        )
        
        return filepath
    
    def finalize(self, blackboard_snapshot: Dict = None) -> str:
        """
        Gera sumário legível da execução.
        Retorna path do diretório da run, ou "" se falhar.
        NUNCA lança exceção para o chamador.
        """
        try:
            with open(self.summary_path, "w", encoding="utf-8") as f:
                f.write(f"# Pipeline Summary — {self.run_id}\n\n")
                f.write(f"**Total de eventos:** {len(self._events)}\n\n")
                
                # Timeline
                f.write("## Timeline\n\n")
                f.write("| Hora | Task | Evento | Detalhes |\n")
                f.write("|---|---|---|---|\n")
                for evt in self._events:
                    detail = self._format_event_detail(evt)
                    ts_short = evt["timestamp"].split("T")[1][:8] if "T" in evt["timestamp"] else ""
                    f.write(f"| {ts_short} | {evt['task_id']} | {evt['event_type']} | {detail} |\n")
                
                # Validações com falha
                failed = [e for e in self._events
                          if e["event_type"] == "VALIDATION"
                          and not e.get("data", {}).get("valid", True)]
                if failed:
                    f.write("\n## Validações com Falha\n\n")
                    for fv in failed:
                        d = fv.get("data", {})
                        f.write(f"- **{fv['task_id']}** ({d.get('artifact_type', '?')}): "
                                f"{d.get('fail_reasons', [])}\n")
                        missing = d.get("missing_sections", [])
                        if missing:
                            f.write(f"  Seções faltantes: {missing}\n")
                
                # Erros
                errors = [e for e in self._events if e["event_type"] == "ERROR"]
                if errors:
                    f.write("\n## Erros\n\n")
                    for err in errors:
                        f.write(f"- **{err['task_id']}**: {err.get('data', {}).get('error', 'desconhecido')}\n")
                
                f.write(f"\n---\n*Gerado por PipelineLogger — IdeaForge CLI Fase 8.0*\n")
            
            return self.run_dir
        except OSError:
            return ""
    
    def _format_event_detail(self, event: Dict) -> str:
        """Formata detalhes de um evento para a tabela do sumário."""
        evt_type = event.get("event_type", "")
        data = event.get("data", {})
        
        if evt_type == "TASK_START":
            return f"agent={event.get('agent', '')}"
        elif evt_type == "TASK_END":
            return f"status={data.get('status', '?')}"
        elif evt_type == "VALIDATION":
            return f"valid={data.get('valid')} compl={data.get('completeness', 0):.0%}"
        elif evt_type == "ERROR":
            return data.get("error", "")[:60]
        elif evt_type == "ARTIFACT_PERSISTED":
            return f"{data.get('name', '?')} ({data.get('chars', 0)} chars)"
        return ""
    
    def get_run_dir(self) -> str:
        """Retorna o diretório da execução atual."""
        return self.run_dir
```

#### 2.2 Integrar Logger no `src/core/controller.py`

**Mudança 1** — No `__init__`, após criação do Blackboard e antes do Planner:

```python
def __init__(self, provider: ModelProvider, think: bool = False):
    self.provider = provider
    self.think = think
    direct_mode = not think
    
    # Inicializa infraestrutura Blackboard
    self.blackboard = Blackboard()
    self.artifact_store = ArtifactStore(self.blackboard)
    
    # ═══ FASE 8.0b: Inicializar PipelineLogger (fail-safe) ═══
    self._run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    self.logger = None  # Default: sem logger
    try:
        from src.core.pipeline_logger import PipelineLogger
        self.logger = PipelineLogger(run_id=self._run_id)
    except Exception:
        pass  # Logger falhou — pipeline opera normalmente
    # ═══ FIM FASE 8.0b ═══
    
    # Inicializa Agentes Especialistas
    self.agents = {
        # ... tudo existente inalterado ...
    }
    
    # ... atributos diretos existentes ...
    
    # Inicializa Planner
    self.planner = Planner(
        blackboard=self.blackboard,
        artifact_store=self.artifact_store,
        agents=self.agents,
        provider=provider,
        think=think,
        logger=self.logger  # FASE 8.0b: Injetar logger (pode ser None)
    )
    self.planner.load_default_dag()
```

**Requer import adicional no topo de `controller.py`:**

```python
import datetime  # FASE 8.0b (já importado implicitamente via blackboard, mas tornar explícito)
```

**Mudança 2** — No `run_pipeline`, antes do `emit_pipeline_state("PIPELINE_COMPLETE", ...)`:

```python
    # ═══ FASE 8.0b: Finalizar logger ═══
    if self.logger:
        try:
            self.logger.finalize(blackboard_snapshot=self.blackboard.snapshot())
        except Exception:
            pass  # Falha no sumário não afeta resultado
    # ═══ FIM FASE 8.0b ═══
    
    emit_pipeline_state("PIPELINE_COMPLETE", "Pipeline Blackboard concluído")
```

**Mudança 3** — No `run_pipeline`, logo após `emit_pipeline_state("PIPELINE_START", ...)`:

```python
    emit_pipeline_state("PIPELINE_START", "Iniciando Pipeline NEXUS (Fase 4)")
    
    # ═══ FASE 8.0b: Log de início do pipeline ═══
    if self.logger:
        try:
            self.logger.log("PIPELINE", "PIPELINE_START", data={"idea_length": len(initial_idea)})
        except Exception:
            pass
    # ═══ FIM FASE 8.0b ═══
```

#### 2.3 Integrar Logger no `src/core/planner.py`

**Mudança 1** — No `__init__`:

```python
def __init__(self, blackboard: Blackboard,
             artifact_store: ArtifactStore,
             agents: Dict[str, Any],
             provider: Any = None,
             think: bool = False,
             logger: Any = None) -> None:  # FASE 8.0b
    self.blackboard = blackboard
    self.artifact_store = artifact_store
    self.agents = agents
    self.provider = provider
    self.think = think
    self.logger = logger  # FASE 8.0b: PipelineLogger (pode ser None)
    self.dag: List[TaskDefinition] = []
```

**Mudança 2** — No `_execute_task`, inserir 4 pontos de instrumentação:

```python
def _execute_task(self, task: TaskDefinition) -> None:
    """Executa uma task individual com Budgeting e Post-processing (Fase 3.1)."""
    self.blackboard.set_task_status(task.task_id, TaskStatus.RUNNING)
    
    # ═══ FASE 8.0b: Log TASK_START ═══
    if self.logger:
        try:
            self.logger.log(task.task_id, "TASK_START", task.agent_name)
        except Exception:
            pass
    # ═══ FIM ═══
    
    # ... código existente de TASK_CONFIGS e try: ...
    
    try:
        # ... todo o bloco existente de hot-load, dispatch, pós-processamento ...
        
        # Após a seção de validação (onde faz validator.validate):
        # ═══ FASE 8.0b: Log VALIDATION ═══
        if self.logger:
            try:
                self.logger.log_validation(
                    task_id=task.task_id,
                    artifact_type=artifact_type_tag,
                    validation_result=validation,
                    content_preview=clean_result[:200]
                )
            except Exception:
                pass
        # ═══ FIM ═══
        
        # Após self.artifact_store.write(...):
        # ═══ FASE 8.0b: Salvar artefato individual + Log TASK_END ═══
        if self.logger:
            try:
                self.logger.save_artifact(
                    name=task.output_artifact,
                    content=clean_result,
                    created_by=task.agent_name
                )
                self.logger.log(task.task_id, "TASK_END", task.agent_name,
                               {"status": "completed"})
            except Exception:
                pass
        # ═══ FIM ═══
        
        self.blackboard.set_task_status(task.task_id, TaskStatus.COMPLETED)
    
    except Exception as e:
        # ═══ FASE 8.0b: Log ERROR ═══
        if self.logger:
            try:
                self.logger.log(task.task_id, "ERROR", task.agent_name,
                               {"error": str(e)})
            except Exception:
                pass
        # ═══ FIM ═══
        
        self.blackboard.set_task_status(task.task_id, TaskStatus.FAILED)
        raise e
```

**Localização precisa dos 4 pontos de inserção no `_execute_task` existente:**

| Ponto | Posição | Após qual linha existente |
|---|---|---|
| TASK_START | Início do método | Após `self.blackboard.set_task_status(task.task_id, TaskStatus.RUNNING)` |
| VALIDATION | Dentro do try, após validação | Após o bloco `if not validation.get("valid", True):` (ambos ramos) |
| TASK_END + ARTIFACT | Dentro do try, após store | Após `self.artifact_store.write(...)` e antes de `self.blackboard.set_task_status(...COMPLETED)` |
| ERROR | No except | Antes de `self.blackboard.set_task_status(task.task_id, TaskStatus.FAILED)` |

#### 2.4 Testes da Sub-fase 8.0b

**Novo arquivo:** `tests/test_pipeline_logger.py`

```python
"""
test_pipeline_logger.py — Testes para o PipelineLogger (Fase 8.0b).
"""
import pytest
import os
import json
from src.core.pipeline_logger import PipelineLogger


class TestPipelineLogger:
    
    def test_creates_directory_structure(self, tmp_path):
        logger = PipelineLogger(run_id="test_001", log_dir=str(tmp_path))
        assert os.path.isdir(logger.run_dir)
        assert os.path.isdir(logger.artifacts_dir)
    
    def test_log_writes_jsonl(self, tmp_path):
        logger = PipelineLogger(run_id="test_002", log_dir=str(tmp_path))
        logger.log("TASK_01", "TASK_START", "product_manager")
        logger.log("TASK_01", "TASK_END", "product_manager", {"status": "completed"})
        
        with open(logger.log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        event1 = json.loads(lines[0])
        assert event1["task_id"] == "TASK_01"
        assert event1["event_type"] == "TASK_START"
        assert event1["agent"] == "product_manager"
        assert "timestamp" in event1
        assert event1["run_id"] == "test_002"
        
        event2 = json.loads(lines[1])
        assert event2["event_type"] == "TASK_END"
        assert event2["data"]["status"] == "completed"
    
    def test_log_validation_event(self, tmp_path):
        logger = PipelineLogger(run_id="test_003", log_dir=str(tmp_path))
        logger.log_validation(
            task_id="TASK_07",
            artifact_type="prd_final",
            validation_result={
                "valid": False,
                "completeness_score": 0.65,
                "density_score": 0.88,
                "table_count": 12,
                "fail_reasons": ["INCOMPLETE (65% < 70%)"],
                "missing_sections": ["## Decisões do Debate"]
            },
            content_preview="## Visão do Produto\n- Codinome: TestApp"
        )
        
        with open(logger.log_path, "r", encoding="utf-8") as f:
            event = json.loads(f.readline())
        
        assert event["event_type"] == "VALIDATION"
        assert event["data"]["valid"] is False
        assert event["data"]["completeness"] == 0.65
        assert "INCOMPLETE" in event["data"]["fail_reasons"][0]
        assert len(event["data"]["content_preview"]) <= 200
    
    def test_save_artifact(self, tmp_path):
        logger = PipelineLogger(run_id="test_004", log_dir=str(tmp_path))
        filepath = logger.save_artifact("prd", "## Objetivo\n- Teste completo", "product_manager")
        
        assert filepath != ""
        assert os.path.exists(filepath)
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "# PRD" in content
        assert "## Objetivo" in content
        assert "**Criado por:** product_manager" in content
    
    def test_save_artifact_failure_returns_empty(self, tmp_path):
        logger = PipelineLogger(run_id="test_005", log_dir=str(tmp_path))
        # Forçar falha removendo o diretório de artefatos
        os.rmdir(logger.artifacts_dir)
        os.makedirs(logger.artifacts_dir)  # Recriar vazio
        
        # Criar um arquivo com o mesmo nome do diretório para forçar OSError
        # Na verdade, testar com um path inválido
        logger.artifacts_dir = "/dev/null/impossible/path"
        filepath = logger.save_artifact("prd", "content", "pm")
        assert filepath == ""
    
    def test_finalize_generates_summary(self, tmp_path):
        logger = PipelineLogger(run_id="test_006", log_dir=str(tmp_path))
        logger.log("TASK_01", "TASK_START", "product_manager")
        logger.log("TASK_01", "TASK_END", "product_manager", {"status": "completed"})
        logger.log_validation("TASK_01", "prd",
                             {"valid": True, "completeness_score": 0.82})
        
        run_dir = logger.finalize()
        
        assert run_dir != ""
        assert os.path.exists(logger.summary_path)
        
        with open(logger.summary_path, "r", encoding="utf-8") as f:
            summary = f.read()
        assert "Pipeline Summary" in summary
        assert "TASK_01" in summary
        assert "TASK_START" in summary
        assert "Total de eventos:" in summary
    
    def test_finalize_shows_failed_validations(self, tmp_path):
        logger = PipelineLogger(run_id="test_007", log_dir=str(tmp_path))
        logger.log_validation("TASK_07", "prd_final",
                             {"valid": False, "fail_reasons": ["INCOMPLETE"],
                              "missing_sections": ["## ADRs"]})
        
        logger.finalize()
        
        with open(logger.summary_path, "r", encoding="utf-8") as f:
            summary = f.read()
        assert "Validações com Falha" in summary
        assert "TASK_07" in summary
        assert "INCOMPLETE" in summary
    
    def test_events_stored_in_memory(self, tmp_path):
        logger = PipelineLogger(run_id="test_008", log_dir=str(tmp_path))
        logger.log("T1", "TASK_START")
        logger.log("T1", "TASK_END")
        
        assert len(logger._events) == 2
    
    def test_log_never_raises(self, tmp_path):
        logger = PipelineLogger(run_id="test_009", log_dir=str(tmp_path))
        # Corromper o path do log para forçar falha de I/O
        logger.log_path = "/dev/null/impossible/pipeline.jsonl"
        
        # NÃO deve lançar exceção
        logger.log("TASK_01", "TASK_START", "pm")
        
        # Evento ainda está em memória
        assert len(logger._events) == 1


class TestPipelineLoggerIntegrationWithPlanner:
    """Testes de integração: Planner aceita logger=None sem quebrar."""
    
    def test_planner_accepts_none_logger(self):
        from src.core.blackboard import Blackboard
        from src.core.artifact_store import ArtifactStore
        from src.core.planner import Planner
        
        bb = Blackboard()
        store = ArtifactStore(bb, persist_dir=".tmp_logger_test")
        
        # Deve funcionar sem exceção
        planner = Planner(bb, store, agents={}, logger=None)
        assert planner.logger is None
    
    def test_planner_accepts_logger_instance(self, tmp_path):
        from src.core.blackboard import Blackboard
        from src.core.artifact_store import ArtifactStore
        from src.core.planner import Planner
        
        bb = Blackboard()
        store = ArtifactStore(bb, persist_dir=".tmp_logger_test")
        logger = PipelineLogger(run_id="planner_test", log_dir=str(tmp_path))
        
        planner = Planner(bb, store, agents={}, logger=logger)
        assert planner.logger is not None
```

---

## 5. STRUCTURAL STANDARDS

### 5.1 Nomenclatura de Arquivos

| Artefato | Padrão de Nome | Exemplo |
|---|---|---|
| PRD Final isolado | `PRD_FINAL_{YYYYMMDD_HHMMSS}.md` | `PRD_FINAL_20260328_143000.md` |
| Diretório de logs | `.forge/logs/{YYYYMMDD_HHMMSS}/` | `.forge/logs/20260328_143000/` |
| Log de eventos | `pipeline.jsonl` (dentro do diretório) | `.forge/logs/20260328_143000/pipeline.jsonl` |
| Sumário legível | `pipeline_summary.md` | `.forge/logs/20260328_143000/pipeline_summary.md` |
| Artefatos individuais | `{nome_artefato}.md` | `.forge/logs/20260328_143000/artifacts/prd.md` |

### 5.2 Regras de Logging

**O que registrar:**

| Event Type | Quando | Dados Obrigatórios |
|---|---|---|
| `PIPELINE_START` | Início de `run_pipeline()` | `idea_length` |
| `TASK_START` | Início de `_execute_task()` | (nenhum) |
| `TASK_END` | Task concluída com sucesso | `status: "completed"` |
| `VALIDATION` | Após cada chamada de `validator.validate()` | `valid`, `completeness`, `fail_reasons` |
| `ERROR` | Task falhou com exceção | `error: str(e)` |
| `ARTIFACT_PERSISTED` | Artefato salvo em disco pelo logger | `name`, `path`, `chars` |
| `PIPELINE_END` | Final de `run_pipeline()` | (via `finalize()`) |

**O que NÃO registrar:**

- Tokens individuais do streaming LLM
- Conteúdo completo de artefatos no JSONL (usar `content_preview[:200]`)
- Eventos do `SectionalGenerator` por pass (complexidade excessiva para esta fase)
- Interações do `human_gate` (dados do usuário)

### 5.3 Proibições Técnicas

| Proibição | Justificativa |
|---|---|
| `print()` para logs de sistema | Usar `self.logger.log()`. `print()` é reservado para output do CLI (agentes, relatório). |
| `sys.stdout.write()` para logs de sistema | Mesmo motivo. ANSI output continua nos handlers existentes. |
| I/O síncrono bloqueante na thread principal | O logger faz append atômico (uma escrita por evento). Se escala for problema, refatorar para buffer em memória com flush periódico. |
| Logging de dados sensíveis | Não registrar API keys, tokens de sessão, ou conteúdo do `.env`. |
| Criar diretórios fora de `.forge/` | Todo output de observabilidade vai para `.forge/logs/`. |

### 5.4 Padrão de Código para Chamadas ao Logger

Todo ponto de instrumentação deve seguir este padrão exato:

```python
# Padrão obrigatório para toda chamada ao logger
if self.logger:
    try:
        self.logger.log(...)  # ou save_artifact, log_validation, etc.
    except Exception:
        pass  # Falha no log NUNCA propaga para o pipeline
```

**Motivo do `except Exception` (não `except OSError`):** O logger pode falhar por razões inesperadas (JSON serialization de dados complexos, encoding issues). Capturar `Exception` garante que NENHUM bug no logger afete o pipeline. O custo é mascarar bugs no logger durante desenvolvimento — mitigado pelos testes unitários dedicados.

---

## 6. TRACEABILITY MATRIX

| Falha Original | ID | Solução Técnica | Arquivo Modificado | Teste de Validação |
|---|---|---|---|---|
| PRD Final embutido no relatório | F-01 | Salvar `PRD_FINAL_{ts}.md` em `main.py` com `try/except` | `src/cli/main.py` | Execução manual: verificar arquivo existe |
| PRD Final embutido no relatório | F-01 | `get_artifact_content()` no Controller | `src/core/controller.py` | `test_planner.py` (implícito via pipeline) |
| Validação genérica de prd_final | F-02 | Tipo `prd_final` com 16 seções em `REQUIRED_SECTIONS` | `src/core/output_validator.py` | `test_validate_prd_final_dedicated_type` |
| Validação genérica de prd_final | F-02 | Mapeamento `"prd_final": "prd_final"` no Planner | `src/core/planner.py` | `test_prd_final_validator_mapping` |
| Validação genérica de prd_final | F-02 | Corrigir `type_map` no `_generate_final_report` | `src/core/controller.py` | `test_prd_final_not_validated_as_prd` |
| Ausência de logs estruturados | F-03 | `PipelineLogger` com JSONL | `src/core/pipeline_logger.py` (NOVO) | `test_log_writes_jsonl` |
| Ausência de logs estruturados | F-03 | Integração no Planner (4 pontos) | `src/core/planner.py` | `test_planner_accepts_logger_instance` |
| Ausência de logs estruturados | F-03 | Integração no Controller (init + finalize) | `src/core/controller.py` | `test_planner_accepts_none_logger` |
| Ausência de logs estruturados | F-03 | Artefatos individuais em `.md` | `src/core/pipeline_logger.py` | `test_save_artifact` |
| Ausência de logs estruturados | F-03 | Sumário legível | `src/core/pipeline_logger.py` | `test_finalize_generates_summary` |
| Ausência de logs estruturados | F-03 | Fail-safe: logger não quebra pipeline | `src/core/planner.py` + `controller.py` | `test_log_never_raises` |

---

## Checklist de Pré-voo (Validação Antes do Merge)

### Sub-fase 8.0a

- [ ] `output_validator.py` contém chave `"prd_final"` em `REQUIRED_SECTIONS` com exatamente 16 seções
- [ ] `output_validator.py` contém `MIN_CHARS["prd_final"] = 800`
- [ ] `output_validator.py` contém `MIN_COMPLETENESS["prd_final"] = 0.70`
- [ ] `planner.py` → `_get_artifact_tag_for_validator` retorna `"prd_final"` para `task.output_artifact == "prd_final"`
- [ ] `controller.py` → `_generate_final_report` → `type_map` contém `"prd_final": "prd_final"`
- [ ] `controller.py` contém método `get_artifact_content(self, name: str) -> str`
- [ ] `main.py` salva `PRD_FINAL_{timestamp}.md` dentro de `try/except OSError`
- [ ] `pytest tests/test_output_validator_v2.py -v` → todos passam (incluindo 2 novos)
- [ ] `pytest tests/test_planner.py -v` → todos passam (incluindo 1 novo)
- [ ] `pytest tests/ -v` → todos os 48+ testes existentes passam sem modificação

### Sub-fase 8.0b

- [ ] Arquivo `src/core/pipeline_logger.py` existe e contém classe `PipelineLogger`
- [ ] `PipelineLogger.log()` contém `try/except` interno e nunca propaga exceções
- [ ] `PipelineLogger.save_artifact()` contém `try/except` interno e retorna `""` em falha
- [ ] `PipelineLogger.finalize()` contém `try/except` interno e retorna `""` em falha
- [ ] `controller.py` → `__init__` inicializa `self.logger` dentro de `try/except`
- [ ] `controller.py` → `run_pipeline` chama `self.logger.finalize()` dentro de `try/except`
- [ ] `planner.py` → `__init__` aceita `logger=None` como parâmetro
- [ ] `planner.py` → `_execute_task` contém 4 pontos de instrumentação com `if self.logger: try/except`
- [ ] `pytest tests/test_pipeline_logger.py -v` → todos os 10 testes passam
- [ ] `pytest tests/ -v` → todos os 50+ testes passam (48 originais + novos)
- [ ] Execução real com `--no-gate` gera diretório `.forge/logs/{run_id}/`
- [ ] Diretório contém `pipeline.jsonl` com eventos `TASK_START`/`TASK_END`
- [ ] Diretório contém `artifacts/prd.md`, `artifacts/prd_final.md`, etc.
- [ ] Diretório contém `pipeline_summary.md` legível

### Validação Cruzada

- [ ] Nenhuma assinatura pública existente foi alterada (diff manual)
- [ ] DAG continua com exatamente 8 tasks (contar em `load_default_dag`)
- [ ] Nenhum novo agente LLM foi adicionado
- [ ] Toda escrita em disco (logs, artefatos, PRD Final) está em `try/except`

---

*Blueprint Técnico — Fase 8.0 | IdeaForge CLI | Versão 1.0*