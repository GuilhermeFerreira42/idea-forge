from typing import Dict, Any, Optional
import datetime
import json
import os

class Blackboard:
    """Estado global centralizado do pipeline."""

    def __init__(self) -> None:
        self.variables: Dict[str, Any] = {
            "pipeline_started_at": datetime.datetime.now().isoformat(),
            "completed_tasks": 0
        }
        self.task_statuses: Dict[str, str] = {}
        self.artifact_registry: Dict[str, Dict[str, Any]] = {}

    def set_variable(self, key: str, value: Any) -> None:
        """Define uma variável global."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Recupera variável global."""
        return self.variables.get(key, default)

    def set_task_status(self, task_id: str, status: Any) -> None:
        """Atualiza status de uma task na DAG."""
        # status should ideally be a TaskStatus enum, but string for now is fine
        self.task_statuses[task_id] = str(status)
        if str(status) == "completed":
            self.variables["completed_tasks"] = sum(1 for s in self.task_statuses.values() if s == "completed")

    def get_task_status(self, task_id: str) -> Optional[str]:
        """Recupera status de uma task."""
        return self.task_statuses.get(task_id)

    def get_all_task_statuses(self) -> Dict[str, str]:
        """Retorna mapa completo de status."""
        return self.task_statuses.copy()

    def update_artifact_registry(self, name: str, version: int) -> None:
        """Atualiza o registro de artefatos."""
        if name not in self.artifact_registry:
            self.artifact_registry[name] = {"latest_version": version, "versions": [version]}
        else:
            self.artifact_registry[name]["latest_version"] = version
            if version not in self.artifact_registry[name]["versions"]:
                self.artifact_registry[name]["versions"].append(version)

    def snapshot(self) -> Dict[str, Any]:
        """Serializa o estado completo para persistência."""
        return {
            "variables": self.variables,
            "task_statuses": self.task_statuses,
            "artifact_registry": self.artifact_registry
        }

    @classmethod
    def from_snapshot(cls, data: Dict[str, Any]) -> 'Blackboard':
        """Reconstrói Blackboard a partir de snapshot persistido."""
        bb = cls()
        bb.variables = data.get("variables", {})
        bb.task_statuses = data.get("task_statuses", {})
        bb.artifact_registry = data.get("artifact_registry", {})
        return bb

    def persist_to_disk(self, filepath: str = ".forge/blackboard_state.json") -> None:
        """Salva o estado do blackboard em disco."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.snapshot(), f, indent=2)

    @classmethod
    def load_from_disk(cls, filepath: str = ".forge/blackboard_state.json") -> 'Blackboard':
        """Carrega o estado do blackboard do disco."""
        if not os.path.exists(filepath):
            return cls()
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return cls.from_snapshot(data)
