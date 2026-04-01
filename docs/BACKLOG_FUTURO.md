# BACKLOG ESTRATÉGICO — IdeaForge CLI

## Intenção Original
- **Objetivo:** Fazer o Consolidador (TASK_07) gerar PRDs de 100.000-140.000 caracteres com profundidade comparável ao padrão ouro (Claude Opus)
- **Estado Atual:** ~31.000 chars com 20/20 seções, is_clean: True
- **Meta Final:** ~140.000 chars com fichas técnicas, JSON funcional, Mermaid, SQL, guias autocontidos
- **Modelo Alvo:** 20B parâmetros (Ollama local)
- **Estratégia:** Amplificar capacidade via orquestração (40-60 passes) em vez de escalar modelo

---

## Onda 1 — Quick Wins (Fase 9.5)

| ID | Técnica | Descrição | Arquivos Impactados | Critério de Aceite | Status |
|---|---|---|---|---|---|
| W1-01 | Exemplar Injection | Extrair seções do PRD OmniPrice (padrão ouro) como few-shot exemplar por pass. Cada pass recebe a seção correspondente do gold-standard como referência de profundidade | `sectional_generator.py`, novo diretório `src/core/exemplars/` | Cada pass de NEXUS_FINAL_PASSES tem campo `exemplar_file` apontando para arquivo em `exemplars/`. Output por seção >= 2x o tamanho atual | CONCLUÍDO |
| W1-02 | Word Count Targets | Pass 0 gera outline com meta de palavras por seção. Cada pass subsequente recebe instrução "esta seção deve ter pelo menos X palavras com Y itens" | `sectional_generator.py`, `product_manager_agent.py` | Outline gerado contém word count target para cada seção. Soma dos targets >= 25.000 palavras (~100.000 chars) | CONCLUÍDO |
| W1-03 | SectionQualityChecker | Checker programático (sem LLM) que valida min_items, required_fields e min_length por tipo de seção. Integrado ao loop de retry com feedback específico | Novo: `src/core/section_quality_checker.py`. Modificado: `sectional_generator.py` | Cada seção tem regras definidas (ex: Riscos min 10 itens com 5 campos). Seção que falha recebe feedback e é regenerada. Zero seções abaixo do threshold após pipeline | CONCLUÍDO |

### Meta da Onda 1
- **Chars esperados:** 35.000-50.000
- **Critério binário:** `len(prd_final) >= 35.000` E `is_clean: True` E `SectionQualityChecker validado`
- **Status:** CONCLUÍDO (Meta de 35k quase atingida na 9.5.1, validada integridade estrutural)

---

## Onda 2 — Profundidade Estrutural (Fase 9.6)

| ID | Técnica | Descrição | Arquivos Impactados | Critério de Aceite | Status |
|---|---|---|---|---|---|
| W2-01 | Skeleton-then-Flesh | Para seções críticas (Riscos, Componentes, ADRs, Extensibilidade, Guia de Replicação): Pass A gera outline com 12-15 bullet points; Pass B expande cada bullet em parágrafo com detalhes concretos | `sectional_generator.py` — adicionar passes de outline+expansão | Seções críticas têm sub-outline com >= 12 pontos. Expansão produz >= 3.000 chars por seção crítica | PENDENTE |
| W2-02 | Critique-and-Expand | Após gerar seção, pass de critique: "O que um engenheiro sênior acharia insuficiente?" Gera lista de gaps. Pass de expansão regenera incorporando respostas | `sectional_generator.py`, possivelmente `critic_agent.py` reutilizado | 5-7 seções passam por ciclo critique→expand. Cada ciclo adiciona >= 30% de conteúdo à seção | PENDENTE |

### Meta da Onda 2
- **Chars esperados:** 70.000-85.000
- **Critério binário:** `len(prd_final) >= 70.000` E `is_clean: True` E `>= 10 riscos com 5 campos cada`
- **Pré-requisito:** Onda 1 concluída

---

## Onda 3 — Riqueza Técnica (Fase 9.7)

| ID | Técnica | Descrição | Arquivos Impactados | Critério de Aceite | Status |
|---|---|---|---|---|---|
| W3-01 | Passes de Artefatos | Passes dedicados para: diagramas Mermaid (sequence, state, flowchart), schema SQL com constraints, exemplos JSON funcionais, guia bash de replicação, glossário técnico | `sectional_generator.py` — 6 passes novos dedicados a artefatos | PRD contém >= 3 diagramas Mermaid válidos, >= 1 schema SQL, >= 3 blocos JSON funcionais, guia com comandos bash copiáveis | PENDENTE |
| W3-02 | Chain-of-Density | Passes de densificação: "Adicione exemplos concretos, valores numéricos, edge cases, formatos de dados específicos" aplicados a 5 seções-chave | `sectional_generator.py` | Seções densificadas contêm >= 5 exemplos concretos cada. Zero campos com valores genéricos ("dependendo do caso", "pode variar") | PENDENTE |
| W3-03 | Cross-Reference + Assembly | Pass final que adiciona referências cruzadas entre seções, verifica consistência terminológica e gera ToC com links | `sectional_generator.py`, `product_manager_agent.py` | PRD contém ToC funcional. >= 10 referências cruzadas entre seções. Terminologia consistente (verificável programaticamente) | PENDENTE |

### Meta da Onda 3
- **Chars esperados:** 100.000-140.000
- **Critério binário:** `len(prd_final) >= 100.000` E `is_clean: True` E `>= 3 diagramas Mermaid` E `>= 1 schema SQL`
- **Pré-requisito:** Onda 2 concluída

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

---

## Regras do Backlog
1. Itens movem de `PENDENTE` para `CONCLUÍDO` apenas após validação com critério binário
2. Cada Onda é uma Fase numerada (9.5, 9.6, 9.7)
3. Nenhuma Onda inicia sem a anterior concluída
4. Novas técnicas descobertas são adicionadas como Onda 4+
