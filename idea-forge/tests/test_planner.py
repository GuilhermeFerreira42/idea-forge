import pytest
from src.core.planner import Planner, TaskDefinition, TaskStatus
from src.core.blackboard import Blackboard
from src.core.artifact_store import ArtifactStore

class MockAgent:
    def __init__(self, return_val="success"):
        self.return_val = return_val
        self.called_with = []

    def generate_prd(self, idea, context=""):
        self.called_with.append((idea, context))
        return self.return_val

    def review_artifact(self, content, context=""):
        self.called_with.append((content, context))
        return "critique"

def test_planner_dag_initialization():
    bb = Blackboard()
    store = ArtifactStore(bb, persist_dir=".tmp_planner")
    planner = Planner(bb, store, agents={})
    planner.load_default_dag()
    
    # FASE 4: Agora são 7 tasks
    assert len(planner.dag) == 7
    assert bb.get_task_status("TASK_01") == str(TaskStatus.PENDING)

def test_planner_dependency_check():
    bb = Blackboard()
    store = ArtifactStore(bb, persist_dir=".tmp_planner")
    planner = Planner(bb, store, agents={})
    planner.load_default_dag()
    
    t2 = [t for t in planner.dag if t.task_id == "TASK_02"][0]
    assert planner._check_dependencies(t2) == False
    
    bb.set_task_status("TASK_01", TaskStatus.COMPLETED)
    assert planner._check_dependencies(t2) == True

def test_planner_execution_simple():
    bb = Blackboard()
    store = ArtifactStore(bb, persist_dir=".tmp_planner")
    pm_agent = MockAgent("PRD CONTENT")
    agents = {"product_manager": pm_agent}
    
    planner = Planner(bb, store, agents=agents)
    
    # Custom simple DAG for testing
    task = TaskDefinition(
        task_id="T1",
        agent_name="product_manager",
        method_name="generate_prd",
        input_artifacts=["user_idea"],
        output_artifact="prd"
    )
    planner.dag = [task]
    bb.set_task_status("T1", TaskStatus.PENDING)
    
    store.write("user_idea", "My Idea", "raw_input", "user")
    planner._execute_task(task)
    
    assert bb.get_task_status("T1") == str(TaskStatus.COMPLETED)
    assert store.read("prd").content == "PRD CONTENT"
    assert pm_agent.called_with[0][0] == "My Idea"

def test_planner_pipeline_flow():
    bb = Blackboard()
    store = ArtifactStore(bb, persist_dir=".tmp_planner")
    pm = MockAgent("PRD")
    critic = MockAgent("CRITIQUE")
    agents = {
        "product_manager": pm,
        "critic": critic,
        "human_gate_callback": lambda x: "APPROVED"
    }
    
    planner = Planner(bb, store, agents=agents)
    # Subset of DAG
    planner.dag = [
        TaskDefinition("TASK_01", "product_manager", "generate_prd", ["user_idea"], "prd"),
        TaskDefinition("TASK_02", "critic", "review_artifact", ["prd"], "prd_review", requires=["TASK_01"]),
        TaskDefinition("TASK_03", "system", "human_gate", ["prd", "prd_review"], "approval", requires=["TASK_02"], task_type="HUMAN_GATE")
    ]
    for t in planner.dag:
        bb.set_task_status(t.task_id, TaskStatus.PENDING)
        
    result = planner.execute_pipeline("START")
    
    assert bb.get_task_status("TASK_03") == str(TaskStatus.COMPLETED)
    assert store.exists("prd")
    assert store.exists("prd_review")
    assert store.exists("approval")
