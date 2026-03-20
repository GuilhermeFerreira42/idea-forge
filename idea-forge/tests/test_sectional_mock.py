import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
