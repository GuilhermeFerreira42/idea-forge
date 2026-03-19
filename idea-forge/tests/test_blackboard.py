import pytest
import os
import json
from src.core.blackboard import Blackboard

def test_blackboard_variables():
    bb = Blackboard()
    bb.set_variable("test_key", "test_value")
    assert bb.get_variable("test_key") == "test_value"
    assert bb.get_variable("non_existent", "default") == "default"

def test_blackboard_task_status():
    bb = Blackboard()
    bb.set_task_status("TASK_01", "completed")
    assert bb.get_task_status("TASK_01") == "completed"
    assert bb.get_variable("completed_tasks") == 1
    
    bb.set_task_status("TASK_02", "pending")
    assert bb.get_task_status("TASK_02") == "pending"
    assert bb.get_variable("completed_tasks") == 1

def test_blackboard_snapshot():
    bb = Blackboard()
    bb.set_variable("v1", 123)
    bb.set_task_status("T1", "completed")
    bb.update_artifact_registry("art1", 1)
    
    snapshot = bb.snapshot()
    bb2 = Blackboard.from_snapshot(snapshot)
    
    assert bb2.get_variable("v1") == 123
    assert bb2.get_task_status("T1") == "completed"
    assert bb2.artifact_registry["art1"]["latest_version"] == 1

def test_blackboard_persistence(tmp_path):
    persist_file = tmp_path / "bb_state.json"
    bb = Blackboard()
    bb.set_variable("persistent_key", "value")
    bb.persist_to_disk(str(persist_file))
    
    assert os.path.exists(persist_file)
    
    bb2 = Blackboard.load_from_disk(str(persist_file))
    assert bb2.get_variable("persistent_key") == "value"
