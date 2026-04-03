

# Blueprint — Fase 9.6: RetryOrchestrator com Recuperação Semântica

---

## 1. Contexto e Motivação

### Onde estamos
- **Onda 1 (Fase 9.5.3c) CONCLUÍDA**: Assembly 100% (20/20 seções, 26.5k chars)
- **Problema residual**: `is_clean: False` — 7 seções marcadas com `[GERAÇÃO FALHOU]` no PRD_FINAL
- **Causa raiz**: O modelo gpt-oss:20b-cloud falha qualitativamente em ~35% dos passes na primeira tentativa, e o retry atual (Nível 1 — mesmo prompt) não é suficiente para recuperar seções complexas

### Seções que falharam na certificação 9.5.3c
| Seção | Pass ID | Causa provável |
|---|---|---|
| `## Público-Alvo` | final_p02b | Modelo não gera personas com narrativa suficiente |
| `## Requisitos Funcionais` | final_p04 | Tabela RF muito longa, modelo trunca |
| `## ADRs` | final_p06c | Formato ficha não é seguido, qualidade insuficiente |
| `## Análise de Segurança` | final_p07 | STRIDE incompleto |
| `## Métricas de Sucesso` | final_p09b | Poucas métricas, sem método de medição |
| `## Plano de Implementação` | final_p10 | Plano superficial |
| `## Decisões do Debate` | final_p10 | Mesma passagem, seção negligenciada |

### Objetivo da Fase 9.6
Criar o `RetryOrchestrator` que intercepta as seções falhadas e as recupera com 3 níveis de fallback escalonados, garantindo `is_clean: True` em 3 execuções consecutivas.

---

## 2. Arquitetura do RetryOrchestrator

### 2.1 Posição no Pipeline

```
TASK_07 (Consolidação NEXUS — 20 passes)
    │
    ▼
┌─────────────────────────────────────────┐
│  SectionalGenerator (existente)         │
│  - Executa passes sequenciais           │
│  - Retry Nível 1 (mesmo prompt)         │ ← JÁ EXISTE (MAX_RETRIES_PER_PASS=3)
│  - Marca [GERAÇÃO FALHOU] se falhar     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  RetryOrchestrator (NOVO)               │
│  - Analisa consistency_report           │
│  - Identifica seções falhadas           │
│  - Aplica Nível 2: prompt reformulado   │
│  - Aplica Nível 3: template estático    │
│  - Substitui seções no PRD_FINAL        │
└──────────────┬──────────────────────────┘
               │
               ▼
         PRD_FINAL recuperado
```

### 2.2 Quando executa

O RetryOrchestrator é invocado **após** o `SectionalGenerator` terminar a geração dos 20 passes e **antes** da Cláusula de Integridade ser anexada. Ele opera dentro do método `consolidate_prd()` do `ProductManagerAgent`.

### 2.3 Diagrama de Fluxo

```
┌────────────────────────────┐
│ PRD_FINAL (pós-passes)     │
└──────────┬─────────────────┘
           │
     ┌─────▼──────┐
     │ Detectar    │
     │ seções com  │
     │ [GERAÇÃO    │
     │  FALHOU]    │
     └─────┬──────┘
           │
     ┌─────▼──────────────────────┐
     │ Para cada seção falhada:   │
     │                            │
     │ ┌────────────────────────┐ │
     │ │ NÍVEL 2: Prompt        │ │
     │ │ reformulado com        │ │
     │ │ exemplo inline +       │ │
     │ │ contexto enriquecido   │ │
     │ └──────┬─────────────────┘ │
     │        │                   │
     │   Passou?                  │
     │   ┌─Sim──► Substituir     │
     │   │        no PRD_FINAL   │
     │   │                       │
     │   └─Não──►                │
     │ ┌────────────────────────┐ │
     │ │ NÍVEL 3: Template      │ │
     │ │ estático preenchido    │ │
     │ │ com dados extraídos    │ │
     │ │ dos artefatos-fonte    │ │
     │ └──────┬─────────────────┘ │
     │        │                   │
     │   Substituir no PRD_FINAL │
     └────────┬───────────────────┘
              │
        ┌─────▼──────┐
        │ PRD_FINAL   │
        │ recuperado  │
        └─────────────┘
```

---

## 3. Especificação dos 3 Níveis de Retry

### Nível 1 — Retry Simples (JÁ EXISTE)
- **Onde**: `SectionalGenerator._execute_pass_with_retry()`
- **O quê**: Mesmo prompt + instrução corretiva baseada no `fail_reasons`
- **Limite**: `MAX_RETRIES_PER_PASS = 3`
- **Status**: Implementado na Fase 9.5

### Nível 2 — Prompt Reformulado (NOVO)
- **Onde**: `RetryOrchestrator._retry_level_2()`
- **Estratégia**:
  1. Prompt completamente reescrito com foco cirúrgico na seção falhada
  2. Exemplo inline extraído do exemplar gold-standard correspondente
  3. Contexto enriquecido: injeta trecho relevante do artefato-fonte (via `context_extractors`)
  4. Instrução explícita: "Gere APENAS a seção `## [Nome]`. Nada mais."
  5. `max_output_tokens` aumentado em 50% em relação ao pass original
- **Temperature**: Mantida em 0.1 (hardcoded no `OllamaProvider`). O ganho do Nível 2 vem do prompt cirúrgico e contexto enriquecido, não de mais entropia.
- **Validação**: `SectionQualityChecker.check_section_by_type()` + `OutputValidator.validate_pass()`
- **Limite**: 2 tentativas neste nível

### Nível 3 — Template Estático com Dados Extraídos (NOVO)
- **Onde**: `RetryOrchestrator._retry_level_3()`
- **Estratégia**:
  1. Não usa LLM
  2. Template Markdown pré-definido para cada seção
  3. Campos preenchidos programaticamente com dados extraídos dos artefatos (PRD, system_design, debate_transcript, etc.)
  4. Onde não há dados, preenche com `[Dado não disponível nos artefatos]`
  5. Resultado é sempre válido estruturalmente, mesmo que menos rico
- **Garantia**: Nível 3 NUNCA retorna vazio — é o safety net absoluto

---

## 4. Arquivos Impactados

| Arquivo | Ação | Descrição |
|---|---|---|
| `src/core/retry_orchestrator.py` | **NOVO** | Classe principal do RetryOrchestrator |
| `src/core/retry_templates.py` | **NOVO** | Templates estáticos para Nível 3 |
| `src/agents/product_manager_agent.py` | **MOD** | Invocar RetryOrchestrator após geração |
| `src/core/sectional_generator.py` | **MOD** | Expor método para gerar seção individual |
| `tests/test_retry_orchestrator.py` | **NOVO** | Testes unitários do orquestrador |
| `tests/test_retry_templates.py` | **NOVO** | Testes dos templates estáticos |

---

## 5. Especificação do `retry_orchestrator.py`

### 5.1 Classe `RetryOrchestrator`

```python
class RetryOrchestrator:
    """
    Orquestrador de retry em 3 níveis para seções falhadas do PRD_FINAL.
    
    Contrato:
        Input: PRD_FINAL (str) + artefatos-fonte (dict)
        Output: PRD_FINAL recuperado (str) com seções substituídas
    
    Invariantes:
        - Nível 3 NUNCA falha (template estático)
        - Cada seção é tratada independentemente
        - Log indica qual nível foi usado para cada seção
        - Zero chamadas LLM no Nível 3
    """
    
    FAILED_MARKER = "[GERAÇÃO FALHOU"
    
    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self.recovery_log: List[Dict] = []
    
    def recover(self, prd_final: str, artifacts: Dict[str, str]) -> str:
        """
        Ponto de entrada principal.
        
        Args:
            prd_final: PRD_FINAL com possíveis [GERAÇÃO FALHOU]
            artifacts: Dict com chaves: prd, system_design, security_review,
                       debate_transcript, development_plan
        
        Returns:
            PRD_FINAL com seções recuperadas
        """
    
    def _detect_failed_sections(self, prd_final: str) -> List[Dict]:
        """
        Identifica seções com marcador [GERAÇÃO FALHOU].
        
        Returns:
            Lista de dicts: {
                "heading": "## Público-Alvo",
                "pass_id": "final_p02b",
                "start_line": 42,
                "end_line": 44,
            }
        """
    
    def _retry_level_2(self, section_info: Dict, artifacts: Dict) -> Optional[str]:
        """
        Nível 2: Prompt reformulado com exemplo inline.
        Retorna conteúdo da seção ou None se falhar.
        """
    
    def _retry_level_3(self, section_info: Dict, artifacts: Dict) -> str:
        """
        Nível 3: Template estático preenchido com dados extraídos.
        NUNCA retorna None.
        """
    
    def _replace_section(self, prd_final: str, section_info: Dict, new_content: str) -> str:
        """
        Substitui seção falhada pelo conteúdo recuperado no PRD_FINAL.
        """
    
    def get_recovery_log(self) -> List[Dict]:
        """
        Retorna log de recuperação para auditoria.
        
        Formato:
        [
            {
                "heading": "## Público-Alvo",
                "level_used": 2,
                "attempts": 1,
                "chars_recovered": 850,
                "source": "llm_reformulated"
            },
            ...
        ]
        """
```

### 5.2 Mapeamento Seção → Pass ID → Artefato-Fonte

```python
SECTION_RECOVERY_MAP = {
    "## Visão do Produto": {
        "pass_id": "final_p01",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p01",
        "l3_template_key": "visao_produto",
    },
    "## Problema e Solução": {
        "pass_id": "final_p01",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p01",
        "l3_template_key": "problema_solucao",
    },
    "## Público-Alvo": {
        "pass_id": "final_p02b",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p02b",
        "l3_template_key": "publico_alvo",
    },
    "## Princípios Arquiteturais": {
        "pass_id": "final_p03b",
        "source_artifacts": ["prd", "system_design"],
        "exemplar_key": "final_p03b",
        "l3_template_key": "principios",
    },
    "## Diferenciais": {
        "pass_id": "final_p03b",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p03b",
        "l3_template_key": "diferenciais",
    },
    "## Requisitos Funcionais": {
        "pass_id": "final_p04",
        "source_artifacts": ["prd", "prd_review"],
        "exemplar_key": "final_p04",
        "l3_template_key": "requisitos_funcionais",
    },
    "## Requisitos Não-Funcionais": {
        "pass_id": "final_p05b",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p05b",
        "l3_template_key": "rnfs",
    },
    "## Arquitetura e Tech Stack": {
        "pass_id": "final_p06b",
        "source_artifacts": ["system_design"],
        "exemplar_key": "final_p06b",
        "l3_template_key": "arquitetura",
    },
    "## ADRs": {
        "pass_id": "final_p06c",
        "source_artifacts": ["system_design"],
        "exemplar_key": "final_p06c",
        "l3_template_key": "adrs",
    },
    "## Análise de Segurança": {
        "pass_id": "final_p07",
        "source_artifacts": ["security_review"],
        "exemplar_key": "final_p07",
        "l3_template_key": "seguranca",
    },
    "## Escopo MVP": {
        "pass_id": "final_p08",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p08",
        "l3_template_key": "escopo_mvp",
    },
    "## Riscos Consolidados": {
        "pass_id": "final_p09a",
        "source_artifacts": ["prd", "system_design", "security_review"],
        "exemplar_key": "final_p09a",
        "l3_template_key": "riscos",
    },
    "## Métricas de Sucesso": {
        "pass_id": "final_p09b",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p09b",
        "l3_template_key": "metricas",
    },
    "## Plano de Implementação": {
        "pass_id": "final_p10",
        "source_artifacts": ["development_plan"],
        "exemplar_key": "final_p10",
        "l3_template_key": "plano",
    },
    "## Decisões do Debate": {
        "pass_id": "final_p10",
        "source_artifacts": ["debate_transcript"],
        "exemplar_key": "final_p10",
        "l3_template_key": "decisoes_debate",
    },
    "## Constraints Técnicos": {
        "pass_id": "final_p11a",
        "source_artifacts": ["prd", "system_design"],
        "exemplar_key": "final_p11a",
        "l3_template_key": "constraints",
    },
    "## Matriz de Rastreabilidade": {
        "pass_id": "final_p11a",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p11a",
        "l3_template_key": "rastreabilidade",
    },
    "## Limitações Conhecidas": {
        "pass_id": "final_p11b",
        "source_artifacts": ["prd", "system_design"],
        "exemplar_key": "final_p11b",
        "l3_template_key": "limitacoes",
    },
    "## Guia de Replicação Resumido": {
        "pass_id": "final_p12",
        "source_artifacts": ["development_plan"],
        "exemplar_key": "final_p12",
        "l3_template_key": "guia_replicacao",
    },
    "## Cláusula de Integridade": {
        "pass_id": "final_p12",
        "source_artifacts": [],
        "exemplar_key": "final_p12",
        "l3_template_key": "clausula",
    },
}
```

---

## 6. Especificação do `retry_templates.py`

Templates estáticos para Nível 3. Cada template é uma função que recebe dados extraídos e retorna Markdown válido.

### 6.0 Estratégia de Priorização

**Prioridade 1 (implementar primeiro)** — As 7 seções que falharam na certificação 9.5.3c:
| Template | Extrator necessário |
|---|---|
| `template_publico_alvo` | `extract_personas_from_prd` |
| `template_requisitos_funcionais` | `extract_rfs_from_prd` |
| `template_adrs` | `extract_adrs_from_design` |
| `template_seguranca` | `extract_threats_from_security` |
| `template_metricas` | `extract_metrics_from_prd` |
| `template_plano` | `extract_phases_from_plan` |
| `template_decisoes_debate` | `extract_decisions_from_debate` |

**Prioridade 2 (stubs)** — As 13 seções que passaram na certificação. Implementar como:
```python
def template_stub(heading: str, extracted: Dict) -> str:
    """Stub para seções que normalmente não falham."""
    return f"{heading}\n\n[Seção não recuperável via template — verificar geração original]"
```
Expandir para templates completos apenas se falharem em certificação real.

### 6.1 Código dos Templates Prioritários

```python
"""
retry_templates.py — Templates estáticos para fallback Nível 3.

Contrato:
    - Cada função recebe um dict de dados extraídos dos artefatos
    - Cada função retorna Markdown estruturalmente válido
    - Se um dado não existir, usa placeholder "[Dado não disponível]"
    - NUNCA retorna string vazia
    - ZERO chamadas LLM
"""

def template_publico_alvo(extracted: Dict) -> str:
    """Template para ## Público-Alvo"""
    personas = extracted.get("personas", [])
    if not personas:
        personas = [
            {"segmento": "Usuário Principal", "perfil": "Persona não definida nos artefatos", "prioridade": "P0"},
            {"segmento": "Usuário Secundário", "perfil": "Persona não definida nos artefatos", "prioridade": "P1"},
            {"segmento": "Stakeholder", "perfil": "Persona não definida nos artefatos", "prioridade": "P2"},
        ]
    
    lines = ["## Público-Alvo\n"]
    lines.append("| Segmento | Perfil (nome fictício + dor específica) | Prioridade |")
    lines.append("|---|---|---|")
    for p in personas:
        lines.append(f"| {p['segmento']} | {p['perfil']} | {p['prioridade']} |")
    
    return "\n".join(lines)


def template_requisitos_funcionais(extracted: Dict) -> str:
    """Template para ## Requisitos Funcionais"""
    rfs = extracted.get("rfs", [])
    if not rfs:
        rfs = [{"id": "RF-01", "req": "[Extraído do PRD]", "criterio": "[A validar]", 
                "prioridade": "Must", "complexidade": "Média"}]
    
    lines = ["## Requisitos Funcionais\n"]
    lines.append("| ID | Requisito | Critério de Aceite | Prioridade | Complexidade |")
    lines.append("|---|---|---|---|---|")
    for rf in rfs:
        lines.append(f"| {rf['id']} | {rf['req']} | {rf['criterio']} | {rf['prioridade']} | {rf['complexidade']} |")
    
    return "\n".join(lines)

# ... funções análogas para ADRs, Segurança, Métricas, Plano, Decisões (7 prioritárias)
# ... + template_stub() para as 13 restantes
```

### 6.1 Extratores de Dados para Templates Nível 3

Novos extratores em `context_extractors.py` ou como métodos do `RetryOrchestrator`:

```python
def extract_personas_from_prd(prd: str) -> List[Dict]:
    """Extrai personas da tabela de Público-Alvo do PRD original."""

def extract_rfs_from_prd(prd: str) -> List[Dict]:
    """Extrai RFs da tabela de Requisitos Funcionais do PRD original."""

def extract_adrs_from_design(system_design: str) -> List[Dict]:
    """Extrai ADRs do system_design."""

def extract_threats_from_security(security_review: str) -> List[Dict]:
    """Extrai ameaças STRIDE do security_review."""

def extract_decisions_from_debate(debate: str) -> List[Dict]:
    """Extrai decisões da tabela de Decisões Aplicáveis."""

def extract_phases_from_plan(plan: str) -> List[Dict]:
    """Extrai fases do development_plan."""

def extract_metrics_from_prd(prd: str) -> List[Dict]:
    """Extrai métricas de sucesso do PRD original."""
```

---

## 7. Integração com `product_manager_agent.py`

### Posição exata no código

O `RetryOrchestrator.recover()` deve ser chamado **entre** a geração seccional (linha 165) e a contagem de falhas para a Cláusula (linha 172). Assim a Cláusula contará `failed_sections = 0` após recovery bem-sucedido.

### Modificação no método `consolidate_prd()`

```python
def consolidate_prd(self, artifacts_context: str, original_idea: str = "") -> str:
    # ... código existente: parse + geração via SectionalGenerator ...
    
    # Linha 126: parsed = self._parse_artifact_sections(artifacts_context)
    # Linha 161: result = generator.generate_sectional_with_inputs(...)
    
    if result:
        # ═══ FASE 9.6: Retry Inteligente ═══
        # POSIÇÃO: ENTRE linha 166 e linha 172 do código atual
        # ANTES da contagem de [GERAÇÃO FALHOU] para a Cláusula
        if "[GERAÇÃO FALHOU" in result:
            from src.core.retry_orchestrator import RetryOrchestrator
            
            orchestrator = RetryOrchestrator(
                provider=self.provider,
                direct_mode=self.direct_mode
            )
            
            # IMPORTANTE: Reusar o dict 'parsed' que já foi construído na linha 126
            # NÃO fazer novo parse — as chaves dependem dos delimitadores
            # '--- ARTEFATO: [NOME] ---' do planner
            result = orchestrator.recover(result, parsed)
            
            # Log de recuperação
            for entry in orchestrator.get_recovery_log():
                self._emit(
                    f"  Seção '{entry['heading']}' recuperada via Nível {entry['level_used']} "
                    f"({entry['chars_recovered']} chars)"
                )
        # ═══ FIM FASE 9.6 ═══
        
        # Linha 172: count_failed = result.count("[GERAÇÃO FALHOU]")
        # Agora count_failed será 0 se recovery funcionou
        # ... Cláusula de Integridade (código existente) ...
```

---

## 8. Lógica do Prompt Nível 2

### 8.1 Estrutura do Prompt

```
System: {CONSOLIDATOR_DIRECTIVE}

TAREFA CIRÚRGICA: Gere APENAS a seção "{heading}".
NÃO gere nenhuma outra seção. NÃO inclua introdução ou conclusão.
Comece diretamente com o heading ##.

CONTEXTO DO PROJETO:
{trecho_relevante_do_artefato_fonte}  (máx 800 chars)

REFERÊNCIA DE FORMATO E PROFUNDIDADE:
{exemplar_correspondente}

SEÇÕES JÁ GERADAS (para contexto, NÃO repita):
{resumo_das_seções_que_já_passaram}  (máx 400 chars)

INSTRUÇÕES ESPECÍFICAS:
- {instrução_original_do_pass}
- Mínimo {min_words} palavras
- Tabelas devem ter pelo menos {min_items} linhas de dados

GERE A SEÇÃO AGORA:
```

### 8.2 Diferenças em relação ao Nível 1

| Aspecto | Nível 1 (existente) | Nível 2 (novo) |
|---|---|---|
| Prompt | Mesmo + instrução corretiva | Completamente reescrito |
| Foco | Multi-seção (pass original) | Seção individual |
| Contexto | Budget fixo do pass | Contexto enriquecido por seção |
| Exemplo | Via `_get_exemplar()` | Inline no prompt |
| Temperature | 0.1 (hardcoded) | 0.1 (mesma — sem suporte a override) |
| max_tokens | Original do pass | +50% |
| Tentativas | 3 | 2 |

---

## 9. Deduplicação Automática (W2-03)

### Onde vive
Método `_check_deduplication()` no `RetryOrchestrator`.

### Lógica
Antes de gerar qualquer seção via Nível 2 ou 3:
1. Extrair o **conteúdo** (corpo) de cada seção do PRD_FINAL
2. Comparar via Jaccard de n-grams (bigrams) entre o conteúdo da seção a ser gerada e todas as outras
3. Se overlap > 60%, pular geração e usar referência cruzada: "Ver seção [Nome]"
4. Se não, prosseguir com geração

**NOTA**: Duplicação por heading já é impedida pelo `_validate_passes_config()` da Fase 9.5.3. Aqui verificamos duplicação de **conteúdo** entre seções com nomes diferentes.

```python
def _check_deduplication(self, heading: str, new_content: str, prd_final: str) -> Optional[str]:
    """
    Verifica se o CONTEÚDO da seção já existe em outra parte do PRD.
    Compara corpo (não headings) via Jaccard de bigrams.
    Retorna heading da seção duplicada, ou None.
    """
    sections = self._split_sections(prd_final)
    new_bigrams = self._extract_bigrams(new_content)
    
    for other_heading, other_content in sections.items():
        if other_heading == heading:
            continue
        other_bigrams = self._extract_bigrams(other_content)
        if self._jaccard_similarity(new_bigrams, other_bigrams) > 0.6:
            return other_heading
    return None

def _extract_bigrams(self, text: str) -> set:
    """Extrai conjunto de bigrams (pares de palavras consecutivas) do texto."""
    words = text.lower().split()
    return {(words[i], words[i+1]) for i in range(len(words) - 1)} if len(words) > 1 else set()

def _jaccard_similarity(self, set_a: set, set_b: set) -> float:
    """Calcula similaridade de Jaccard entre dois conjuntos."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)
```

---

## 10. Testes

### 10.1 `test_retry_orchestrator.py` — Testes Unitários

```python
class TestRetryOrchestrator:
    
    def test_detect_failed_sections_finds_markers(self):
        """Detecta seções com [GERAÇÃO FALHOU]."""
    
    def test_detect_failed_sections_empty_prd(self):
        """PRD sem falhas retorna lista vazia."""
    
    def test_recover_no_failures_returns_unchanged(self):
        """PRD sem falhas passa sem modificação."""
    
    def test_level_3_never_returns_empty(self):
        """Nível 3 sempre retorna conteúdo válido."""
    
    def test_level_3_publico_alvo_with_data(self):
        """Template de Público-Alvo preenche com dados extraídos."""
    
    def test_level_3_publico_alvo_without_data(self):
        """Template de Público-Alvo usa fallback quando sem dados."""
    
    def test_replace_section_preserves_others(self):
        """Substituição de seção não afeta seções adjacentes."""
    
    def test_recovery_log_records_level(self):
        """Log registra nível usado para cada seção."""
    
    def test_deduplication_detects_overlap(self):
        """Deduplicação identifica conteúdo similar."""
    
    def test_full_recovery_pipeline(self):
        """Teste E2E: PRD com 3 falhas → 0 falhas após recovery."""
```

### 10.2 `test_retry_templates.py` — Testes dos Templates

```python
class TestRetryTemplates:
    
    def test_each_template_returns_valid_markdown(self):
        """Todos os 20 templates retornam Markdown com heading ##."""
    
    def test_each_template_handles_empty_data(self):
        """Templates funcionam com dict vazio."""
    
    def test_template_publico_alvo_has_table(self):
        """Template de Público-Alvo contém tabela com |---|."""
    
    def test_template_rfs_has_minimum_rows(self):
        """Template de RFs gera pelo menos 1 linha de dados."""
```

---

## 11. Critérios de Aceite

| ID | Critério | Verificação |
|---|---|---|
| CA-01 | `RetryOrchestrator` implementado com 3 níveis | Código em `src/core/retry_orchestrator.py` |
| CA-02 | Nível 3 NUNCA retorna vazio para nenhuma das 20 seções | Teste unitário `test_level_3_never_returns_empty` |
| CA-03 | Taxa de retry < 20% (máx 4 de 20 passes precisam Nível 2+) | Medição em 3 execuções |
| CA-04 | `is_clean: True` em 3 execuções consecutivas com gpt-oss:20b-cloud | Log de execução |
| CA-05 | Zero seções com `[GERAÇÃO FALHOU]` no PRD_FINAL pós-recovery | Análise do consistency_report |
| CA-06 | Zero seções duplicadas no PRD_FINAL | Teste de deduplicação |
| CA-07 | Log indica nível usado para cada seção recuperada | `get_recovery_log()` |
| CA-08 | Todos os testes unitários novos passam | `pytest tests/test_retry_*.py` |
| CA-09 | 140+ testes de regressão continuam passando | `pytest tests/` |
| CA-10 | PRD_FINAL >= 25.000 caracteres pós-recovery | Análise de tamanho |

---

## 12. Plano de Implementação (Ordem Corrigida)

> **Princípio**: Nível 3 (safety net) primeiro, porque o Nível 2 precisa de um fallback funcional.
> A ordem é: Templates → Infraestrutura → Nível 2 → Integração → Certificação.

---

### Fase 9.6a — Nível 3: Templates Estáticos + Extratores

**Checklist:**
- [ ] Criar `src/core/retry_templates.py`
- [ ] Implementar 7 templates prioritários (Público-Alvo, RFs, ADRs, Segurança, Métricas, Plano, Decisões)
- [ ] Implementar `template_stub()` para as 13 seções restantes
- [ ] Criar 7 extratores em `context_extractors.py` (personas, RFs, ADRs, threats, decisions, phases, metrics)
- [ ] Criar `tests/test_retry_templates.py`
- [ ] Teste: cada template retorna Markdown com heading `##` e nunca retorna vazio
- [ ] Teste: cada template funciona com `extracted = {}` (dict vazio)

**Critério de Fechamento 9.6a:**
- ✅ 7 templates prioritários retornam conteúdo válido com dados reais
- ✅ 13 stubs retornam heading + mensagem padrão
- ✅ Todos os testes de `test_retry_templates.py` passam
- ✅ Zero chamadas LLM nos templates

---

### Fase 9.6b — Infraestrutura do Orquestrador

**Checklist:**
- [ ] Criar `src/core/retry_orchestrator.py` com classe `RetryOrchestrator`
- [ ] Implementar `_detect_failed_sections()` — encontra marcadores `[GERAÇÃO FALHOU]`
- [ ] Implementar `_replace_section()` — substitui seção no PRD preservando adjacentes
- [ ] Implementar `_retry_level_3()` — chama templates + extratores
- [ ] Implementar `get_recovery_log()` — log de auditoria
- [ ] Implementar `recover()` — fluxo principal (apenas L3 nesta fase)
- [ ] Criar `tests/test_retry_orchestrator.py` com testes de detecção, substituição e L3

**Critério de Fechamento 9.6b:**
- ✅ `_detect_failed_sections()` encontra todas as seções com marcador em PRD de teste
- ✅ `_replace_section()` substitui sem corromper markdown adjacente
- ✅ `recover()` com apenas L3 elimina 100% dos `[GERAÇÃO FALHOU]` em PRD sintético
- ✅ `recovery_log` registra `level_used: 3` para cada seção
- ✅ Testes de regressão (140+) continuam passando

---

### Fase 9.6c — Nível 2: Prompt Reformulado

**Checklist:**
- [ ] Implementar `_retry_level_2()` com prompt cirúrgico (seção 8 do blueprint)
- [ ] Implementar seleção de exemplar via `SECTION_RECOVERY_MAP`
- [ ] Implementar injeção de contexto enriquecido via `context_extractors`
- [ ] `max_output_tokens` = 150% do pass original
- [ ] Atualizar `recover()` para tentar L2 antes de cair para L3
- [ ] Testes com mock do provider simulando sucesso e falha do L2

**Critério de Fechamento 9.6c:**
- ✅ L2 com mock recupera pelo menos 3 de 7 seções falhadas
- ✅ L2 que falha cai corretamente para L3 (sem exceção, sem dado perdido)
- ✅ `recovery_log` registra `level_used: 2` ou `level_used: 3` corretamente
- ✅ Testes de regressão continuam passando

---

### Fase 9.6d — Integração + Deduplicação

**Checklist:**
- [ ] Integrar `RetryOrchestrator` no `consolidate_prd()` (posição: entre L166 e L172)
- [ ] Passar `parsed` dict existente (não recriar)
- [ ] Implementar `_check_deduplication()` com Jaccard de bigrams no conteúdo
- [ ] Implementar `_extract_bigrams()` e `_jaccard_similarity()`
- [ ] Teste de deduplicação falso-positivo (seções diferentes com conteúdo similar)
- [ ] Executar 1 run completa com gpt-oss:20b-cloud

**Critério de Fechamento 9.6d:**
- ✅ PRD_FINAL pós-recovery tem 0 ocorrências de `[GERAÇÃO FALHOU]`
- ✅ Cláusula de Integridade reporta `failed_sections = 0`
- ✅ Zero seções duplicadas no PRD_FINAL
- ✅ Recovery log mostra níveis usados para cada seção

---

### Fase 9.6e — Certificação Final

**Checklist:**
- [ ] Rodar suite completa de testes (150+)
- [ ] Executar 3 runs consecutivas com gpt-oss:20b-cloud
- [ ] Verificar `is_clean: True` em todas as 3 runs
- [ ] Verificar PRD_FINAL >= 25.000 chars em todas
- [ ] Capturar recovery_log das 3 runs
- [ ] Calcular taxa de retry (target: < 20%)
- [ ] Executar ARCHIVING_PROTOCOL
- [ ] Atualizar CURRENT_STATE.md e BACKLOG_FUTURO.md

**Critério de Fechamento 9.6e (= Onda 2 CONCLUÍDA):**
- ✅ `is_clean: True` em 3 execuções consecutivas
- ✅ Taxa de retry < 20% (máx 4 de 20 passes precisam L2+)
- ✅ PRD_FINAL >= 25.000 chars em todas as runs
- ✅ Zero `[GERAÇÃO FALHOU]` em todas as runs
- ✅ 150+ testes passando

---

## 13. Riscos e Mitigações

| ID | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|
| R-01 | Nível 2 consome muitos tokens/tempo | Média | Médio | Limitar a 2 tentativas; timeout de 60s por seção |
| R-02 | Templates Nível 3 ficam genéricos demais | Média | Baixo | Extratores enriquecidos; aceitar que Nível 3 é safety net, não golden |
| R-03 | Substituição de seção corrompe markdown adjacente | Baixa | Alto | Regex robusto com testes; preservar \n\n entre seções |
| R-04 | Deduplicação falso-positivo remove seção válida | Baixa | Alto | Threshold alto (>80% similarity); log de ação para auditoria |
| R-05 | Tempo total do pipeline aumenta significativamente | Média | Médio | Nível 2 só executa para seções falhadas (~3-5 de 20) |

---

## 14. Decisões Arquiteturais

| ID | Decisão | Alternativa Rejeitada | Motivo |
|---|---|---|---|
| D-01 | RetryOrchestrator como classe separada (não inline no SectionalGenerator) | Adicionar níveis no `_execute_pass_with_retry` | Separação de responsabilidades; o SectionalGenerator não deve conhecer templates estáticos |
| D-02 | Nível 3 não usa LLM | Usar LLM com prompt simplificado | Garantia de determinismo; zero custo de inferência; NUNCA falha |
| D-03 | Recovery acontece pós-geração completa (não durante) | Retry inline entre passes | Permite visão global; evita reprocessar passes que já passaram |
| D-04 | Cada seção é recuperada independentemente | Regenerar passes inteiros (multi-seção) | Granularidade; economia de tokens; foco cirúrgico |
| D-05 | Templates Nível 3 são funções Python (não strings) | Templates como constantes string | Funções permitem lógica condicional de preenchimento |

---

## 15. Métricas de Sucesso da Fase 9.6

| Métrica | Target | Como Medir |
|---|---|---|
| Taxa de seções com `[GERAÇÃO FALHOU]` pós-recovery | 0% | `grep "GERAÇÃO FALHOU" prd_final` |
| `is_clean` em 3 runs consecutivos | `True` | consistency_report |
| Taxa de uso do Nível 2 | < 35% das seções | recovery_log |
| Taxa de uso do Nível 3 | < 10% das seções | recovery_log |
| Tempo adicional de pipeline | < 120s | timestamp logs |
| PRD_FINAL chars pós-recovery | >= 25.000 | `len(prd_final)` |
| Testes passando | 150+ | `pytest tests/` |

---

*Blueprint gerado para Fase 9.6 — IdeaForge CLI*
*Preparado em: 02/04/2026*
*Revisado em: 02/04/2026 — 5 correções técnicas + checklists por sub-fase*
*Próxima ação: Implementar Fase 9.6a (Templates Estáticos + Extratores)*