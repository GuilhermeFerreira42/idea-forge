"""
stream_handler.py — Módulo de interceptação e buffering de tokens de streaming.

Responsabilidades:
1. Parsear chunks JSON do Ollama stream
2. Separar tokens de pensamento (thinking) de tokens de conteúdo (response)
3. Detectar blocos <think>...</think> inline para modelos sem campo 'thinking' separado
4. Emitir eventos de estado para a CLI
5. Renderizar output formatado com diferenciação visual ANSI

NÃO contém lógica de negócio. NÃO conhece agentes. Apenas processa stream.
"""

import sys
import re
from enum import Enum
from typing import NamedTuple, Optional, Callable
from dataclasses import dataclass, field


class TokenType(Enum):
    """Classificação de cada token recebido do stream."""
    THINKING = "thinking"
    CONTENT = "content"
    STATE = "state"


class StreamResult(NamedTuple):
    """Resultado estruturado do processamento de stream completo."""
    thinking: str       # Buffer completo de pensamento (para log/debug)
    content: str        # Resposta final limpa (para histórico e relatório)
    raw: str            # Stream bruto completo (para diagnóstico)


class StateEvent:
    """Evento de telemetria emitido durante o processamento."""
    def __init__(self, event_type: str, message: str, metadata: dict = None):
        self.event_type = event_type
        self.message = message
        self.metadata = metadata or {}

    def __repr__(self):
        return f"[STATE: {self.event_type}] {self.message}"


# ─── ANSI Color Codes ───────────────────────────────────────
class ANSIStyle:
    """Códigos ANSI para formatação de terminal."""
    RESET = "\033[0m"
    DIM = "\033[2m"            # Texto dimmed/cinza para pensamento
    DIM_ITALIC = "\033[2;3m"   # Dimmed + itálico
    CYAN = "\033[36m"          # Para labels de estado
    YELLOW = "\033[33m"        # Para avisos
    GREEN = "\033[32m"         # Para confirmações
    BLUE = "\033[34m"          # Para informações de agente
    BOLD = "\033[1m"           # Para headers
    GRAY = "\033[90m"          # Cinza explícito


class SilentProgressIndicator:
    """
    FASE 2: Indicador visual de progresso para quando o modelo está
    gerando tokens de pensamento em background (show_thinking=False).

    Exibe um spinner minimalista para que o usuário saiba que
    o sistema está processando, não travado.

    Ciclo visual: ⣾ ⣽ ⣻ ⢿ ⡿ ⣟ ⣯ ⣷
    """
    SPINNER_FRAMES = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
    # Intervalo mínimo entre atualizações do spinner (em tokens, não tempo)
    # para evitar overhead de sys.stdout.write a cada token
    TOKEN_UPDATE_INTERVAL = 3

    def __init__(self):
        self._frame_index = 0
        self._token_count = 0
        self._is_active = False
        self._header_shown = False

    def tick(self):
        """
        Chamado cada vez que um token de thinking é recebido em modo silencioso.
        Atualiza o spinner a cada TOKEN_UPDATE_INTERVAL tokens.
        """
        self._token_count += 1

        if not self._header_shown:
            sys.stdout.write(
                f"{ANSIStyle.GRAY}💭 IA processando internamente "
            )
            sys.stdout.flush()
            self._header_shown = True
            self._is_active = True

        if self._token_count % self.TOKEN_UPDATE_INTERVAL == 0:
            # Mover cursor para trás sobre o último frame e escrever o novo
            frame = self.SPINNER_FRAMES[
                self._frame_index % len(self.SPINNER_FRAMES)
            ]
            sys.stdout.write(f"\b{frame}")
            sys.stdout.flush()
            self._frame_index += 1

    def finish(self):
        """Finaliza o indicador quando o conteúdo começa a chegar."""
        if self._is_active:
            sys.stdout.write(
                f"\b✓ ({self._token_count} tokens processados)"
                f"{ANSIStyle.RESET}\n"
            )
            sys.stdout.flush()
            self._is_active = False


@dataclass
class InlineThinkParser:
    """
    Parser de estado para detectar blocos <think>...</think> inline.
    
    Modelos sem campo 'thinking' separado emitem pensamento dentro do
    campo 'response' usando tags XML. Este parser rastreia se estamos
    dentro ou fora de um bloco <think>.
    
    Máquina de estados:
        OUTSIDE -> encontra '<think>' -> INSIDE
        INSIDE  -> encontra '</think>' -> OUTSIDE
    """
    inside_think: bool = False
    think_buffer: str = ""
    content_buffer: str = ""
    # Buffer parcial para detectar tags fragmentadas entre chunks
    _partial_tag_buffer: str = ""

    def process_chunk(self, chunk: str) -> tuple:
        """
        Processa um chunk de texto e separa pensamento de conteúdo.
        
        Returns:
            (think_text, content_text) — texto a ser exibido em cada canal
        """
        # Concatenar com buffer parcial de tag anterior
        text = self._partial_tag_buffer + chunk
        self._partial_tag_buffer = ""

        think_output = ""
        content_output = ""

        while text:
            if self.inside_think:
                # Procurar fim do bloco de pensamento
                end_idx = text.find("</think>")
                if end_idx != -1:
                    # Encontrou fechamento
                    think_part = text[:end_idx]
                    think_output += think_part
                    self.think_buffer += think_part
                    text = text[end_idx + len("</think>"):]
                    self.inside_think = False
                else:
                    # Verificar se temos uma tag parcial no final
                    # Ex: chunk termina com "</thi" — pode ser início de </think>
                    partial_match = self._check_partial_close_tag(text)
                    if partial_match is not None:
                        # Guardar o sufixo parcial para o próximo chunk
                        safe_text = text[:partial_match]
                        self._partial_tag_buffer = text[partial_match:]
                        think_output += safe_text
                        self.think_buffer += safe_text
                        text = ""
                    else:
                        think_output += text
                        self.think_buffer += text
                        text = ""
            else:
                # Procurar início de bloco de pensamento
                start_idx = text.find("<think>")
                if start_idx != -1:
                    # Conteúdo antes da tag
                    content_part = text[:start_idx]
                    content_output += content_part
                    self.content_buffer += content_part
                    text = text[start_idx + len("<think>"):]
                    self.inside_think = True
                else:
                    # Verificar tag parcial de abertura no final
                    partial_match = self._check_partial_open_tag(text)
                    if partial_match is not None:
                        safe_text = text[:partial_match]
                        self._partial_tag_buffer = text[partial_match:]
                        content_output += safe_text
                        self.content_buffer += safe_text
                        text = ""
                    else:
                        content_output += text
                        self.content_buffer += text
                        text = ""

        return think_output, content_output

    def _check_partial_open_tag(self, text: str) -> Optional[int]:
        """Verifica se o final do texto pode ser início de '<think>'."""
        tag = "<think>"
        for i in range(1, len(tag)):
            if text.endswith(tag[:i]):
                return len(text) - i
        return None

    def _check_partial_close_tag(self, text: str) -> Optional[int]:
        """Verifica se o final do texto pode ser início de '</think>'."""
        tag = "</think>"
        for i in range(1, len(tag)):
            if text.endswith(tag[:i]):
                return len(text) - i
        return None


class StreamHandler:
    """
    Gerenciador principal de stream do LLM.
    
    Processa chunks do Ollama API e:
    1. Separa pensamento de conteúdo (via campo 'thinking' OU tags inline)
    2. Renderiza em tempo real com formatação visual diferenciada
    3. Emite eventos de estado
    
    Uso:
        handler = StreamHandler(show_thinking=True)
        result = handler.process_ollama_stream(response_iterator)
        # result.content contém apenas a resposta limpa
        # result.thinking contém o raciocínio capturado
    """

    def __init__(self, show_thinking: bool = True, 
                 state_callback: Callable[[StateEvent], None] = None):
        """
        Args:
            show_thinking: Se True, exibe pensamento em estilo dimmed. 
                          Se False, exibe indicador de progresso silencioso.
            state_callback: Função chamada quando um evento de estado é emitido.
        """
        self.show_thinking = show_thinking
        self.state_callback = state_callback
        self._inline_parser = InlineThinkParser()
        self._thinking_header_shown = False
        self._content_header_shown = False
        self._has_thinking_content = False
        # FASE 2: Indicador de progresso para modo silencioso
        self._silent_progress = SilentProgressIndicator()

    def emit_state(self, event_type: str, message: str, metadata: dict = None):
        """Emite um evento de estado para a CLI."""
        event = StateEvent(event_type, message, metadata or {})
        if self.state_callback:
            self.state_callback(event)
        else:
            # Fallback: imprimir diretamente
            sys.stdout.write(
                f"\n{ANSIStyle.CYAN}⚡ {event.message}{ANSIStyle.RESET}\n"
            )
            sys.stdout.flush()

    def process_ollama_stream(self, line_iterator) -> StreamResult:
        """
        Processa o stream completo do Ollama e retorna resultado estruturado.
        
        Args:
            line_iterator: Iterator de linhas bytes da resposta HTTP streaming.
            
        Returns:
            StreamResult com thinking, content e raw separados.
        """
        import json

        full_thinking = ""
        full_content = ""
        full_raw = ""
        has_native_thinking = False  # Flag: modelo usa campo 'thinking' nativo

        for line in line_iterator:
            if not line:
                continue
            try:
                data = json.loads(line.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            # ── Estratégia 1: Campo 'thinking' nativo do Ollama ──
            thinking_chunk = data.get("thinking", "")
            response_chunk = data.get("response", "")

            if thinking_chunk:
                has_native_thinking = True
                full_thinking += thinking_chunk
                full_raw += thinking_chunk
                self._render_thinking_chunk(thinking_chunk)

            if response_chunk:
                if has_native_thinking:
                    # Modelo tem campo nativo — response é conteúdo limpo
                    if not self._content_header_shown and self._has_thinking_content:
                        self._transition_to_content()
                    full_content += response_chunk
                    full_raw += response_chunk
                    self._render_content_chunk(response_chunk)
                else:
                    # ── Estratégia 2: Parse inline de <think> tags ──
                    full_raw += response_chunk
                    think_part, content_part = self._inline_parser.process_chunk(
                        response_chunk
                    )
                    if think_part:
                        full_thinking += think_part
                        self._render_thinking_chunk(think_part)
                    if content_part:
                        if not self._content_header_shown and self._has_thinking_content:
                            self._transition_to_content()
                        full_content += content_part
                        self._render_content_chunk(content_part)

            # Verificar se o stream terminou
            if data.get("done", False):
                break

        # Finalizar renderização
        self._finalize_render()

        # Se não houve campo nativo e nem tags inline, o content é o raw
        if not has_native_thinking and not self._inline_parser.think_buffer:
            full_content = full_raw
            full_thinking = ""

        return StreamResult(
            thinking=full_thinking.strip(),
            content=full_content.strip(),
            raw=full_raw.strip()
        )

    def _render_thinking_chunk(self, chunk: str):
        """
        Renderiza um chunk de pensamento.

        FASE 2: Comportamento bifurcado:
        - show_thinking=True  → Exibe em estilo dimmed (comportamento Fase 1)
        - show_thinking=False → Aciona indicador de progresso silencioso
        """
        self._has_thinking_content = True

        if self.show_thinking:
            # Modo visível: renderizar em cinza/dimmed
            if not self._thinking_header_shown:
                sys.stdout.write(
                    f"\n{ANSIStyle.GRAY}{'─' * 40}{ANSIStyle.RESET}\n"
                    f"{ANSIStyle.DIM_ITALIC}💭 Raciocínio interno:{ANSIStyle.RESET}\n"
                    f"{ANSIStyle.DIM}"
                )
                sys.stdout.flush()
                self._thinking_header_shown = True

            sys.stdout.write(f"{ANSIStyle.DIM}{chunk}{ANSIStyle.RESET}")
            sys.stdout.flush()
        else:
            # FASE 2: Modo silencioso — exibir indicador de progresso
            self._silent_progress.tick()

    def _transition_to_content(self):
        """Renderiza a transição visual de pensamento para conteúdo."""
        # FASE 2: Finalizar o indicador silencioso se estava ativo
        self._silent_progress.finish()

        if self.show_thinking:
            sys.stdout.write(
                f"{ANSIStyle.RESET}\n"
                f"{ANSIStyle.GRAY}{'─' * 40}{ANSIStyle.RESET}\n"
                f"{ANSIStyle.GREEN}✅ Resposta:{ANSIStyle.RESET}\n"
            )
        else:
            # FASE 2: Transição limpa sem header de thinking anterior
            sys.stdout.write(
                f"{ANSIStyle.GREEN}✅ Resposta:{ANSIStyle.RESET}\n"
            )
        sys.stdout.flush()
        self._content_header_shown = True

    def _render_content_chunk(self, chunk: str):
        """Renderiza um chunk de conteúdo final (estilo normal)."""
        sys.stdout.write(chunk)
        sys.stdout.flush()

    def _finalize_render(self):
        """Limpa estado visual ao fim do stream."""
        # FASE 2: Garantir que o indicador silencioso seja finalizado
        self._silent_progress.finish()
        sys.stdout.write(f"{ANSIStyle.RESET}\n")
        sys.stdout.flush()

    def reset(self):
        """Reset do handler para reutilização."""
        self._inline_parser = InlineThinkParser()
        self._thinking_header_shown = False
        self._content_header_shown = False
        self._has_thinking_content = False
        self._silent_progress = SilentProgressIndicator()
