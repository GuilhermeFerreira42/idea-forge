import os
import shutil
import subprocess
from datetime import datetime

def coletar():
    target_dir = f"VALIDACAO_PAYLOAD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(target_dir, exist_ok=True)

    # 1. Executar testes e salvar output
    print("Executando testes...")
    test_result = subprocess.run(["pytest", "tests/", "-q"], capture_output=True, text=True)
    with open(os.path.join(target_dir, "test_results.txt"), "w", encoding="utf-8") as f:
        f.write(test_result.stdout)

    # 2. Localizar diretório de log mais recente
    logs_base = ".forge/logs"
    if os.path.exists(logs_base):
        log_dirs = [os.path.join(logs_base, d) for d in os.listdir(logs_base)]
        if log_dirs:
            latest_log = max(log_dirs, key=os.path.getmtime)
            print(f"Copiando evidências de: {latest_log}")
            
            # Copiar artifacts vitais
            artifacts_dir = os.path.join(latest_log, "artifacts")
            if os.path.exists(artifacts_dir):
                for file in ["prd_final.md", "consistency_report.md"]:
                    src = os.path.join(artifacts_dir, file)
                    if os.path.exists(src):
                        shutil.copy2(src, target_dir)
            
            # Copiar pipeline.jsonl para análise de steps
            pipeline_log = os.path.join(latest_log, "pipeline.jsonl")
            if os.path.exists(pipeline_log):
                shutil.copy2(pipeline_log, target_dir)

    print(f"Evidências consolidadas em: {target_dir}/")

if __name__ == "__main__":
    coletar()