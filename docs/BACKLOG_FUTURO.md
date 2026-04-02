# BACKLOG ESTRATÉGICO — IdeaForge CLI

## Intenção Original
- **Objetivo:** Fazer o IdeaForge gerar PRDs completos, estruturalmente válidos e portáveis entre modelos de 1B a 20B+ parâmetros
- **Estado Atual:** ~29.400 chars com completude 100%, 5 seções com [GERAÇÃO FALHOU], is_clean: False
- **Meta Final:** ~140.000 chars com fichas técnicas, JSON funcional, Mermaid, SQL, guias autocontidos
- **Modelo Alvo Primário:** 20B parâmetros (gpt-oss:20b-cloud)
- **Modelo Alvo Portabilidade:** 1B-3B parâmetros (Qwen 2.5, Phi-3 mini, gemma3:1b)
- **Estratégia:** Decomposição em micro-tarefas com orquestração inteligente e retry em múltiplas camadas, garantindo completude estrutural independente do modelo

---

## Onda 1 — Quick Wins (Fase 9.5)

| ID | Técnica | Descrição | Arquivos Impactados | Critério de Aceite | Status |
|---|---|---|---|---|---|
| W1-01 | Exemplar Injection | Extrair seções do PRD OmniPrice (padrão ouro) como few-shot exemplar por pass. Cada pass recebe a seção correspondente do gold-standard como referência de profundidade | `sectional_generator.py`, novo diretório `src/core/exemplars/` | Cada pass de NEXUS_FINAL_PASSES tem campo `exemplar_file` apontando para arquivo em `exemplars/`. Output por seção >= 2x o tamanho atual | CONCLUÍDO |
| W1-02 | Word Count Targets | Pass 0 gera outline com meta de palavras por seção. Cada pass subsequente recebe instrução "esta seção deve ter pelo menos X palavras com Y itens" | `sectional_generator.py`, `product_manager_agent.py` | Outline gerado contém word count target para cada seção. Soma dos targets >= 25.000 palavras (~100.000 chars) | CONCLUÍDO |
| W1-03 | SectionQualityChecker | Checker programático (sem LLM) que valida min_items, required_fields e min_length por tipo de seção. Integrado ao loop de retry com feedback específico | Novo: `src/core/section_quality_checker.py`. Modificado: `sectional_generator.py` | Cada seção tem regras definidas (ex: Riscos min 10 itens com 5 campos). Seção que falha recebe feedback e é regenerada. Zero seções abaixo do threshold após pipeline | CONCLUÍDO |
| W1-04 | Remoção de Duplicatas | Remover passagens duplicadas (skeleton+flesh redundantes) no NEXUS_FINAL_PASSES e adicionar guarda de validação contra duplicatas futuras | `sectional_generator.py` | Zero seções duplicadas no PRD_FINAL. `_validate_passes_config()` bloqueia duplicatas | CONCLUÍDO |
| W1-05 | Critic com Resumo | Critic recebe resumo de ~800 tokens do PRD em vez do documento completo, com extração determinística por seções-chave | `critic_agent.py` | PRD_REVIEW com conteúdo válido (não EMPTY_CONTENT). Input do Critic <= 4000 chars | CONCLUÍDO |

### Meta da Onda 1
- **Chars esperados:** 35.000-50.000
- **Critério binário:** `is_clean: True` E zero `[GERAÇÃO FALHOU]` E zero seções duplicadas
- **Status:** CONCLUÍDO — Onda 1 finalizada com exemplares e QualityChecker recalibrados.

---

## Onda 1b — Micro-Tarefas Cirúrgicas (Fase 9.5.3)

| ID | Técnica | Descrição | Arquivos Impactados | Critério de Aceite | Status |
|---|---|---|---|---|---|
| W1b-01 | Extratores de Contexto Mínimo | Para cada seção que falha, criar extrator que puxa apenas o trecho relevante do artefato-fonte em no máximo 400 tokens. Arquitetura e Tech Stack ← tabela tech stack do system_design. Plano de Implementação ← fases do development_plan. Decisões do Debate ← tabela síntese do debate_transcript. Guia de Replicação ← dependências + ambiente do development_plan. Cláusula de Integridade ← template estático com metadados do pipeline | Novo: `src/core/context_extractors.py`. Modificado: `sectional_generator.py` | 5 seções que falhavam agora geram conteúdo válido. Input de cada passagem <= 600 tokens | CONCLUÍDO |
| W1b-02 | Fix Consistency Checker Sub-Headers | Ajustar contagem de conteúdo para incluir sub-headers `###` na medição de chars por seção. ADRs deixa de ser marcado como THIN | `consistency_checker.py` (ou equivalente) | Seção ADRs com 7 ADRs não é mais marcada como THIN_SECTIONS. Contagem inclui conteúdo sob `###` | CONCLUÍDO |
| W1b-03 | Fix PRD_REVIEW Headers | Ajustar prompt do Critic para gerar os headers NEXUS esperados pelo validator (`## Score de Qualidade`, `## Issues Identificadas`, `## Verificação de Requisitos`, `## Sumário`, `## Recomendação`) | `critic_agent.py` | PRD_REVIEW passa na validação com completude >= 60%. Headers NEXUS presentes no output | CONCLUÍDO |
| W1b-04 | Remoção de Duplicatas Remanescentes | Remover passagens que geram "Métricas de Sucesso" e "Limitações Conhecidas" duas vezes no PRD_FINAL | `sectional_generator.py` — NEXUS_FINAL_PASSES | Zero seções duplicadas no PRD_FINAL. Cada header `##` aparece exatamente uma vez | CONCLUÍDO |
| W1b-05 | Fix PLACEHOLDER_HEAVY | Ajustar prompts das passagens de dependências técnicas para preencher coluna "Alternativa" em vez de "A DEFINIR", ou marcar "N/A" quando não aplicável | `sectional_generator.py` — prompts das passagens de dependências | Validação PLACEHOLDER_HEAVY não dispara. Menos de 10% dos campos com "A DEFINIR" | CONCLUÍDO |

### Meta da Onda 1b
- **Chars esperados:** 29.000-35.000 (foco é completude, não volume)
- **Critério binário:** `is_clean: True` E zero `[GERAÇÃO FALHOU]` E zero seções duplicadas E PRD_REVIEW validado
- **Pré-requisito:** W1-04 e W1-05 concluídos
- **Status:** CONCLUÍDO — Onda 1b concluída e certificada com gpt-oss:20b-cloud. Bug de assembly resolvido.

---

## Onda 2 — Orquestração com Retry Inteligente (Fase 9.6)

| ID | Técnica | Descrição | Arquivos Impactados | Critério de Aceite | Status |
|---|---|---|---|---|---|
| W2-01 | Retry com Validador Acoplado | Cada micro-tarefa recebe validador que checa: conteúdo existe, tamanho mínimo, tabelas têm colunas certas, sem placeholders, sem repetição de outra seção. Falha dispara retry com feedback | Novo: `src/core/task_validator.py`. Modificado: `sectional_generator.py` | Cada micro-tarefa tem validador. Taxa de retry < 20% (max 1 em 5 precisa segunda tentativa) | PENDENTE |
| W2-02 | Retry Escalonado em 3 Níveis | Nível 1: mesmo prompt, retry simples. Nível 2: prompt reformulado com exemplo inline. Nível 3: fallback para template estático preenchido com dados extraídos | Novo: `src/core/retry_orchestrator.py` | 3 níveis implementados. Nível 3 (fallback) garante que nenhuma seção fica vazia. Log indica qual nível foi usado | PENDENTE |
| W2-03 | Deduplicação Automática | Antes de gerar qualquer seção, orquestrador verifica se conteúdo equivalente já foi gerado em outra passagem e pula se redundante | `sectional_generator.py`, `retry_orchestrator.py` | Zero seções duplicadas em 3 execuções consecutivas | PENDENTE |
| W2-04 | Skeleton-then-Flesh Sistematizado | Para seções críticas (Riscos, ADRs, Componentes, Extensibilidade, Guia de Replicação): Pass A gera outline com 12-15 bullet points; Pass B expande cada bullet em parágrafo detalhado | `sectional_generator.py` — passes de outline+expansão | Seções críticas têm outline >= 12 pontos. Expansão produz >= 3.000 chars por seção crítica | PENDENTE |

### Meta da Onda 2
- **Chars esperados:** 50.000-70.000
- **Critério binário:** `is_clean: True` em 3 execuções consecutivas com modelo 20B E taxa de retry < 20%
- **Pré-requisito:** Onda 1b concluída (is_clean: True estável)
- **Status:** PENDENTE

---

## Onda 3 — Portabilidade de Modelo (Fase 9.7)

| ID | Técnica | Descrição | Arquivos Impactados | Critério de Aceite | Status |
|---|---|---|---|---|---|
| W3-01 | Calibração de Prompts por Faixa | Criar perfis de prompt por tamanho de modelo: 1B (prompts <= 300 tokens, 2 exemplos inline), 3B (prompts <= 500 tokens, 1 exemplo), 20B+ (prompts descritivos <= 1200 tokens) | Novo: `src/core/prompt_profiles.py`. Modificado: `sectional_generator.py` | 3 perfis de prompt funcionais. Seleção automática baseada no modelo configurado | PENDENTE |
| W3-02 | Teste com Modelo 3B | Rodar pipeline completo com Qwen 2.5 de 3B. Medir taxa de sucesso na primeira tentativa, taxa de retry e taxa de fallback por seção | Configuração de modelo | is_clean: True com modelo 3B. Taxa de fallback < 30% | PENDENTE |
| W3-03 | Teste com Modelo 1B-1.5B | Rodar pipeline com Qwen 2.5 de 1.5B ou gemma3:1b. Aceitar menor qualidade textual desde que estrutura seja válida | Configuração de modelo | is_clean: True com modelo 1.5B. PRD_FINAL estruturalmente completo mesmo que texto seja menos elaborado | PENDENTE |
| W3-04 | Micro-Tarefas Atômicas | Decompor passagens que ainda falham em modelos pequenos em unidades menores: uma chamada por linha de tabela, um parágrafo por chamada. Montagem final por código | `sectional_generator.py`, `context_extractors.py` | Nenhuma chamada individual requer mais de 500 tokens de output. Modelo 1B consegue gerar cada fragmento | PENDENTE |

### Meta da Onda 3
- **Chars esperados:** 35.000-50.000 com modelo 1B, 70.000+ com modelo 20B
- **Critério binário:** `is_clean: True` com modelo de 3B E `is_clean: True` com modelo de 1.5B
- **Pré-requisito:** Onda 2 concluída (orquestração com retry estável)
- **Status:** PENDENTE

---

## Onda 4 — Qualidade de Conteúdo (Fase 9.8)

| ID | Técnica | Descrição | Arquivos Impactados | Critério de Aceite | Status |
|---|---|---|---|---|---|
| W4-01 | Consistência Cruzada | Validador que verifica: RF-IDs do Escopo MVP existem na tabela de RFs, ADR-IDs do development plan existem nos ADRs, tecnologias mencionadas são consistentes entre seções | Novo: `src/core/cross_reference_validator.py` | Zero inconsistências cruzadas detectadas. RF-IDs, ADR-IDs e tecnologias consistentes | PENDENTE |
| W4-02 | Critique-and-Expand | Após gerar seção, pass de critique: "O que um engenheiro sênior acharia insuficiente?" Gera lista de gaps. Pass de expansão regenera incorporando respostas | `sectional_generator.py`, `critic_agent.py` | 5-7 seções passam por ciclo critique→expand. Cada ciclo adiciona >= 30% de conteúdo | PENDENTE |
| W4-03 | Chain-of-Density | Passes de densificação: "Adicione exemplos concretos, valores numéricos, edge cases, formatos de dados específicos" aplicados a 5 seções-chave | `sectional_generator.py` | Seções densificadas contêm >= 5 exemplos concretos cada. Zero campos genéricos | PENDENTE |

### Meta da Onda 4
- **Chars esperados:** 85.000-110.000
- **Critério binário:** `is_clean: True` E zero inconsistências cruzadas E density >= 0.95 em todas as seções
- **Pré-requisito:** Onda 3 concluída (portabilidade validada)
- **Status:** PENDENTE

---

## Onda 5 — Riqueza Técnica (Fase 9.9)

| ID | Técnica | Descrição | Arquivos Impactados | Critério de Aceite | Status |
|---|---|---|---|---|---|
| W5-01 | Passes de Artefatos | Passes dedicados para: diagramas Mermaid (sequence, state, flowchart), schema SQL com constraints, exemplos JSON funcionais, guia bash de replicação, glossário técnico | `sectional_generator.py` — 6 passes novos | PRD contém >= 3 diagramas Mermaid válidos, >= 1 schema SQL, >= 3 blocos JSON funcionais | PENDENTE |
| W5-02 | Cross-Reference + Assembly | Pass final que adiciona referências cruzadas entre seções, verifica consistência terminológica e gera ToC com links | `sectional_generator.py`, `product_manager_agent.py` | PRD contém ToC funcional. >= 10 referências cruzadas. Terminologia consistente | PENDENTE |

### Meta da Onda 5
- **Chars esperados:** 100.000-140.000
- **Critério binário:** `len(prd_final) >= 100.000` E `is_clean: True` E `>= 3 diagramas Mermaid` E `>= 1 schema SQL`
- **Pré-requisito:** Onda 4 concluída
- **Status:** PENDENTE

---

## Onda 6 — Hardening e Produção (Fase 10.0)

| ID | Técnica | Descrição | Arquivos Impactados | Critério de Aceite | Status |
|---|---|---|---|---|---|
| W6-01 | Stress Test | 20 execuções consecutivas medindo taxa de sucesso, tempo médio e consumo de recursos. Validação com 3 modelos diferentes (1B, 3B, 20B) | Scripts de teste | Taxa de sucesso >= 95% em 20 runs. Tempo médio documentado por modelo | PENDENTE |
| W6-02 | Documentação Completa | Diagramas de fluxo do pipeline, guia de configuração, guia de contribuição, README atualizado | `docs/` | README com quickstart funcional. Diagrama de pipeline atualizado. Guia de configuração por modelo | PENDENTE |
| W6-03 | CLI Polida | Flags para escolher modelo, nível de verbosidade, modo de fallback, dry run. Exportação em Markdown, PDF e JSON estruturado | `src/cli/`, `src/main.py` | `--model`, `--verbose`, `--fallback-mode`, `--dry-run`, `--format` funcionais | PENDENTE |
| W6-04 | Versão 1.0 | Tag de release, changelog, licença, publicação | Raiz do projeto | Tag v1.0.0 no repositório. CHANGELOG.md completo | PENDENTE |

### Meta da Onda 6
- **Critério binário:** Sistema completo, testado, documentado, portável entre modelos 1B-20B+
- **Pré-requisito:** Onda 5 concluída
- **Status:** PENDENTE

---

## Referências Técnicas

| Técnica | Paper/Fonte | Relevância |
|---|---|---|
| AgentWrite (LongWriter) | THUDM/LongWriter — Tsinghua/THUNLP 2024 | Outline com word count targets |
| STORM | stanford-oval/storm — Stanford 2024 | Multi-perspectiva para densidade |
| Skeleton-of-Thought | Xuefei Ning et al. 2023 — Microsoft Research Asia | Expansão paralela por seção |
| Self-Refine | Aman Madaan et al. 2023 — CMU | Auto-refinamento iterativo |
| Chain-of-Density | Griffin Adams et al. 2023 — MIT/Columbia | Densificação iterativa |
| Scaling Test-Time Compute | Snell et al. 2024 — UC Berkeley | N chamadas 20B >= 1 chamada 70B |
| Verifier-Guided Generation | AlphaCode / Constitutional AI | Checklist verificável por seção |
| RecurrentGPT | Wangchunshu Zhou et al. 2023 | Memória curto/longo prazo entre passes |
| Model as Function | Padrão emergente 2024-2025 | Modelo como executor de micro-tarefas, inteligência na orquestração |

---

## Mapa de Fases

| Fase | Onda | Foco | Modelo Mínimo | Critério de Saída |
|---|---|---|---|---|
| 9.5 | Onda 1 | Quick wins estruturais | 20B | Correções base implementadas |
| 9.5.3 | Onda 1b | Micro-tarefas cirúrgicas | 20B | `is_clean: True` estável |
| 9.6 | Onda 2 | Orquestração com retry | 20B | `is_clean: True` em 3 runs consecutivos, retry < 20% |
| 9.7 | Onda 3 | Portabilidade de modelo | 1B-3B | `is_clean: True` com modelo 1.5B |
| 9.8 | Onda 4 | Qualidade de conteúdo | 3B+ | Zero inconsistências cruzadas, density >= 0.95 |
| 9.9 | Onda 5 | Riqueza técnica | 3B+ | >= 100k chars, Mermaid, SQL, JSON |
| 10.0 | Onda 6 | Hardening e produção | 1B+ | v1.0.0 release |

---

## Regras do Backlog
1. Itens movem de `PENDENTE` para `CONCLUÍDO` apenas após validação com critério binário
2. Cada Onda corresponde a uma Fase numerada
3. Nenhuma Onda inicia sem a anterior concluída
4. Novas técnicas descobertas são adicionadas como Onda 7+
5. Portabilidade de modelo (Onda 3) valida que a arquitetura não depende de capacidade do modelo
6. O modelo é executor de micro-tarefas; a inteligência está na orquestração