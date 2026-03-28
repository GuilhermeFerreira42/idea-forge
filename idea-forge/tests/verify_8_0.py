import sys
import os
import datetime
import unittest
from unittest.mock import MagicMock

# Adicionar o diretório raiz ao path para encontrar src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.controller import AgentController
from src.models.model_provider import ModelProvider

class MockProvider(ModelProvider):
    def __init__(self):
        self.model_name = "mock-model"
    def generate(self, prompt, context=None, role="user", max_tokens=None):
        # Retorna um PRD Final completo para passar na validação de 16 seções
        return (
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
            "Texto longo para passar nos 800 caracteres do PRD final consolidado. " * 5
        )

def verify_8_0():
    provider = MockProvider()
    controller = AgentController(provider, think=False)
    
    # Mock para pular o human gate
    controller.agents["human_gate_callback"] = lambda x: "APPROVED"
    
    idea = "Aplicativo de testes para Fase 8.0"
    report_filename = "test_8_0_report.md"
    
    print("\n🚀 Executando pipeline mockado para verificação da Fase 8.0...")
    controller.run_pipeline(idea, report_filename)
    
    # Verificações 8.0a
    prd_final = controller.artifact_store.read("prd_final")
    if not prd_final:
        print("❌ Erro: Artefato prd_final não gerado.")
        return False
    
    print("✅ Artefato prd_final gerado e armazenado.")
    
    # Verificações 8.0b
    log_dir = ".forge/logs"
    if not os.path.exists(log_dir):
        print("❌ Erro: Diretório .forge/logs não encontrado.")
        return False
    
    runs = os.listdir(log_dir)
    if not runs:
        print("❌ Erro: Nenhuma execução encontrada em .forge/logs.")
        return False
    
    # Pega a run mais recente
    latest_run = sorted(runs)[-1]
    run_path = os.path.join(log_dir, latest_run)
    
    files_to_check = ["pipeline.jsonl", "pipeline_summary.md", "artifacts/prd_final.md"]
    for f in files_to_check:
        if not os.path.exists(os.path.join(run_path, f)):
            print(f"❌ Erro: Arquivo de log '{f}' não encontrado em {run_path}.")
            return False
    
    print(f"✅ Logs gerados corretamente em: {run_path}")
    print("✅ Sumário e artefatos individuais salvos.")
    
    # Limpeza (opcional)
    # import shutil
    # shutil.rmtree(run_path)
    # os.remove(report_filename)
    
    print("\n🏆 Fase 8.0 verificada com SUCESSO!")
    return True

if __name__ == "__main__":
    if verify_8_0():
        sys.exit(0)
    else:
        sys.exit(1)
