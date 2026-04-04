# ESTADO ATUAL — IdeaForge CLI

**Versão do Sistema:** NEXUS v1.4.5 (Portabilidade Atômica)  
**Status Global:** [✅] Fase 9.7 (Onda 3) Concluída | [ ] Fase 9.8 Próxima (Qualidade de Conteúdo)

---

## 🛠️ Arquitetura NEXUS (V1.4.4)
- **Padrão:** Quadro Negro (Blackboard) com Grafo de Tarefas (DAG) de 9 etapas.
- **Consolidação:** A tarefa TASK_07 utiliza **20 passes granulares** (NEXUS FINAL) com técnicas de *Esqueleto-depois-Conteúdo* (Skeleton-then-Flesh) para seções críticas e calibração de contagem de palavras por passagem.
- **Micro-Tarefas:** Passagens atômicas configuradas em `sectional_generator.py` com limite de contexto (`input_budget`) restrito a 3000 caracteres para estabilidade.
- **Fronteira Dinâmica:** O gerador seccional utiliza regras de fronteira dinâmica e filtragem multi-seção para evitar o truncamento em passes que geram múltiplos cabeçalhos `##`.
- **Retry Inteligente:** Implementação de orquestrador de retry em 3 níveis com validação automática e deduplicação.

---

## 🏗️ Módulos e Contratos Vigentes

| Módulo | Arquivo | Responsabilidade | Versão |
|---|---|---|---|
| Gerador Seccional | `sectional_generator.py` | Geração multi-pass (20 passes NEXUS) com filtros multi-seção. | F9.5.3c |
| Verificador de Qualidade | `section_quality_checker.py` | Validação programática de densidade e estrutura (mínimo de palavras/itens). | F9.5 |
| Agente Gerente de Produto | `product_manager_agent.py` | Orquestração da consolidação final e injeção de artefatos. | F12 |
| Verificador de Consistência | `consistency_checker_agent.py` | Auditoria estrutural pós-geração (verificação de integridade). | F9 |
| Planejador | `planner.py` | Orquestração do fluxo principal de tarefas. | F9 |
| Provedor de Modelo | `ollama_provider.py` | Interface com LLM (separação entre Raciocínio/Conteúdo). | F7 |
| Orquestrador de Retry | `retry_orchestrator.py` | Mecanismo de recuperação em 3 níveis para seções falhadas. | F9.6 |
| Templates de Retry | `retry_templates.py` | Templates estáticos para fallback Nível 3. | F9.6 |
| Perfis de Prompt | `prompt_profiles.py` | Calibração de tokens e inferência baseada em modelo (SMALL/MEDIUM/LARGE). | F9.7 |
| Decompositor Atômico | `atomic_task_decomposer.py` | Geração estruturada de micro-tarefas (tabelas/bullets) para modelos 1B-3B. | F9.7 |

---

## 🗺️ Fluxo de Tarefas (Pipeline NEXUS)
1. **TASK_01**: Geração do PRD inicial (PM).
2. **TASK_02**: Crítica técnica (Critic).
3. **TASK_04**: Design de Sistema e Segurança (Designer/Security).
4. **TASK_05**: Debate estruturado de problemas identificados.
5. **TASK_06**: Geração do Plano de Desenvolvimento.
6. **TASK_07**: Consolidação NEXUS (20 passes) → **PRD FINAL**.
7. **TASK_07b**: Auditoria de Consistência (Audit).
8. **TASK_07c**: Retry Inteligente (recuperação de seções falhadas).

---

## 📉 Invariantes e Restrições de Qualidade
1. **Densidade Crítica**: Meta de 25.000+ caracteres para o PRD Final Consolidado.
2. **Integridade Estrutural**: Garantia de 20/20 seções obrigatórias via filtros de montagem.
3. **Limite de Contexto**: Máximo de 3000 caracteres de contexto injetado por sub-passagem.
4. **Resiliência**: Limite de 3 tentativas por passagem com fallback automático.
5. **Zero Falhas**: Garantia de zero `AttributeError` e zero `[GERAÇÃO FALHOU]` no output final.

---

## 🧪 Verificação e Testes
- **Suíte de Unidade:** 159 testes em `tests/` cobrindo filtros, prompts, provedores e retry.
- **Certificação Cloud:** Validação recorrente com `gpt-oss:20b-cloud` para profundidade máxima.
- **Teste de Regressão:** `tests/test_sectional_generator_filters.py` valida as correções da Onda 1c (Montagem).
- **Teste de Retry:** Novos testes em `tests/test_retry_orchestrator.py` e `tests/test_retry_templates.py`.

---
*Gerado via Protocolo de Arquivamento — 04/04/2026*