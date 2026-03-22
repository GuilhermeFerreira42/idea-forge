"""
test_pipeline_logger.py — Testes unitários para o PipelineLogger.
"""

import pytest
import json
import os
import tempfile
from src.core.pipeline_logger import (
    PipelineLogger, init_pipeline_logger, get_pipeline_logger
)


class TestPipelineLogger:
    """Testes para o PipelineLogger."""

    def test_creates_log_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=tmpdir)
            assert os.path.exists(logger.filepath)
            assert logger.filepath.endswith(".jsonl")
            logger.close()

    def test_log_writes_valid_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.log("TEST_EVENT", {"key": "value"})
            logger.close()

            with open(logger.filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Pelo menos 3 linhas: PIPELINE_INIT + TEST_EVENT + PIPELINE_END
            assert len(lines) >= 3

            for line in lines:
                data = json.loads(line)
                assert "t" in data  # event type
                assert "ts" in data  # timestamp relativo
                assert "wall" in data  # timestamp absoluto

    def test_log_event_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.log("MY_EVENT", {"foo": "bar", "num": 42})
            logger.close()

            with open(logger.filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Segunda linha é MY_EVENT (primeira é PIPELINE_INIT)
            event = json.loads(lines[1])
            assert event["t"] == "MY_EVENT"
            assert event["d"]["foo"] == "bar"
            assert event["d"]["num"] == 42
            assert event["ts"] >= 0

    def test_truncate_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=tmpdir)
            long_text = "A" * 5000
            logger.log("BIG_EVENT", {"prompt": long_text},
                        truncate_fields=["prompt"], max_field_len=100)
            logger.close()

            with open(logger.filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            event = json.loads(lines[1])
            assert len(event["d"]["prompt"]) < 200
            assert "TRUNCATED" in event["d"]["prompt"]

    def test_log_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.log_task("TASK_01", "START", {"agent": "pm"})
            logger.log_task("TASK_01", "COMPLETE", {"output_chars": 500})
            logger.close()

            with open(logger.filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            events = [json.loads(l) for l in lines]
            task_events = [e for e in events if e["t"].startswith("TASK_")]
            assert len(task_events) == 2
            assert task_events[0]["t"] == "TASK_START"
            assert task_events[1]["t"] == "TASK_COMPLETE"

    def test_log_pass(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.log_pass("prd_p1", "START", {"attempt": 1})
            logger.log_pass("prd_p1", "VALID", {"char_count": 200})
            logger.close()

            with open(logger.filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            events = [json.loads(l) for l in lines]
            pass_events = [e for e in events if e["t"].startswith("PASS_")]
            assert len(pass_events) == 2

    def test_log_llm_request_response(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.log_llm_request("pm", "product_manager", "Generate PRD")
            logger.log_llm_response("pm", "## Objetivo\n- Teste", tokens_processed=50)
            logger.close()

            with open(logger.filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            events = [json.loads(l) for l in lines]
            llm_events = [e for e in events if e["t"].startswith("LLM_")]
            assert len(llm_events) == 2

    def test_log_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.log_validation("prd", {
                "valid": True,
                "completeness_score": 1.0,
                "density_score": 0.95,
                "table_count": 5,
            })
            logger.close()

            with open(logger.filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            events = [json.loads(l) for l in lines]
            val_events = [e for e in events if e["t"] == "VALIDATION"]
            assert len(val_events) == 1
            assert val_events[0]["d"]["valid"] is True

    def test_log_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.log_error("test_context", "Something broke", "traceback...")
            logger.close()

            with open(logger.filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            events = [json.loads(l) for l in lines]
            err_events = [e for e in events if e["t"] == "ERROR"]
            assert len(err_events) == 1
            assert err_events[0]["d"]["error"] == "Something broke"

    def test_pipeline_end_has_duration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=tmpdir)
            logger.close()

            with open(logger.filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            last_event = json.loads(lines[-1])
            assert last_event["t"] == "PIPELINE_END"
            assert "total_duration_seconds" in last_event["d"]
            assert "total_duration_human" in last_event["d"]

    def test_logger_never_crashes_pipeline(self):
        """Logger com arquivo já fechado não deve lançar exceção."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=tmpdir)
            logger._file.close()  # Forçar fechamento
            # Não deve lançar exceção
            logger.log("AFTER_CLOSE", {"test": True})
