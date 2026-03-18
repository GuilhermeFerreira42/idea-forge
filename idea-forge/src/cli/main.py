import sys
import os
import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def prompt_idea() -> str:
    print("\n" + "="*50)
    print("💡 IdeaForge CLI - Conversor de Ideias em Planos")
    print("="*50)
    print("\nPor favor, descreva a sua ideia de projeto de software:")
    
    lines = []
    while True:
        try:
            line = input("> ")
            if not line:
                break
            lines.append(line)
        except EOFError:
            break
            
    return "\n".join(lines).strip()

def display_response(role: str, content: str):
    """
    Exibe resposta de um agente com formatação ANSI.
    O conteúdo aqui já está LIMPO (sem blocos de pensamento).
    """
    from src.core.stream_handler import ANSIStyle

    role_styles = {
        "critic agent": (ANSIStyle.YELLOW, "⚡"),
        "proponent agent": (ANSIStyle.GREEN, "🛡️"),
        "planner": (ANSIStyle.BLUE, "📋"),
    }
    style, icon = role_styles.get(role.lower(), (ANSIStyle.CYAN, "🤖"))

    print(f"\n{style}{ANSIStyle.BOLD}--- [{icon} {role.upper()}] ---{ANSIStyle.RESET}")
    print(content)
    print(f"{style}{'─' * 25}{ANSIStyle.RESET}")

def ask_approval() -> bool:
    while True:
        choice = input("\nAprovar ideia refinada para o debate de agentes? (s/n): ").strip().lower()
        if choice in ['s', 'sim', 'y', 'yes']:
            return True
        elif choice in ['n', 'nao', 'não', 'no']:
            return False
        else:
            print("Resposta inválida. Digite 's' ou 'n'.")

from src.config.settings import LLM_PROVIDER, MODEL_NAME
from src.models.ollama_provider import OllamaProvider
from src.models.cloud_provider import CloudProvider
from src.core.controller import AgentController
import requests

def select_model() -> str:
    print("\n🔍 Buscando modelos locais no Ollama...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        
        if not models:
            print("Nenhum modelo encontrado no Ollama. Usando o padrão.")
            return MODEL_NAME
            
        print("\nModelos Disponíveis:")
        for i, model in enumerate(models):
            print(f"[{i+1}] {model['name']}")
            
        while True:
            choice = input(f"\nEscolha o modelo (1-{len(models)}) ou Enter para o padrão ({MODEL_NAME}): ")
            if not choice.strip():
                return MODEL_NAME
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(models):
                    selected_model = models[idx]['name']
                    break
                print("Opção inválida.")
            except ValueError:
                print("Por favor, digite um número válido.")
                
        # Ask for Deep Thinking if the model supports it
        reasoning_keywords = ["qwen", "deepseek", "reasoning", "r1"]
        think_preference = False
        if any(keyword in selected_model.lower() for keyword in reasoning_keywords):
            while True:
                think_choice = input(f"\nEste modelo ({selected_model}) suporta pensamento profundo (Reasoning). Deseja ativar? (s/n): ").strip().lower()
                if think_choice in ['s', 'sim', 'y', 'yes']:
                    think_preference = True
                    print("🧠 Pensamento profundo ativado.")
                    break
                elif think_choice in ['n', 'nao', 'não', 'no']:
                    print("⚡ Pensamento profundo desativado.")
                    break
                else:
                    print("Resposta inválida. Digite 's' ou 'n'.")
        
        return selected_model, think_preference
                
    except Exception as e:
        print(f"⚠️ Não foi possível carregar os modelos do Ollama: {str(e)}")
        print(f"Iremos usar a variável de ambiente: {MODEL_NAME}")
        return MODEL_NAME, False

def get_provider(selected_model: str, think_preference: bool):
    if LLM_PROVIDER.lower() == "ollama":
        return OllamaProvider(
            model_name=selected_model,
            think=think_preference,
            show_thinking=think_preference  # Mostrar pensamento apenas se ativado
        )
    else:
        return CloudProvider(model_name=selected_model)

def main():
    selected_model, think_preference = select_model()
    
    idea = prompt_idea()
    if not idea:
        print("Nenhuma ideia inserida. Encerrando.")
        sys.exit(0)
        
    provider = get_provider(selected_model, think_preference)
    # FASE 2: Propagar think_preference para o AgentController
    controller = AgentController(provider, think=think_preference)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"debate_RELATORIO_{timestamp}.md"
    
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(
            f"# 📋 Relatório de Debate IdeaForge - "
            f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        )
        f.write(f"**Ideia Inicial:**\n{idea}\n\n---\n")
    
    try:
        final_plan = controller.run_pipeline(idea, report_filename)
        
        print("\n" + "=" * 50)
        print("  🏆 PLANO DE DESENVOLVIMENTO FINALIZADO  ")
        print("=" * 50 + "\n")
        print(final_plan)
        print("\n" + "="*50)
        
    except Exception as e:
        print(f"\n❌ Erro durante a execução do pipeline: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
