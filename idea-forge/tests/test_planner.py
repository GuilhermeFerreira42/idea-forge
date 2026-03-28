import pytest
import sys
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
        return self.return_val

    def design_system(self, prd, approval_decision):
        self.called_with.append((prd, approval_decision))
        return self.return_val

    def review_security(self, system_design, prd_context=""):
        self.called_with.append((system_design, prd_context))
        return self.return_val

    def consolidate_prd(self, artifacts_context, original_idea=""):
        self.called_with.append((artifacts_context, original_idea))
        return self.return_val

def test_planner_dag_initialization():
    bb = Blackboard()
    store = ArtifactStore(bb, persist_dir=".tmp_planner")
    planner = Planner(bb, store, agents={})
    planner.load_default_dag()
    
    # FASE 7.1: Agora são 8 tasks
    assert len(planner.dag) == 8
    assert bb.get_task_status("TASK_01") == str(TaskStatus.PENDING)
    assert bb.get_task_status("TASK_07") == str(TaskStatus.PENDING)

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
    # FASE 7: Mock PRD longo para passar na validação NEXUS
    prd_content = (
        "## Objetivo\n- Teste\n\n## Problema\n| ID | P | I | R |\n|---|---|---|---|\n| P1 | X | Y | Z |\n\n"
        "## Público-Alvo\n## Princípios Arquiteturais\n## Requisitos Funcionais\n## Requisitos Não-Funcionais\n"
        "## Escopo MVP\n## Métricas de Sucesso\n## Dependências e Riscos\n## Diferenciais\n## Constraints Técnicos\n"
        "Texto longo para validação. " * 30
    )
    pm_agent = MockAgent(prd_content)
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
    
    status = bb.get_task_status("T1")
    actual_content = store.read("prd").content
    
    if actual_content != prd_content or status != str(TaskStatus.COMPLETED):
        print(f"\nDEBUG: Status={status}")
        print(f"DEBUG: Actual len={len(actual_content)}, Expected len={len(prd_content)}")
        if "AVISO" in actual_content:
            print("DEBUG: Warning detected in actual content!")
        # Use simple slice to show start of both
        print(f"DEBUG: Actual starts with: {actual_content[:100]!r}")
        print(f"DEBUG: Expected starts with: {prd_content[:100]!r}")
        
    assert status == str(TaskStatus.COMPLETED)
    assert actual_content.strip() == prd_content.strip()
    assert pm_agent.called_with[0][0] == "My Idea"

def test_planner_pipeline_flow():
    bb = Blackboard()
    store = ArtifactStore(bb, persist_dir=".tmp_planner")
    # Mock content that passes NEXUS validation
    content = "## Objetivo\n- Teste\n\n## Problema\n| ID | P | I | R |\n|---|---|---|---|\n| P1 | X | Y | Z |\n\n"
    content += "## Público-Alvo\n## Princípios Arquiteturais\n## Requisitos Funcionais\n## Requisitos Não-Funcionais\n"
    content += "## Escopo MVP\n## Métricas de Sucesso\n## Dependências e Riscos\n## Diferenciais\n## Constraints Técnicos\n"
    content += "Texto longo para validação. " * 30
    
    pm = MockAgent(content)
    critic_content = "## Score de Qualidade\n## Issues Identificadas\n## Verificação de Requisitos\n## Sumário\n## Recomendação\n"
    critic_content += "Critique text here that needs to be long enough to pass the validation threshold of 200 characters for reviews in the NEXUS standard. " * 5
    critic = MockAgent(critic_content)
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

def test_prd_final_validator_mapping():
    """FASE 8.0a: Verifica que prd_final é mapeado para tipo prd_final, não prd."""
    bb = Blackboard()
    store = ArtifactStore(bb, persist_dir=".tmp_planner")
    planner = Planner(bb, store, agents={})
    planner.load_default_dag()
    
    task_07 = [t for t in planner.dag if t.task_id == "TASK_07"][0]
    tag = planner._get_artifact_tag_for_validator(task_07)
    assert tag == "prd_final", f"Esperado 'prd_final', obtido '{tag}'"

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
