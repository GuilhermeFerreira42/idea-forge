from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import hashlib
import datetime
import json
import os

@dataclass(frozen=True)
class Artifact:
    """
    Artefato imutável produzido por um agente durante o pipeline.
    
    Invariantes:
    - Uma vez criado, NUNCA é modificado (frozen=True)
    - Novas versões criam novos objetos Artifact
    - fingerprint é SHA-256 do content
    """
    name: str
    content: str
    artifact_type: str      # "raw_input" | "document" | "review" | "transcript" | "decision"
    version: int
    created_by: str
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    fingerprint: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.fingerprint:
            fp = hashlib.sha256(self.content.encode('utf-8')).hexdigest()[:16]
            object.__setattr__(self, 'fingerprint', fp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "content": self.content,
            "artifact_type": self.artifact_type,
            "version": self.version,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "fingerprint": self.fingerprint,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Artifact':
        return cls(**data)

    def token_estimate(self) -> int:
        """Estimativa de tokens: ~4 chars por token para português."""
        return len(self.content) // 4

class ArtifactStore:
    """Gerenciador de artefatos tipados com versionamento."""

    def __init__(self, blackboard: Any, persist_dir: str = ".forge/artifacts"):
        self.blackboard = blackboard
        self.persist_dir = persist_dir
        self.artifacts: Dict[str, Dict[int, Artifact]] = {}
        
        if not os.path.exists(self.persist_dir):
            os.makedirs(self.persist_dir, exist_ok=True)

    def write(self, name: str, content: str, artifact_type: str, created_by: str, metadata: Dict[str, Any] = None) -> Artifact:
        """Escreve um artefato. Incrementa versão automaticamente."""
        if name not in self.artifacts:
            self.artifacts[name] = {}
            version = 1
        else:
            version = max(self.artifacts[name].keys()) + 1

        artifact = Artifact(
            name=name,
            content=content,
            artifact_type=artifact_type,
            version=version,
            created_by=created_by,
            metadata=metadata or {}
        )
        
        self.artifacts[name][version] = artifact
        
        # Update blackboard registry
        if self.blackboard:
            self.blackboard.update_artifact_registry(name, version)
            
        return artifact

    def read(self, name: str, version: int = None) -> Optional[Artifact]:
        """Lê artefato. Se version=None, retorna a mais recente."""
        if name not in self.artifacts:
            return None
            
        if version is None:
            version = max(self.artifacts[name].keys())
            
        return self.artifacts[name].get(version)

    def read_multiple(self, names: List[str]) -> Dict[str, Artifact]:
        """Lê múltiplos artefatos mais recentes."""
        results = {}
        for name in names:
            art = self.read(name)
            if art:
                results[name] = art
        return results

    def exists(self, name: str) -> bool:
        """Verifica se artefato existe."""
        return name in self.artifacts

    def get_context_for_agent(self, artifact_names: List[str], max_tokens: int = 1500, usage_hint: str = "reference") -> str:
        """
        Hot-load: Monta string de contexto para injeção no prompt.
        
        FASE 3.1: Adicionado usage_hint para context framing.
        """
        HINT_HEADERS = {
            "reference": "↓ REFERÊNCIA — NÃO repita este conteúdo na sua resposta ↓",
            "review": "↓ ARTEFATO PARA REVISÃO — Analise criticamente ↓",
            "transform": "↓ INPUT — Transforme no formato solicitado ↓",
            "summary": "↓ SUMÁRIO — Apenas campos-chave do artefato ↓",
        }

        context_parts = []
        current_tokens = 0

        for name in artifact_names:
            artifact = self.read(name)
            if not artifact:
                continue

            hint = HINT_HEADERS.get(usage_hint, HINT_HEADERS["reference"])
            header = (
                f"=== ARTIFACT: {artifact.name} "
                f"(v{artifact.version}, {artifact.artifact_type}) ===\n"
                f"{hint}\n"
            )
            footer = "\n=== END ARTIFACT ===\n"
            
            content = artifact.content
            
            # Simple summary logic: take first few lines if summary hint is used
            if usage_hint == "summary" and len(content) > 500:
                lines = content.split('\n')
                content = '\n'.join(lines[:10]) + "... [SUMMARY ONLY]"

            # Basic budget management
            overhead = (len(header) + len(footer)) // 4
            available_for_content = max_tokens - current_tokens - overhead
            
            if (len(content) // 4) > available_for_content:
                allowed_chars = max(0, available_for_content * 4)
                content = content[:allowed_chars] + "... [TRUNCATED]"

            context_parts.append(f"{header}{content}{footer}")
            current_tokens += len(context_parts[-1]) // 4
            
            if current_tokens >= max_tokens:
                break

        return "\n".join(context_parts)

    def persist_to_disk(self) -> None:
        """Salva todos os artefatos em disco como JSON."""
        for name, versions in self.artifacts.items():
            for version, artifact in versions.items():
                filename = f"{name}_v{version}.json"
                path = os.path.join(self.persist_dir, filename)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(artifact.to_dict(), f, indent=2)

    def load_from_disk(self) -> None:
        """Carrega artefatos do disco."""
        if not os.path.exists(self.persist_dir):
            return

        for filename in os.listdir(self.persist_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.persist_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        artifact = Artifact.from_dict(data)
                        
                        if artifact.name not in self.artifacts:
                            self.artifacts[artifact.name] = {}
                        self.artifacts[artifact.name][artifact.version] = artifact
                except Exception:
                    continue
