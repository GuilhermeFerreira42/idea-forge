F9.3 | ADD | `NEXUS_FINAL_PASSES` | Estabelecem 12 passes para PRD Final Consolidado | `sectional_generator.py`
F9.3 | MOD | `SectionalGenerator` | `_summarize_previous` estendido para max_tokens 500 | `sectional_generator.py`
F9.3 | ADD | `generate_sectional_with_inputs` | Método novo para combinação de contextos seletivos | `sectional_generator.py`

### Fase 9.3 — Calibração de Profundidade
- F9.3 | ADD | `NEXUS_FINAL_PASSES` | Estabelecem 12 passes para PRD Final Consolidado | `src/core/sectional_generator.py`
- F9.3 | MOD | `SectionalGenerator` | `_summarize_previous` estendido para max_tokens 500 | `src/core/sectional_generator.py`
- F9.3 | ADD | `generate_sectional_with_inputs` | Método novo para combinação de contextos seletivos | `src/core/sectional_generator.py`

### Fase 9.4 — Calibração de Passes Fracos + Fix RF_ORPHAN
- F9.4 | MOD | NEXUS_FINAL_PASSES | Aumentado min_chars nos passes para PRD Final longo | src/core/sectional_generator.py
- F9.4 | MOD | NEXUS_FINAL_PASSES | Ajustado example do P08 para mitigar fantasma de RF | src/core/sectional_generator.py

### Fase 9.5 — Onda 1 de Expansão
- F9.5 | ADD | src/core/exemplars/ | 12 arquivos com trechos gold-standard para injeção de profundidade | src/core/exemplars/
- F9.5 | ADD | SectionQualityChecker | Verificador programático de densidade, itens e palavras-chave por seção | src/core/section_quality_checker.py
- F9.5 | MOD | SectionalGenerator | Integração de exemplares e QualityChecker no loop de retry | src/core/sectional_generator.py
- F9.5 | MOD | NEXUS_FINAL_PASSES | Word count targets e min_chars agressivos (meta 40k-50k) | src/core/sectional_generator.py

### Fase 9.5.1 — Onda 1 (Correção)
- F9.5.1 | MOD | `NEXUS_FINAL_PASSES` | Expansão para 18 passes com técnica Skeleton-then-Flesh | `src/core/sectional_generator.py`
- F9.5.1 | MOD | `src/core/exemplars/` | Redução para Exemplares Lean (~400 chars) para mitigar sobrecarga cognitiva | `src/core/exemplars/`
- F9.5.1 | MOD | `SectionalGenerator` | Aumento de MAX_RETRIES_PER_PASS para 3 e bypass de qualidade em skeletons | `src/core/sectional_generator.py`
- F9.5.1 | MOD | `src/cli/main.py` | Adição de argumentos --model e --idea para automação de testes/execução | `src/cli/main.py`
- F9.5.1 | MOD | `SectionPass` | Migração para keyword arguments e input_budget fixo de 3000 para estabilidade | `src/core/sectional_generator.py`

### Fase 9.5.3 — Onda 1 Concluída (Cura de Assembly)
- F9.5.3b | MOD | Calibração de Word Count | Evitar falhas de prompt e garantir densidade | src/core/sectional_generator.py
- F9.5.3c | MOD | Filtros Multi-Seção | Resolver bug de assembly e garantir 20 seções | src/core/sectional_generator.py
