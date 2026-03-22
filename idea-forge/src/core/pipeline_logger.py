"""
pipeline_logger.py — Logger estruturado do pipeline completo.

Captura TODOS os eventos do pipeline em formato JSONL para
análise posterior. Cada linha é um JSON independente.

Eventos registrados:
- PIPELINE_INIT / PIPELINE_END
- TASK_START / TASK_COMPLETE / TASK_FAIL
- PASS_START / PASS_VALID / PASS_FAIL / PASS_RETRY
- LLM_REQUEST / LLM_RESPONSE
- VALIDATION
- DEBATE_ROUND_START / DEBATE_PROPONENT / DEBATE_CRITIC
- HARD_GATE
- ERROR

Uso:
    logger = PipelineLogger()
    logger.log("TASK_START", {"task_id": "TASK_01"})
    logger.close()

Singleton:
    init_pipeline_logger()  # Uma vez no controller
    get_pipeline_logger()   # Em qualquer módulo
"""

import json
import time
import datetime
import os
from typing import Any, Dict, List, Optional


class PipelineLogger:
    """Logger estruturado que captura todo o pipeline em JSONL."""

    def __init__(self, log_dir: str = ".forge/logs"):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = os.path.join(log_dir, f"pipeline_{timestamp}.jsonl")
        self.start_time = time.time()
        self._file = open(self.filepath, "w", encoding="utf-8")

        # Primeiro evento
        self.log("PIPELINE_INIT", {
            "timestamp": datetime.datetime.now().isoformat(),
            "log_file": self.filepath,
        })

    def log(self, event_type: str, data: Dict[str, Any] = None,
            truncate_fields: Optional[List[str]] = None,
            max_field_len: int = 3000) -> None:
        """
        Registra um evento no log.

        Args:
            event_type: Tipo do evento (TASK_START, LLM_REQUEST, etc)
            data: Dados do evento (dict)
            truncate_fields: Campos para truncar (ex: ["prompt", "content"])
            max_field_len: Tamanho máximo de campos truncados
        """
        entry = {
            "t": event_type,
            "ts": round(time.time() - self.start_time, 3),
            "wall": datetime.datetime.now().isoformat(),
        }

        if data:
            if truncate_fields:
                data = dict(data)  # Cópia para não mutar original
                for field in truncate_fields:
                    if field in data and isinstance(data[field], str):
                        if len(data[field]) > max_field_len:
                            original_len = len(data[field])
                            data[field] = (
                                data[field][:max_field_len]
                                + f"\n[TRUNCATED: {original_len} chars total]"
                            )
            entry["d"] = data

        try:
            self._file.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._file.flush()  # Flush imediato para não perder em crash
        except Exception:
            pass  # Logger nunca deve crashar o pipeline

    def log_task(self, task_id: str, status: str,
                 details: Dict[str, Any] = None) -> None:
        """Atalho para logar transição de task."""
        self.log(f"TASK_{status}", {
            "task_id": task_id,
            **(details or {}),
        })

    def log_pass(self, pass_id: str, event: str,
                 details: Dict[str, Any] = None) -> None:
        """Atalho para logar evento de pass."""
        self.log(f"PASS_{event}", {
            "pass_id": pass_id,
            **(details or {}),
        })

    def log_llm_request(self, agent: str, role: str, prompt: str,
                        pass_info: str = "", attempt: int = 1) -> None:
        """Atalho para logar requisição ao LLM."""
        self.log("LLM_REQUEST", {
            "agent": agent,
            "role": role,
            "prompt": prompt,
            "pass": pass_info,
            "attempt": attempt,
            "prompt_chars": len(prompt),
            "prompt_tokens_est": len(prompt) // 4,
        }, truncate_fields=["prompt"])

    def log_llm_response(self, agent: str, content: str,
                         thinking: str = "", tokens_processed: int = 0,
                         duration_ms: int = 0) -> None:
        """Atalho para logar resposta do LLM."""
        self.log("LLM_RESPONSE", {
            "agent": agent,
            "content": content,
            "thinking_chars": len(thinking) if thinking else 0,
            "content_chars": len(content),
            "tokens_processed": tokens_processed,
            "duration_ms": duration_ms,
        }, truncate_fields=["content"])

    def log_validation(self, artifact: str, validation_result: Dict) -> None:
        """Atalho para logar resultado de validação."""
        # Remover campos muito grandes do validation_result
        safe_result = {k: v for k, v in validation_result.items()
                       if k != "present_sections"}  # Evitar listas longas
        self.log("VALIDATION", {
            "artifact": artifact,
            **safe_result,
        })

    def log_error(self, context: str, error: str,
                  traceback_str: str = "") -> None:
        """Atalho para logar erro."""
        self.log("ERROR", {
            "context": context,
            "error": error,
            "traceback": traceback_str[:2000] if traceback_str else "",
        })

    def get_filepath(self) -> str:
        """Retorna o caminho do arquivo de log."""
        return self.filepath

    def close(self) -> None:
        """Fecha o arquivo de log com evento final."""
        total_time = time.time() - self.start_time
        self.log("PIPELINE_END", {
            "total_duration_seconds": round(total_time, 2),
            "total_duration_human": f"{int(total_time // 60)}m {int(total_time % 60)}s",
        })
        try:
            self._file.close()
        except Exception:
            pass


# ─── Singleton Global ──────────────────────────────────
_global_logger: Optional[PipelineLogger] = None


def init_pipeline_logger(log_dir: str = ".forge/logs") -> PipelineLogger:
    """Inicializa o logger global do pipeline."""
    global _global_logger
    _global_logger = PipelineLogger(log_dir)
    return _global_logger


def get_pipeline_logger() -> Optional[PipelineLogger]:
    """Retorna o logger global (None se não inicializado)."""
    return _global_logger
