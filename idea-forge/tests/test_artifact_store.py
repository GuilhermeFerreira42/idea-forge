import pytest
import os
from src.core.artifact_store import Artifact, ArtifactStore
from src.core.blackboard import Blackboard

def test_artifact_creation():
    art = Artifact(name="test", content="content", artifact_type="document", version=1, created_by="agent")
    assert art.name == "test"
    assert art.content == "content"
    assert art.fingerprint != ""
    assert art.token_estimate() == len("content") // 4

def test_artifact_store_write_read():
    bb = Blackboard()
    store = ArtifactStore(bb, persist_dir=".tmp_artifacts")
    
    art1 = store.write("prd", "content v1", "document", "pm_agent")
    assert art1.version == 1
    assert bb.artifact_registry["prd"]["latest_version"] == 1
    
    art2 = store.write("prd", "content v2", "document", "pm_agent")
    assert art2.version == 2
    assert bb.artifact_registry["prd"]["latest_version"] == 2
    
    read_latest = store.read("prd")
    assert read_latest.version == 2
    assert read_latest.content == "content v2"
    
    read_v1 = store.read("prd", version=1)
    assert read_v1.version == 1
    assert read_v1.content == "content v1"

def test_artifact_store_context():
    store = ArtifactStore(None)
    store.write("art1", "Hello World", "document", "agent")
    store.write("art2", "Second Artifact", "document", "agent")
    
    context = store.get_context_for_agent(["art1", "art2"])
    assert "=== ARTIFACT: art1" in context
    assert "Hello World" in context
    assert "=== ARTIFACT: art2" in context
    assert "Second Artifact" in context

def test_artifact_store_context_truncation():
    store = ArtifactStore(None)
    large_content = "A" * 4000 # ~1000 tokens
    store.write("large", large_content, "document", "agent")
    
    context = store.get_context_for_agent(["large"], max_tokens=100)
    assert "[TRUNCATED]" in context
    # Rough check on length (100 tokens * 4 chars + some header padding)
    assert len(context) < 1000 
