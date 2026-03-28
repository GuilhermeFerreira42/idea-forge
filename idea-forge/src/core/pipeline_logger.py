"""
pipeline_logger.py — Logger estruturado para execuções do pipeline IdeaForge.

FASE 8.0b:
- Captura eventos do pipeline em formato JSONL (um JSON por linha)
- Salva artefatos individuais em disco como arquivos .md separados
- Gera sumário legível ao final da execução
- TODA operação de I/O está em try/except — falha no log ≠ falha no pipeline

Contrato:
    Input: Eventos do pipeline (task_id, event_type, agent, data)
    Output: Arquivo .jsonl + artefatos .md + sumário .md

NÃO contém lógica de negócio. NÃO conhece agentes. Apenas persiste eventos.
"""

import os
import json
import datetime
from typing import Dict, Any, List


class PipelineLogger:
    """Logger JSONL para rastreamento estruturado de execuções."""
    
    def __init__(self, run_id: str, log_dir: str = ".forge/logs"):
        """
        Inicializa logger. Cria diretórios necessários.
        Lança OSError se não conseguir criar diretórios (capturada pelo Controller).
        """
        self.run_id = run_id
        # Garante que o diretório base existe
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        self.run_dir = os.path.join(log_dir, run_id)
        self.artifacts_dir = os.path.join(self.run_dir, "artifacts")
        self.log_path = os.path.join(self.run_dir, "pipeline.jsonl")
        self.summary_path = os.path.join(self.run_dir, "pipeline_summary.md")
        self._events: List[Dict[str, Any]] = []
        
        # Esta é a ÚNICA operação que pode lançar exceção para o chamador
        os.makedirs(self.artifacts_dir, exist_ok=True)
    
    def log(self, task_id: str, event_type: str, agent: str = "",
            data: Dict[str, Any] = None) -> None:
        """
        Persiste evento como linha JSONL.
        NUNCA lança exceção para o chamador.
        """
        event = {
            "timestamp": datetime.datetime.now().isoformat(),
            "run_id": self.run_id,
            "task_id": task_id,
            "event_type": event_type,
            "agent": agent,
            "data": data or {}
        }
        self._events.append(event)
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            pass  # Evento salvo em memória, escrita em disco falhou silenciosamente
    
    def log_validation(self, task_id: str, artifact_type: str,
                       validation_result: Dict, content_preview: str = "") -> None:
        """Registra resultado de validação com preview truncado."""
        self.log(
            task_id=task_id,
            event_type="VALIDATION",
            data={
                "artifact_type": artifact_type,
                "valid": validation_result.get("valid", False),
                "completeness": validation_result.get("completeness_score", 0),
                "density": validation_result.get("density_score", 0),
                "table_count": validation_result.get("table_count", 0),
                "fail_reasons": validation_result.get("fail_reasons", []),
                "missing_sections": validation_result.get("missing_sections", []),
                "content_preview": content_preview[:200] if content_preview else ""
            }
        )
    
    def save_artifact(self, name: str, content: str, created_by: str = "") -> str:
        """
        Salva artefato individual como .md.
        Retorna path do arquivo, ou "" se falhar.
        NUNCA lança exceção para o chamador.
        """
        filepath = os.path.join(self.artifacts_dir, f"{name}.md")
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {name.upper().replace('_', ' ')}\n\n")
                if created_by:
                    f.write(f"**Criado por:** {created_by}\n\n---\n\n")
                f.write(content)
        except OSError:
            filepath = ""
        
        self.log(
            task_id="ARTIFACT_SAVE",
            event_type="ARTIFACT_PERSISTED",
            agent=created_by,
            data={"name": name, "path": filepath, "chars": len(content)}
        )
        
        return filepath
    
    def finalize(self, blackboard_snapshot: Dict = None) -> str:
        """
        Gera sumário legível da execução.
        Retorna path do diretório da run, ou "" se falhar.
        NUNCA lança exceção para o chamador.
        """
        try:
            with open(self.summary_path, "w", encoding="utf-8") as f:
                f.write(f"# Pipeline Summary — {self.run_id}\n\n")
                f.write(f"**Total de eventos:** {len(self._events)}\n\n")
                
                # Timeline
                f.write("## Timeline\n\n")
                f.write("| Hora | Task | Evento | Detalhes |\n")
                f.write("|---|---|---|---|\n")
                for evt in self._events:
                    detail = self._format_event_detail(evt)
                    ts_short = evt["timestamp"].split("T")[1][:8] if "T" in evt["timestamp"] else ""
                    f.write(f"| {ts_short} | {evt['task_id']} | {evt['event_type']} | {detail} |\n")
                
                # Validações com falha
                failed = [e for e in self._events
                          if e["event_type"] == "VALIDATION"
                          and not e.get("data", {}).get("valid", True)]
                if failed:
                    f.write("\n## Validações com Falha\n\n")
                    for fv in failed:
                        d = fv.get("data", {})
                        f.write(f"- **{fv['task_id']}** ({d.get('artifact_type', '?')}): "
                                f"{d.get('fail_reasons', [])}\n")
                        missing = d.get("missing_sections", [])
                        if missing:
                            f.write(f"  Seções faltantes: {missing}\n")
                
                # Erros
                errors = [e for e in self._events if e["event_type"] == "ERROR"]
                if errors:
                    f.write("\n## Erros\n\n")
                    for err in errors:
                        f.write(f"- **{err['task_id']}**: {err.get('data', {}).get('error', 'desconhecido')}\n")
                
                f.write(f"\n---\n*Gerado por PipelineLogger — IdeaForge CLI Fase 8.0*\n")
            
            return self.run_dir
        except OSError:
            return ""
    
    def _format_event_detail(self, event: Dict) -> str:
        """Formata detalhes de um evento para a tabela do sumário."""
        evt_type = event.get("event_type", "")
        data = event.get("data", {})
        
        if evt_type == "TASK_START":
            return f"agent={event.get('agent', '')}"
        elif evt_type == "TASK_END":
            return f"status={data.get('status', '?')}"
        elif evt_type == "VALIDATION":
            return f"valid={data.get('valid')} compl={data.get('completeness', 0):.0%}"
        elif evt_type == "ERROR":
            return data.get("error", "")[:60]
        elif evt_type == "ARTIFACT_PERSISTED":
            return f"{data.get('name', '?')} ({data.get('chars', 0)} chars)"
        return ""
    
    def get_run_dir(self) -> str:
        """Retorna o diretório da execução atual."""
        return self.run_dir
