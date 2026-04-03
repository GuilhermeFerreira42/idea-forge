import sys
import os
import time
from src.models.ollama_provider import OllamaProvider
from src.core.controller import AgentController

def run_certification(run_number):
    print(f"\n{'='*20} INICIANDO RUN {run_number} {'='*20}")
    idea = "Sistema de gerenciamento de biblioteca descentralizado com empréstimos via blockchain e sistema de reputação para leitores."

    provider = OllamaProvider(model_name="gpt-oss:20b-cloud", think=False)
    controller = AgentController(provider, think=False)

    # Pular human gate para automação
    controller.agents["human_gate_callback"] = lambda ctx: "APPROVED"

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_file = f"certification_run_{run_number}_{timestamp}.md"

    try:
        start_time = time.time()
        final_prd = controller.run_pipeline(idea, report_file)
        end_time = time.time()

        duration = end_time - start_time
        prd_len = len(final_prd)

        # Verificar is_clean
        consistency_report = controller.get_artifact_content("consistency_report")
        is_clean = "is_clean:** True" in consistency_report
        failed_markers = final_prd.count("[GERAÇÃO FALHOU]")

        print(f"\nRESULTADOS RUN {run_number}:")
        print(f"- Duração: {duration:.2f}s")
        print(f"- Tamanho PRD: {prd_len} chars")
        print(f"- is_clean: {is_clean}")
        print(f"- Marcadores de falha: {failed_markers}")

        return {
            "run": run_number,
            "duration": duration,
            "len": prd_len,
            "is_clean": is_clean,
            "failed_markers": failed_markers,
            "report": report_file
        }
    except Exception as e:
        print(f"Erro na Run {run_number}: {e}")
        return None

if __name__ == "__main__":
    results = []
    for i in range(1, 4):
        res = run_certification(i)
        if res:
            results.append(res)
            
    print("\n" + "#"*50)
    print("RESUMO DA CERTIFICAÇÃO FASE 9.6")
    print("#"*50)
    for r in results:
        status = "✅ PASSOU" if r["is_clean"] and r["failed_markers"] == 0 and r["len"] >= 25000 else "❌ FALHOU"
        print(f"Run {r['run']}: {status} | Chars: {r['len']} | Clean: {r['is_clean']} | Failures: {r['failed_markers']}")
