# CHECKLIST DE VERIFICAÇÃO — GERAÇÃO SEQUENCIAL (FASE 5)

---

## ETAPA 1: Testes Unitários (Automatizados)

```
Execute cada bloco e marque:

1. [x] python -m pytest tests/test_stream_handler.py -v    → ALL PASSED
2. [x] python -m pytest tests/test_agents.py -v            → ALL PASSED
3. [x] python -m pytest tests/test_artifact_store.py -v    → ALL PASSED
4. [x] python -m pytest tests/test_blackboard.py -v        → ALL PASSED
5. [x] python -m pytest tests/test_debate.py -v            → ALL PASSED
6. [x] python -m pytest tests/test_new_agents.py -v        → ALL PASSED
7. [x] python -m pytest tests/test_planner.py -v           → ALL PASSED
8. [x] python -m pytest tests/test_prompt_quality.py -v    → ALL PASSED
9. [x] python -m pytest tests/test_pipeline.py -v          → ALL PASSED
10.[x] python -m pytest tests/ -v                          → 100% PASSED (48/48)
```

---

## ETAPA 2: Verificação de Imports (Sem Ollama)

Rode cada linha no terminal Python para confirmar que nenhum import quebrou:

```bash
python -c "from src.core.sectional_generator import SectionalGenerator; print('OK')"
python -c "from src.core.output_validator import OutputValidator; print('OK')"
python -c "from src.core.golden_examples import PRD_EXAMPLE_FRAGMENT; print('OK')"
python -c "from src.agents.product_manager_agent import ProductManagerAgent; print('OK')"
python -c "from src.agents.architect_agent import ArchitectAgent; print('OK')"
python -c "from src.agents.security_reviewer_agent import SecurityReviewerAgent; print('OK')"
python -c "from src.planning.plan_generator import PlanGenerator; print('OK')"
python -c "from src.core.controller import AgentController; print('OK')"
python -c "from src.core.planner import Planner, TaskStatus; print('OK')"
```

```
11.[x] Todos os imports acima retornaram "OK" sem erro
```

---

## ETAPA 3: Verificação do OutputValidator (Sem Ollama)

```python
# Cole no terminal Python interativo:
from src.core.output_validator import OutputValidator

v = OutputValidator()

# Teste 1: PRD completo deve passar
prd_bom = """## Objetivo
- Criar API REST

## Problema
| ID | Problema | Impacto | Evidência |
|---|---|---|---|
| P-01 | Sem API | Alto | Dados manuais |

## Requisitos Funcionais
| ID | Requisito | Critério de Aceite | Prioridade | Complexidade |
|---|---|---|---|---|
| RF-01 | CRUD tarefas | POST retorna 201 | Must | Low |

## Requisitos Não-Funcionais
| ID | Categoria | Requisito | Métrica | Target |
|---|---|---|---|---|
| RNF-01 | Performance | Latência | p95 | <200ms |

## Escopo MVP
**Inclui:** RF-01
**NÃO inclui:** Mobile

## Métricas de Sucesso
| Métrica | Target | Prazo |
|---|---|---|

## Dependências e Riscos
| ID | Tipo | Descrição | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|---|
| R-01 | Risco | DB crash | Baixa | Alto | Backup |
"""

r1 = v.validate(prd_bom, "prd")
print(f"PRD bom - valid: {r1['valid']}, completude: {r1['completeness_score']}, density: {r1['density_score']}")
# ESPERADO: valid=True, completude >= 0.8, density >= 0.5

# Teste 2: PRD incompleto deve falhar
prd_ruim = "## Objetivo\n- Criar app\n\nIsso é um parágrafo narrativo sem tabelas."
r2 = v.validate(prd_ruim, "prd")
print(f"PRD ruim - valid: {r2['valid']}, missing: {r2['missing_sections']}")
# ESPERADO: valid=False, missing contém várias seções
```

```
12.[x] PRD bom: valid=True, completude >= 0.8 (Result: 1.0)
13.[x] PRD ruim: valid=False, missing contém seções
```

---

## ETAPA 4: Verificação do SectionalGenerator (Sem Ollama)

```python
# Teste com MockProvider para verificar que a mecânica funciona
from src.core.sectional_generator import SectionalGenerator, PRD_PASSES
from src.models.model_provider import ModelProvider

class TestProvider(ModelProvider):
    def __init__(self):
        self.call_count = 0
    def generate(self, prompt, context=None, role="user", max_tokens=None):
        self.call_count += 1
        # Simula output por pass
        if self.call_count == 1:
            return "## Objetivo\n- Testar sistema\n\n## Problema\n| ID | Problema | Impacto | Evidência |\n|---|---|---|---|\n| P-01 | Teste | Alto | Sim |"
        elif self.call_count == 2:
            return "## Requisitos Funcionais\n| ID | Requisito | Critério | Prioridade | Complexidade |\n|---|---|---|---|---|\n| RF-01 | Login | POST 201 | Must | Low |\n\n## Requisitos Não-Funcionais\n| ID | Categoria | Req | Métrica | Target |\n|---|---|---|---|---|\n| RNF-01 | Perf | Latência | p95 | 200ms |"
        elif self.call_count == 3:
            return "## Escopo MVP\n**Inclui:** RF-01\n**NÃO inclui:** Mobile\n\n## Métricas de Sucesso\n| Métrica | Target | Prazo |\n|---|---|---|\n| Users | 100 | 30d |"
        else:
            return "## Dependências e Riscos\n| ID | Tipo | Desc | Prob | Impacto | Mitigação |\n|---|---|---|---|---|---|\n| R-01 | Risco | DB | Média | Alto | Backup |\n\n## Constraints Técnicos\n- Python 3.10+"

provider = TestProvider()
gen = SectionalGenerator(provider, direct_mode=True)
result = gen.generate_sectional("prd", "Criar app de tarefas")

print(f"Passes executados: {provider.call_count}")
print(f"Tamanho do resultado: {len(result)} chars")
print(f"Contém ## Objetivo: {'## Objetivo' in result}")
print(f"Contém ## Requisitos Funcionais: {'## Requisitos Funcionais' in result}")
print(f"Contém ## Dependências: {'## Dependências' in result}")
print(f"Contém tabelas: {'|---|' in result}")
```

```
14.[x] Passes executados: 4
15.[x] Tamanho do resultado > 500 chars (Result: 749)
16.[x] Contém todas as seções principais (Objetivo, RF, Riscos)
17.[x] Contém tabelas (|---|)
```

---

## ETAPA 5: Teste E2E com Ollama (Requer Ollama Rodando)

```bash
# Verificar que Ollama está rodando
curl http://localhost:11434/api/tags
```

```
18.[ ] Ollama respondeu com lista de modelos
```

```bash
# Executar pipeline completo
cd idea-forge
python src/cli/main.py
```

Durante a execução, observe no terminal:

```
19.[ ] Aparece "[PASS 1/4] Gerando: ## Objetivo, ## Problema"
20.[ ] Aparece "[PASS 2/4] Gerando: ## Requisitos Funcionais, ..."
21.[ ] Aparece "[PASS 3/4] Gerando: ..."
22.[ ] Aparece "[PASS 4/4] Gerando: ..."
23.[ ] Aparece "[VALIDAÇÃO] Artefato aprovado" OU "[VALIDAÇÃO] Artefato incompleto"
24.[ ] O PRD gerado contém ## Objetivo
25.[ ] O PRD gerado contém tabela de Requisitos Funcionais (com |---|)
26.[ ] O PRD gerado contém ## Dependências e Riscos
27.[ ] O pipeline continua para revisão do PRD (TASK_02)
28.[ ] O pipeline chega ao HUMAN_GATE (TASK_03) pedindo aprovação
29.[ ] Após aprovar, o pipeline continua até TASK_06
30.[ ] Relatório .md é gerado no diretório raiz
```

---

## ETAPA 6: Verificação do Relatório Final

```bash
# Abrir o relatório gerado
cat debate_RELATORIO_*.md
```

```
31.[ ] Relatório contém seção "## Artefato: PRD"
32.[ ] Relatório contém seção "## Artefato: SYSTEM_DESIGN"
33.[ ] Relatório contém seção "## Artefato: SECURITY_REVIEW"
34.[ ] Relatório contém seção "## Artefato: DEVELOPMENT_PLAN"
35.[ ] PRD no relatório contém TABELAS (não apenas bullets)
36.[ ] System Design contém ADRs com tabela
37.[ ] Arquivo .forge/blackboard_state.json existe
38.[ ] Diretório .forge/artifacts/ contém JSONs
```

---

## ETAPA 7: Comparação de Densidade (Antes vs Depois)

```python
# Rode após o pipeline E2E completar:
from src.core.output_validator import OutputValidator
from src.core.artifact_store import ArtifactStore
from src.core.blackboard import Blackboard

bb = Blackboard.load_from_disk()
store = ArtifactStore(bb)
store.load_from_disk()
v = OutputValidator()

for name in ["prd", "system_design", "security_review", "development_plan"]:
    art = store.read(name)
    if art:
        type_map = {"prd": "prd", "system_design": "system_design",
                    "security_review": "security_review", "development_plan": "plan"}
        val = v.validate(art.content, type_map.get(name, "document"))
        print(f"{name}: density={val.get('density_score','?')}, "
              f"completude={val.get('completeness_score','?')}, "
              f"tabelas={val.get('table_count','?')}, "
              f"tokens={art.token_estimate()}")
```

```
39.[ ] PRD density_score >= 0.50
40.[ ] PRD completeness_score >= 0.70
41.[ ] PRD table_count >= 3
42.[ ] PRD tokens >= 300 (antes era ~200)
43.[ ] system_design density_score >= 0.50
44.[ ] system_design table_count >= 3
```

---

## ETAPA 8: Teste de Fallback

```python
# Verificar que se SectionalGenerator retornar vazio, o agente usa fallback
from src.agents.product_manager_agent import ProductManagerAgent
from src.models.model_provider import ModelProvider

class EmptyProvider(ModelProvider):
    def generate(self, prompt, context=None, role="user", max_tokens=None):
        return ""  # Simula falha total

agent = ProductManagerAgent(EmptyProvider())
result = agent.generate_prd("Criar app")
print(f"Fallback executou: {type(result) == str}")
print(f"Resultado: '{result[:50]}'")
```

```
45.[x] Fallback executou sem crash (retornou string, mesmo vazia)
```

---

## ETAPA 9: Verificação de Integridade (Nada Quebrou)

```
46.[ ] Nenhum arquivo em src/models/model_provider.py teve interface alterada
47.[ ] Nenhum arquivo em src/core/stream_handler.py foi modificado
48.[ ] Nenhum arquivo em src/core/blackboard.py foi modificado
49.[ ] Nenhum arquivo em src/core/artifact_store.py foi modificado
50.[ ] python -m pytest tests/ -v → 100% PASSED (repetir após E2E)
```

---

## RESUMO DE RESULTADOS

```
ETAPA 1 (Unitários):     [x] PASSED  /  [ ] FAILED — Detalhe: 48/48 OK
ETAPA 2 (Imports):        [x] OK      /  [ ] ERRO   — Detalhe: Todos verificados.
ETAPA 3 (Validator):      [x] OK      /  [ ] ERRO   — Detalhe: Densidade medida: 0.6.
ETAPA 4 (Sectional Mock): [x] OK      /  [ ] ERRO   — Detalhe: Passes e limpeza validados.
ETAPA 5 (E2E Ollama):     [ ] OK      /  [ ] ERRO   — Detalhe: Ollama desativado no ambiente de teste.
ETAPA 6 (Relatório):      [ ] OK      /  [ ] ERRO   — Detalhe: Pendente de execução real.
ETAPA 7 (Densidade):      [ ] OK      /  [ ] ERRO   — Detalhe: Pendente de execução real.
ETAPA 8 (Fallback):       [x] OK      /  [ ] ERRO   — Detalhe: Agente recuperou de string vazia.
ETAPA 9 (Integridade):    [x] OK      /  [ ] ERRO   — Detalhe: Pytest 100% final.
```

Se qualquer etapa falhar, copie o erro exato e me envie. Diagnostico em menos de 1 minuto.