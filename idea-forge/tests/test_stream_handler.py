"""
test_stream_handler.py — Testes para o módulo de streaming e buffering.
"""

import pytest
import json
from src.core.stream_handler import (
    StreamHandler, InlineThinkParser, StreamResult, ANSIStyle
)


class TestInlineThinkParser:
    """Testes para o parser de tags <think> inline."""

    def test_no_think_tags(self):
        parser = InlineThinkParser()
        think, content = parser.process_chunk("Hello world")
        assert think == ""
        assert content == "Hello world"

    def test_complete_think_block(self):
        parser = InlineThinkParser()
        think, content = parser.process_chunk(
            "<think>reasoning here</think>actual response"
        )
        assert think == "reasoning here"
        assert content == "actual response"

    def test_think_across_multiple_chunks(self):
        parser = InlineThinkParser()

        t1, c1 = parser.process_chunk("<think>start of ")
        assert t1 == "start of "
        assert c1 == ""

        t2, c2 = parser.process_chunk("thinking</think>content here")
        assert t2 == "thinking"
        assert c2 == "content here"

    def test_content_before_think(self):
        parser = InlineThinkParser()
        think, content = parser.process_chunk(
            "prefix<think>thought</think>suffix"
        )
        assert think == "thought"
        assert content == "prefixsuffix"

    def test_multiple_think_blocks(self):
        parser = InlineThinkParser()
        think, content = parser.process_chunk(
            "<think>t1</think>c1<think>t2</think>c2"
        )
        assert think == "t1t2"
        assert content == "c1c2"

    def test_fragmented_open_tag(self):
        """Tag <think> dividida entre dois chunks."""
        parser = InlineThinkParser()
        t1, c1 = parser.process_chunk("hello<thi")
        # O parser deve reter "<thi" como possível início de tag
        t2, c2 = parser.process_chunk("nk>inside</think>after")
        
        assert parser.content_buffer == "helloafter"
        assert parser.think_buffer == "inside"

    def test_fragmented_close_tag(self):
        """Tag </think> dividida entre dois chunks."""
        parser = InlineThinkParser()
        t1, c1 = parser.process_chunk("<think>thought</thi")
        t2, c2 = parser.process_chunk("nk>content")
        
        assert parser.think_buffer == "thought"
        assert parser.content_buffer == "content"


class TestStreamHandler:
    """Testes para o StreamHandler principal."""

    def _make_line_iterator(self, chunks):
        """Helper: cria um iterador de linhas JSON simulando o Ollama."""
        for chunk in chunks:
            yield json.dumps(chunk).encode('utf-8')

    def test_native_thinking_field(self):
        """Modelo com campo 'thinking' nativo no JSON."""
        chunks = [
            {"thinking": "Let me analyze...", "response": "", "done": False},
            {"thinking": "The architecture...", "response": "", "done": False},
            {"thinking": "", "response": "Here is my ", "done": False},
            {"thinking": "", "response": "analysis.", "done": True},
        ]
        handler = StreamHandler(show_thinking=False)  # Suprimir output no teste
        result = handler.process_ollama_stream(self._make_line_iterator(chunks))

        assert result.thinking == "Let me analyze...The architecture..."
        assert result.content == "Here is my analysis."

    def test_inline_think_tags(self):
        """Modelo sem campo nativo — usa tags <think> inline."""
        chunks = [
            {"response": "<think>reasoning", "done": False},
            {"response": " step</think>", "done": False},
            {"response": "Final answer", "done": True},
        ]
        handler = StreamHandler(show_thinking=False)
        result = handler.process_ollama_stream(self._make_line_iterator(chunks))

        assert result.thinking == "reasoning step"
        assert result.content == "Final answer"

    def test_no_thinking_at_all(self):
        """Modelo sem nenhum pensamento — tudo é conteúdo."""
        chunks = [
            {"response": "Direct ", "done": False},
            {"response": "response.", "done": True},
        ]
        handler = StreamHandler(show_thinking=False)
        result = handler.process_ollama_stream(self._make_line_iterator(chunks))

        assert result.thinking == ""
        assert result.content == "Direct response."

    def test_empty_stream(self):
        """Stream vazio não causa erro."""
        handler = StreamHandler(show_thinking=False)
        result = handler.process_ollama_stream(iter([]))
        assert result.content == ""
        assert result.thinking == ""

    def test_malformed_json_skipped(self):
        """Linhas JSON malformadas são ignoradas."""
        lines = [
            b'{"response": "valid", "done": false}',
            b'not json at all',
            b'{"response": " end", "done": true}',
        ]
        handler = StreamHandler(show_thinking=False)
        result = handler.process_ollama_stream(iter(lines))
        assert result.content == "valid end"


# ── FASE 2: Testes adicionais ──────────────────────────────

class TestSilentProgressIndicator:
    """Testes para o indicador de progresso silencioso (Fase 2)."""

    def test_tick_increments_counter(self):
        from src.core.stream_handler import SilentProgressIndicator
        indicator = SilentProgressIndicator()
        indicator.tick()
        assert indicator._token_count == 1
        indicator.tick()
        assert indicator._token_count == 2

    def test_finish_resets_active(self):
        from src.core.stream_handler import SilentProgressIndicator
        indicator = SilentProgressIndicator()
        indicator.tick()  # Ativar
        assert indicator._is_active is True
        indicator.finish()
        assert indicator._is_active is False

    def test_finish_without_activation_is_noop(self):
        from src.core.stream_handler import SilentProgressIndicator
        indicator = SilentProgressIndicator()
        # Não deve lançar exceção
        indicator.finish()
        assert indicator._is_active is False


class TestStreamHandlerSilentMode:
    """Testes para o StreamHandler em modo show_thinking=False (Fase 2)."""

    def _make_line_iterator(self, chunks):
        for chunk in chunks:
            yield json.dumps(chunk).encode('utf-8')

    def test_silent_mode_still_captures_thinking(self):
        """Mesmo em modo silencioso, o thinking deve ser capturado no resultado."""
        chunks = [
            {"thinking": "Silent reasoning...", "response": "", "done": False},
            {"thinking": "", "response": "Final answer.", "done": True},
        ]
        handler = StreamHandler(show_thinking=False)
        result = handler.process_ollama_stream(self._make_line_iterator(chunks))

        # Thinking foi capturado mesmo sem ser exibido em dimmed
        assert result.thinking == "Silent reasoning..."
        assert result.content == "Final answer."

    def test_silent_mode_inline_tags(self):
        """Tags <think> inline em modo silencioso."""
        chunks = [
            {"response": "<think>internal</think>visible", "done": True},
        ]
        handler = StreamHandler(show_thinking=False)
        result = handler.process_ollama_stream(self._make_line_iterator(chunks))

        assert result.thinking == "internal"
        assert result.content == "visible"


class TestOllamaProviderPromptInjection:
    """Testes para a injeção de diretiva de resposta direta (Fase 2)."""

    def test_direct_mode_injects_directive(self):
        from src.models.ollama_provider import (
            OllamaProvider, DIRECT_RESPONSE_DIRECTIVE
        )
        provider = OllamaProvider(
            model_name="qwen3:8b", think=False, show_thinking=False
        )
        result = provider._build_prompt("Test prompt")
        assert result.startswith("IMPORTANT INSTRUCTION:")
        assert "Test prompt" in result

    def test_reasoning_mode_no_injection(self):
        from src.models.ollama_provider import OllamaProvider
        provider = OllamaProvider(
            model_name="qwen3:8b", think=True, show_thinking=True
        )
        result = provider._build_prompt("Test prompt")
        assert result == "Test prompt"

    def test_non_reasoning_model_no_injection(self):
        from src.models.ollama_provider import OllamaProvider
        provider = OllamaProvider(
            model_name="llama3:8b", think=False, show_thinking=False
        )
        result = provider._build_prompt("Test prompt")
        # llama3 não é modelo de reasoning, não injeta diretiva
        assert result == "Test prompt"


class TestAgentDirectMode:
    """Testes para o direct_mode nos agentes (Fase 2)."""

    def test_critic_direct_mode_prompt(self):
        from src.agents.critic_agent import CriticAgent, DIRECT_MODE_SUFFIX
        from src.models.model_provider import ModelProvider
        
        class MockProvider(ModelProvider):
            def generate(self, prompt, context=None, role="user"): return ""
            def generate_with_thinking(self, prompt, context=None, role="user"): pass
            
        provider = MockProvider()
        critic = CriticAgent(provider, direct_mode=True)
        assert "Do NOT use <think> tags" in critic.system_prompt

    def test_critic_normal_mode_prompt(self):
        from src.agents.critic_agent import CriticAgent
        from src.models.model_provider import ModelProvider
        
        class MockProvider(ModelProvider):
            def generate(self, prompt, context=None, role="user"): return ""
            def generate_with_thinking(self, prompt, context=None, role="user"): pass
            
        provider = MockProvider()
        critic = CriticAgent(provider, direct_mode=False)
        assert "Do NOT use <think> tags" not in critic.system_prompt

    def test_proponent_direct_mode_prompt(self):
        from src.agents.proponent_agent import ProponentAgent, DIRECT_MODE_SUFFIX
        from src.models.model_provider import ModelProvider
        
        class MockProvider(ModelProvider):
            def generate(self, prompt, context=None, role="user"): return ""
            def generate_with_thinking(self, prompt, context=None, role="user"): pass
            
        provider = MockProvider()
        proponent = ProponentAgent(provider, direct_mode=True)
        assert "Do NOT use <think> tags" in proponent.system_prompt

    def test_proponent_normal_mode_prompt(self):
        from src.agents.proponent_agent import ProponentAgent
        from src.models.model_provider import ModelProvider
        
        class MockProvider(ModelProvider):
            def generate(self, prompt, context=None, role="user"): return ""
            def generate_with_thinking(self, prompt, context=None, role="user"): pass
            
        provider = MockProvider()
        proponent = ProponentAgent(provider, direct_mode=False)
        assert "Do NOT use <think> tags" not in proponent.system_prompt
