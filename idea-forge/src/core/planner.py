import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from src.core.blackboard import Blackboard
from src.core.artifact_store import ArtifactStore

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"      # Dependência não satisfeita
    SKIPPED = "skipped"      # Pulada por decisão do Planner

@dataclass
class TaskDefinition:
    """Definição estática de uma task na DAG."""
    task_id: str                    # Identificador único (ex: "TASK_01")
    agent_name: str                 # Nome do agente responsável
    method_name: str                # Método a invocar no agente
    input_artifacts: List[str]      # Nomes dos artefatos de input
    output_artifact: str            # Nome do artefato de output
    requires: List[str] = field(default_factory=list) # IDs de tasks que devem estar COMPLETED
    task_type: str = "AGENT"        # "AGENT" | "HUMAN_GATE" | "ENGINE"
    max_context_tokens: int = 1500  # Budget de tokens para hot-load

class Planner:
    """Orquestrador baseado em DAG de tarefas."""

    def __init__(self, blackboard: Blackboard,
                 artifact_store: ArtifactStore,
                 agents: Dict[str, Any],
                 provider: Any = None,
                 think: bool = False,
                 logger: Any = None) -> None:
        self.blackboard = blackboard
        self.artifact_store = artifact_store
        self.agents = agents
        self.provider = provider
        self.think = think
        self.logger = logger  # FASE 8.0b
        self.dag: List[TaskDefinition] = []

    def load_default_dag(self) -> None:
        """Carrega a DAG padrão de 8 tasks conforme o Blueprint NEXUS (Fase 7.1)."""
        self.dag = [
            TaskDefinition(
                task_id="TASK_01",
                agent_name="product_manager",
                method_name="generate_prd",
                input_artifacts=["user_idea"],
                output_artifact="prd",
                requires=[]
            ),
            TaskDefinition(
                task_id="TASK_02",
                agent_name="critic",
                method_name="review_artifact",
                input_artifacts=["prd"],
                output_artifact="prd_review",
                requires=["TASK_01"]
            ),
            TaskDefinition(
                task_id="TASK_03",
                agent_name="system",
                method_name="human_gate",
                input_artifacts=["prd", "prd_review"],
                output_artifact="approval_decision",
                requires=["TASK_02"],
                task_type="HUMAN_GATE"
            ),
            TaskDefinition(
                task_id="TASK_04",
                agent_name="architect",
                method_name="design_system",
                input_artifacts=["prd", "approval_decision"],
                output_artifact="system_design",
                requires=["TASK_03"]
            ),
            # FASE 4: Nova task de Security Review
            TaskDefinition(
                task_id="TASK_04b",
                agent_name="security_reviewer",
                method_name="review_security",
                input_artifacts=["system_design", "prd"],
                output_artifact="security_review",
                requires=["TASK_04"]
            ),
            TaskDefinition(
                task_id="TASK_05",
                agent_name="debate_engine",
                method_name="run",
                input_artifacts=["prd", "system_design", "security_review"],
                output_artifact="debate_transcript",
                requires=["TASK_04b"],  # Agora depende de security review
                task_type="ENGINE"
            ),
            TaskDefinition(
                task_id="TASK_06",
                agent_name="plan_generator",
                method_name="generate_plan",
                input_artifacts=["prd", "system_design", "security_review", "debate_transcript"],
                output_artifact="development_plan",
                requires=["TASK_05"],
                task_type="ENGINE"
            ),
            # FASE 7.1: Consolidação final — PRD definitivo no padrão NEXUS
            TaskDefinition(
                task_id="TASK_07",
                agent_name="product_manager",
                method_name="consolidate_prd",
                input_artifacts=["prd", "prd_review", "system_design", 
                               "security_review", "debate_transcript", "development_plan"],
                output_artifact="prd_final",
                requires=["TASK_06"],
                task_type="AGENT",
                max_context_tokens=3000
            )
        ]
        for task in self.dag:
            self.blackboard.set_task_status(task.task_id, TaskStatus.PENDING)

    def execute_pipeline(self, user_idea: str) -> str:
        """Executa todas as tasks da DAG em ordem topológica."""
        # Inicializa a ideia do usuário no blackboard/artifact_store
        self.artifact_store.write("user_idea", user_idea, "raw_input", "user")
        
        while True:
            # Encontra as próximas tasks prontas para executar
            pending_tasks = [t for t in self.dag if self.blackboard.get_task_status(t.task_id) == str(TaskStatus.PENDING)]
            if not pending_tasks:
                break

            ready_tasks = [t for t in pending_tasks if self._check_dependencies(t)]
            if not ready_tasks:
                # Pode haver um impasse ou todas as tasks falharam/bloquearam
                break

            for task in ready_tasks:
                self._execute_task(task)

        # Retorna o artefato final se existir
        final_art = self.artifact_store.read("development_plan")
        return final_art.content if final_art else "Pipeline failed to generate a final plan."

    def _check_dependencies(self, task: TaskDefinition) -> bool:
        """Verifica se todas as dependências de uma task estão COMPLETED."""
        for dep_id in task.requires:
            if self.blackboard.get_task_status(dep_id) != str(TaskStatus.COMPLETED):
                return False
        return True

    def _execute_task(self, task: TaskDefinition) -> None:
        """Executa uma task individual com Budgeting e Post-processing (Fase 3.1)."""
        self.blackboard.set_task_status(task.task_id, TaskStatus.RUNNING)
        
        # FASE 8.0b: Log start
        if self.logger:
            self.logger.log(task.task_id, "TASK_START", agent=task.agent_name)

        # FASE 7.1: Aumentar budget de contexto para artefatos NEXUS densos
        TASK_CONFIGS = {
            "generate_prd": {"hint": "transform", "max_tokens": 1000},
            "review_artifact": {"hint": "review", "max_tokens": 2500},      # era 1200
            "design_system": {"hint": "transform", "max_tokens": 2500},     # era 1500
            "run": {"hint": "reference", "max_tokens": 1500},               # era 1000
            "generate_plan": {"hint": "transform", "max_tokens": 2500},     # era 1800
            "review_security": {"hint": "review", "max_tokens": 2000},
            "consolidate_prd": {"hint": "reference", "max_tokens": 3000},   # FASE 7.1: TASK_07
        }
        
        config = TASK_CONFIGS.get(task.method_name, {"hint": "reference", "max_tokens": 1500})
        
        try:
            # 1. Hot-load context com usage_hint
            context = self.artifact_store.get_context_for_agent(
                task.input_artifacts, 
                max_tokens=config["max_tokens"],
                usage_hint=config["hint"]
            )
            
            agent = self.agents.get(task.agent_name)
            
            if task.task_type == "HUMAN_GATE":
                result = self._handle_human_gate(task, context)
            else:
                method = getattr(agent, task.method_name) if agent else None
                
                # Resgate do input primário
                first_input_art = self.artifact_store.read(task.input_artifacts[0])
                first_input = first_input_art.content if first_input_art else ""
                
                # FASE 4: Dispatch especializado para Security Review
                if task.method_name == "review_security":
                    # Security Reviewer recebe system_design como primeiro input, PRD como contexto
                    prd_art = self.artifact_store.read("prd")
                    result = method(
                        system_design=first_input,
                        prd_context=prd_art.content[:500] if prd_art else ""
                    )
                # FASE 7.1: Dispatch especializado para Consolidação NEXUS
                elif task.method_name == "consolidate_prd":
                    original_idea = self.blackboard.get_variable("initial_idea", "")
                    result = method(
                        artifacts_context=context,
                        original_idea=original_idea
                    )
                # FASE 3.1: Passagem explícita de contexto
                elif method and (len(task.input_artifacts) > 1 or context):
                    result = method(first_input, context)
                elif method:
                    result = method(first_input)
                else:
                    # Caso de fallback para motores (Engine) que não usam métodos de agentes tradicionais
                    result = "Engine task execution" # Isso deve ser tratado pela lógica de Engine

            # 2. Pós-processamento: Limpeza de ruído narrativo residual
            clean_result = self._post_process_output(str(result))

            # ═══════════════════════════════════════════════
            # FASE 5.1: HARD GATE — Validação bloqueante
            # ═══════════════════════════════════════════════
            from src.core.output_validator import OutputValidator
            validator = OutputValidator()
            artifact_type_tag = self._get_artifact_tag_for_validator(task)
            validation = validator.validate(clean_result, artifact_type_tag)

            # FASE 8.0b: Log validation
            if self.logger:
                self.logger.log_validation(
                    task_id=task.task_id,
                    artifact_type=artifact_type_tag,
                    validation_result=validation,
                    content_preview=clean_result[:200]
                )

            if not validation.get("valid", True):
                fail_reasons = validation.get("fail_reasons", [])
                import sys
                from src.core.stream_handler import ANSIStyle

                # Verificar se é falha total (vazio) ou parcial
                is_empty = any("EMPTY" in r or "TOO_SHORT" in r for r in fail_reasons)

                if is_empty:
                    # FALHA TOTAL: artefato vazio — NÃO persistir
                    sys.stdout.write(
                        f"\n{ANSIStyle.YELLOW}⚠ [HARD GATE] Artefato "
                        f"'{task.output_artifact}' está VAZIO ou muito curto. "
                        f"Motivos: {fail_reasons}\n"
                        f"Persistindo marcador de falha.{ANSIStyle.RESET}\n"
                    )
                    sys.stdout.flush()

                    # Persistir marcador de falha em vez de string vazia
                    clean_result = (
                        f"## {task.output_artifact.upper()} — GERAÇÃO FALHOU\n\n"
                        f"O modelo não produziu conteúdo válido para este artefato.\n"
                        f"Motivos de falha: {', '.join(fail_reasons)}\n\n"
                        f"**Ação necessária:** Re-executar com modelo maior ou "
                        f"fornecer mais contexto.\n"
                    )
                else:
                    # FALHA PARCIAL: conteúdo existe mas incompleto
                    sys.stdout.write(
                        f"\n{ANSIStyle.YELLOW}⚠ [HARD GATE] Artefato "
                        f"'{task.output_artifact}' incompleto. "
                        f"Motivos: {fail_reasons}\n"
                        f"Completude: {int(validation.get('completeness_score', 0)*100)}% "
                        f"(mínimo: {int(validator.MIN_COMPLETENESS.get(artifact_type_tag, 0.6)*100)}%)\n"
                        f"Persistindo com aviso.{ANSIStyle.RESET}\n"
                    )
                    sys.stdout.flush()

                    # Adicionar aviso no topo do artefato
                    warning_header = (
                        f"<!-- AVISO: Artefato com completude abaixo do threshold. "
                        f"Seções faltantes: {validation.get('missing_sections', [])} -->\n\n"
                    )
                    clean_result = warning_header + clean_result

            # 3. Store result
            self.artifact_store.write(
                name=task.output_artifact,
                content=clean_result,
                artifact_type=self._get_artifact_type_from_task(task),
                created_by=task.agent_name
            )
            self.blackboard.set_task_status(task.task_id, TaskStatus.COMPLETED)
            
            # FASE 8.0b: Log success and save individual artifact
            if self.logger:
                self.logger.log(task.task_id, "TASK_END", agent=task.agent_name, data={"status": "COMPLETED"})
                self.logger.save_artifact(task.output_artifact, clean_result, created_by=task.agent_name)

        except Exception as e:
            self.blackboard.set_task_status(task.task_id, TaskStatus.FAILED)
            # FASE 8.0b: Log error
            if self.logger:
                self.logger.log(task.task_id, "ERROR", agent=task.agent_name, data={"error": str(e)})
            raise e

    def _post_process_output(self, text: str) -> str:
        """Remove preâmbulos e conclusões típicas de Chat Interface."""
        bad_starts = [
            "Certamente", "Com certeza", "Aqui está", "Entendido", 
            "Com base no", "Analisando o", "Como solicitado", "Segue o",
            "Okay", "Let's", "I will", "Based on", "Here is", "Sure",
            "Entendi", "Com base na", "De acordo"
        ]
        
        lines = text.split('\n')
        start_idx = 0
        
        for i, line in enumerate(lines[:10]):
            line_strip = line.strip()
            if not line_strip:
                start_idx = i + 1
                continue
            
            line_lower = line_strip.lower()
            # Se a linha começa com um bad start, removemos ela.
            # Mas não removemos se for um heading (##) ou lista (- ) ou tabela (|)
            is_noise = any(line_lower.startswith(b.lower()) for b in bad_starts)
            is_struct = line_strip.startswith(('#', '-', '|')) or re.match(r'^\d+\.', line_strip)
            
            if is_noise and not is_struct:
                start_idx = i + 1
            else:
                # Encontramos conteúdo real
                break
        
        clean_text = '\n'.join(lines[start_idx:]).strip()
        
        # Remove tags de pensamento residuais
        if "<think>" in clean_text:
            clean_text = re.sub(r'<think>.*?</think>', '', clean_text, flags=re.DOTALL).strip()
            
        return clean_text

    def _handle_human_gate(self, task: TaskDefinition, context: str) -> str:
        """Interage com o usuário para aprovação."""
        if "human_gate_callback" in self.agents:
            # Passa apenas o resumo para o human gate se for muito grande
            short_context = context[:2000] + "..." if len(context) > 2000 else context
            return self.agents["human_gate_callback"](short_context)
        return "APPROVED"

    def _get_artifact_type_from_task(self, task: TaskDefinition) -> str:
        if task.task_type == "HUMAN_GATE":
            return "decision"
        if "review" in task.output_artifact:
            return "review"
        if "transcript" in task.output_artifact:
            return "transcript"
        if "security" in task.output_artifact:
            return "security_review"
        return "document"

    def _get_artifact_tag_for_validator(self, task: TaskDefinition) -> str:
        """Mapeia task_id/output_artifact para o tipo esperado pelo OutputValidator."""
        mapping = {
            "prd": "prd",
            "system_design": "system_design",
            "prd_review": "review",
            "security_review": "security_review",
            "development_plan": "plan",
            "prd_final": "prd_final",  # FASE 8.0a: Valida como prd_final
        }
        return mapping.get(task.output_artifact, "document")
