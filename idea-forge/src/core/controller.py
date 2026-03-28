import sys
from src.core.blackboard import Blackboard
from src.core.artifact_store import ArtifactStore
from src.core.planner import Planner, TaskStatus
from src.agents.critic_agent import CriticAgent
from src.agents.proponent_agent import ProponentAgent
from src.agents.product_manager_agent import ProductManagerAgent
from src.agents.architect_agent import ArchitectAgent
from src.agents.security_reviewer_agent import SecurityReviewerAgent
from src.debate.debate_engine import DebateEngine
from src.planning.plan_generator import PlanGenerator
from src.models.model_provider import ModelProvider
from src.core.stream_handler import ANSIStyle


def emit_pipeline_state(state: str, detail: str = ""):
    """
    Emite um evento de estado visual para o terminal.
    Formato padronizado para todas as transições do pipeline.
    """
    state_icons = {
        "PIPELINE_START": "🚀",
        "BLACKBOARD_INIT": "🧠",
        "TASK_EXECUTION": "⚙️",
        "HUMAN_GATE": "✋",
        "PIPELINE_COMPLETE": "✅",
        "AGENT_THINKING": "💭",
    }
    icon = state_icons.get(state, "⚡")
    detail_str = f" — {detail}" if detail else ""
    sys.stdout.write(
        f"\n{ANSIStyle.CYAN}{ANSIStyle.BOLD}"
        f"[{icon} {state}]{detail_str}"
        f"{ANSIStyle.RESET}\n"
    )
    sys.stdout.flush()

class AgentController:
    """
    Orquestra o fluxo completo do sistema IdeaForge usando o Padrão Blackboard (Fase 3).
    """
    
    def __init__(self, provider: ModelProvider, think: bool = False):
        import datetime
        self.provider = provider
        self.think = think
        direct_mode = not think

        # Inicializa infraestrutura Blackboard
        self.blackboard = Blackboard()
        self.artifact_store = ArtifactStore(self.blackboard)
        
        # ═══ FASE 8.0b: Inicializar PipelineLogger (fail-safe) ═══
        self._run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = None
        try:
            from src.core.pipeline_logger import PipelineLogger
            self.logger = PipelineLogger(run_id=self._run_id)
        except Exception:
            pass # Logger falhou — pipeline opera normalmente
        # ═══ FIM FASE 8.0b ═══
        
        # Inicializa Agentes Especialistas
        self.agents = {
            "product_manager": ProductManagerAgent(provider, direct_mode=direct_mode),
            "architect": ArchitectAgent(provider, direct_mode=direct_mode),
            "critic": CriticAgent(provider, direct_mode=direct_mode),
            "proponent": ProponentAgent(provider, direct_mode=direct_mode),
            "security_reviewer": SecurityReviewerAgent(provider, direct_mode=direct_mode),
            "debate_engine": DebateEngine(
                proponent=ProponentAgent(provider, direct_mode=direct_mode),
                critic=CriticAgent(provider, direct_mode=direct_mode),
                rounds=3
            ),
            "plan_generator": PlanGenerator(provider, direct_mode=direct_mode)
        }
        
        # Atributos diretos para compatibilidade com a Fase 2 (necessário para testes legados)
        self.critic = self.agents["critic"]
        self.proponent = self.agents["proponent"]
        self.debate_engine = self.agents["debate_engine"]
        self.plan_generator = self.agents["plan_generator"]
        
        # Callback para o Human Gate (será injetado pelo CLI ou definido aqui)
        self.agents["human_gate_callback"] = self._cli_human_gate

        # Inicializa Planner
        self.planner = Planner(
            blackboard=self.blackboard,
            artifact_store=self.artifact_store,
            agents=self.agents,
            provider=provider,
            think=think,
            logger=self.logger  # FASE 8.0b
        )
        self.planner.load_default_dag()

    def _cli_human_gate(self, context: str) -> str:
        """Interação real com o CLI para o HUMAN_GATE do Planner."""
        from src.cli.main import display_response, ask_approval
        
        emit_pipeline_state("HUMAN_GATE", "Aguardando revisão do usuário")
        
        # Mostra o contexto (PRD + Review) para o usuário
        print(f"\n{ANSIStyle.BOLD}--- REVISÃO DO ARTEFATO ---{ANSIStyle.RESET}")
        print(context)
        
        approved = ask_approval()
        if approved:
            emit_pipeline_state("HUMAN_GATE", "Artefato aprovado")
            return "APPROVED"
        else:
            emit_pipeline_state("HUMAN_GATE", "Usuário solicitou refinamento")
            print("\nPor favor, descreva os ajustes necessários:")
            user_refinement = input("> ")
            if not user_refinement:
                print("[Sistema] Refinamento vazio. Encerrando.")
                sys.exit(0)
            
            # Na lógica do Planner, retornar algo diferente de APPROVED 
            # pode ser usado para disparar re-execuções se implementado.
            # Por enquanto, vamos injetar o refinamento como uma variável.
            self.blackboard.set_variable("user_refinement", user_refinement)
            return "REFINEMENT_NEEDED"

    def run_pipeline(self, initial_idea: str, report_filename: str = None) -> str:
        """
        Executa o pipeline baseado em Blackboard.
        """
        emit_pipeline_state("PIPELINE_START", "Iniciando Pipeline NEXUS (Fase 4)")
        
        # Armazena meta-informações
        self.blackboard.set_variable("initial_idea", initial_idea)
        self.blackboard.set_variable("report_filename", report_filename)
        
        # Executa o Planner
        try:
            if self.logger:
                self.logger.log("PIPELINE", "PIPELINE_START", data={"idea": initial_idea[:100]})

            final_plan = self.planner.execute_pipeline(initial_idea)
            
            # Persistência final
            self.blackboard.persist_to_disk()
            self.artifact_store.persist_to_disk()
            
            # Geração do relatório físico (.md) se solicitado
            if report_filename:
                self._generate_final_report(report_filename)

            if self.logger:
                self.logger.log("PIPELINE", "PIPELINE_END", data={"status": "SUCCESS"})
                self.logger.finalize(self.blackboard.snapshot())

            emit_pipeline_state("PIPELINE_COMPLETE", "Pipeline Blackboard concluído")
            
            # FASE 7.1: Retornar PRD final se existir, senão Development Plan
            prd_final_art = self.artifact_store.read("prd_final")
            if prd_final_art and len(prd_final_art.content.strip()) > 200:
                return prd_final_art.content
            return final_plan
            
        except Exception as e:
            print(f"\n{ANSIStyle.RED}[ERRO] Falha no pipeline: {str(e)}{ANSIStyle.RESET}")
            self.blackboard.persist_to_disk() # Salva o que deu pra salvar
            raise e

    def get_artifact_content(self, name: str) -> str:
        """
        FASE 8.0a: Retorna conteúdo textual de um artefato pelo nome.
        Retorna versão mais recente. Nunca lança exceção.
        """
        art = self.artifact_store.read(name)
        return art.content if art else ""

    def _generate_final_report(self, filename: str):
        """Compila todos os artefatos em um único arquivo Markdown."""
        
        with open(filename, "w", encoding="utf-8") as f:
            # FASE 7.1: Sumário executivo
            f.write(f"# Relatório IdeaForge — Padrão NEXUS\n\n")
            f.write(f"**Ideia:** {self.blackboard.get_variable('initial_idea')}\n\n")
            f.write(f"**Modelo:** {self.provider.model_name if hasattr(self.provider, 'model_name') else 'N/A'}\n\n")

            # FASE 7.1: PRD Final como documento principal
            prd_final = self.artifact_store.read("prd_final")
            if prd_final:
                f.write("---\n\n")
                f.write("## PRD FINAL CONSOLIDADO (Padrão NEXUS)\n\n")
                f.write(f"{prd_final.content}\n\n")
                f.write("---\n\n")

            # Índice dos artefatos de apoio
            artifacts_to_include = [
                "prd", "prd_review", "system_design",
                "security_review", "debate_transcript", "development_plan"
            ]
            
            f.write("## Artefatos de Apoio (Processo de Elaboração)\n\n")
            for art_name in artifacts_to_include:
                if self.artifact_store.exists(art_name):
                    f.write(f"- [{art_name.upper().replace('_', ' ')}](#{art_name})\n")
            f.write("\n---\n\n")

            # Artefatos individuais
            for art_name in artifacts_to_include:
                artifact = self.artifact_store.read(art_name)
                if artifact:
                    f.write(f"<a id='{art_name}'></a>\n\n")
                    f.write(f"## {art_name.upper().replace('_', ' ')}\n")
                    f.write(f"**Criado por:** {artifact.created_by} | **Versão:** {artifact.version}\n\n")
                    f.write(f"{artifact.content}\n\n")
                    f.write("---\n\n")

            # Métricas de qualidade
            f.write("## Métricas de Qualidade (NEXUS Calibration)\n\n")
            f.write("| Artefato | Density | Completude | Tabelas | Tokens |\n")
            f.write("|---|---|---|---|---|\n")
            from src.core.output_validator import OutputValidator
            validator = OutputValidator()
            
            # Incluir prd_final nas métricas
            all_artifacts = ["prd_final"] + artifacts_to_include
            for art_name in all_artifacts:
                artifact = self.artifact_store.read(art_name)
                if artifact:
                    type_map = {
                        "prd": "prd", "prd_final": "prd_final",  # FASE 8.0a
                        "system_design": "system_design",
                        "prd_review": "review", "security_review": "security_review",
                        "development_plan": "plan"
                    }
                    val = validator.validate(artifact.content, type_map.get(art_name, "document"))
                    f.write(
                        f"| {art_name.upper()} | {val.get('density_score', 0):.2f} | "
                        f"{int(val.get('completeness_score', 0)*100)}% | "
                        f"{val.get('table_count', 0)} | {artifact.token_estimate()} |\n"
                    )

            f.write(f"\n---\n*Gerado via IdeaForge CLI — Calibração NEXUS Fase 7.1*")
