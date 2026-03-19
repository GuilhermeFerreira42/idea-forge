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
                 think: bool = False) -> None:
        self.blackboard = blackboard
        self.artifact_store = artifact_store
        self.agents = agents
        self.provider = provider
        self.think = think
        self.dag: List[TaskDefinition] = []

    def load_default_dag(self) -> None:
        """Carrega a DAG padrão de 6 tasks conforme o Blueprint."""
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
            TaskDefinition(
                task_id="TASK_05",
                agent_name="debate_engine",
                method_name="run",
                input_artifacts=["prd", "system_design"],
                output_artifact="debate_transcript",
                requires=["TASK_04"],
                task_type="ENGINE"
            ),
            TaskDefinition(
                task_id="TASK_06",
                agent_name="plan_generator",
                method_name="generate_plan",
                input_artifacts=["prd", "system_design", "debate_transcript"],
                output_artifact="development_plan",
                requires=["TASK_05"],
                task_type="ENGINE"
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
        """Executa uma task individual."""
        self.blackboard.set_task_status(task.task_id, TaskStatus.RUNNING)
        
        try:
            # 1. Hot-load context
            context = self.artifact_store.get_context_for_agent(task.input_artifacts, task.max_context_tokens)
            
            # 2. Prepare inputs for the agent method
            # NOTE: This logic will need to be refined as we implement the actual agents
            agent = self.agents.get(task.agent_name)
            
            if task.task_type == "HUMAN_GATE":
                # Handle human gate (this will interact with CLI via callback or direct input)
                # For now, let's assume a callback is provided in agents or handled by Controller
                result = self._handle_human_gate(task, context)
            else:
                # Find the method
                method = getattr(agent, task.method_name)
                
                # Dynamic call based on input artifacts (PM needs first input as 'idea', others as 'context')
                # This is a bit brittle, but follows the blueprint's idea of "PM(idea, context)"
                first_input_art = self.artifact_store.read(task.input_artifacts[0])
                first_input = first_input_art.content if first_input_art else ""
                
                if len(task.input_artifacts) > 1:
                    # Pass the first input and the rest as context
                    result = method(first_input, context)
                else:
                    # Just pass the first input (which could be the context itself for some agents)
                    result = method(first_input)

            # 3. Store result
            self.artifact_store.write(
                name=task.output_artifact,
                content=str(result),
                artifact_type=self._get_artifact_type_from_task(task),
                created_by=task.agent_name
            )
            self.blackboard.set_task_status(task.task_id, TaskStatus.COMPLETED)
            
        except Exception as e:
            self.blackboard.set_task_status(task.task_id, TaskStatus.FAILED)
            # Re-raise or handle locally? For now let's raise to see errors
            raise e

    def _handle_human_gate(self, task: TaskDefinition, context: str) -> str:
        """Interage com o usuário para aprovação."""
        # This will be overridden or implemented to call back into CLI
        # For tests, we'll mock this
        if "human_gate_callback" in self.agents:
            return self.agents["human_gate_callback"](context)
        return "APPROVED" # Default for headless execution

    def _get_artifact_type_from_task(self, task: TaskDefinition) -> str:
        if task.task_type == "HUMAN_GATE":
            return "decision"
        if "review" in task.output_artifact:
            return "review"
        if "transcript" in task.output_artifact:
            return "transcript"
        return "document"
