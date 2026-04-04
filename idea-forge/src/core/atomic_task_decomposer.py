"""
atomic_task_decomposer.py — Decomposição de passagens em micro-tarefas atômicas.

Fase 9.7 (Onda 3 — W3-04): Decompor passagens que geram tabelas longas
em chamadas individuais (uma chamada por linha de tabela ou parágrafo),
garantindo que modelos com janelas de saída de 512 tokens não trunquem.

CONTRATO:
- Uma chamada por linha de tabela (máx 500 tokens de output)
- Uma chamada por bullet/parágrafo
- Montagem final por código Python (não por LLM)
- Falhas individuais são registradas e omitidas (degradação graciosa)
- Zero chamadas em paralelo (sequencial, compatível com Ollama local)

IMPORTAÇÕES PERMITIDAS: typing, re, dataclasses, src.models.model_provider,
                         src.core.prompt_profiles
"""

import re
import sys
from dataclasses import dataclass
from typing import List, Literal, Optional

from src.models.model_provider import ModelProvider
from src.core.prompt_profiles import PromptProfile
from src.core.stream_handler import ANSIStyle


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class AtomicCallResult:
    """
    Resultado de uma chamada atômica individual.

    Invariante: se success == True, então len(content) > 0
    Invariante: se success == False, content é "" ou placeholder
    """
    row_index: int       # Índice da linha/item (0-based)
    content: str         # String markdown da linha/bullet gerado
    success: bool        # True se conteúdo válido e não-vazio
    chars: int           # len(content)


@dataclass
class DecompositionPlan:
    """
    Plano de decomposição para uma seção.

    Gerado antes das chamadas atômicas para garantir que parâmetros
    são validados uma vez, não a cada chamada.
    """
    section_heading: str                             # "## Requisitos Funcionais"
    decomposition_type: Literal["TABLE", "BULLETS"]
    columns: List[str]           # Para TABLE: ["ID", "Requisito", ...]
    bullet_labels: List[str]     # Para BULLETS: ["RF-01", "RF-02", ...]
    target_count: int            # Número alvo de linhas/bullets [1..20]
    system_directive: str        # Prompt de sistema truncado ao perfil
    context_snippet: str         # Contexto truncado a max_context_chars
    max_tokens_per_call: int     # profile.max_output_tokens


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------

class AtomicTaskDecomposer:
    """
    Decomposição de passagens em micro-tarefas atômicas para modelos pequenos.

    Uso:
        decomposer = AtomicTaskDecomposer(provider=provider, profile=PROFILE_SMALL)
        rows = decomposer.decompose_table_pass(
            section_heading="## Requisitos Funcionais",
            columns=["ID", "Requisito", "Critério", "Prioridade", "Complexidade"],
            context="PROJETO: Sistema de debate de ideias...",
            target_row_count=8,
            system_directive="Gere UMA linha de tabela markdown. Apenas a linha, sem heading."
        )
        table_section = decomposer.assemble_table(
            heading="## Requisitos Funcionais",
            columns=["ID", "Requisito", "Critério", "Prioridade", "Complexidade"],
            rows=rows
        )
    """

    # Colunas-alvo para seções conhecidas (usadas para gerar DecompositionPlan)
    SECTION_COLUMNS_MAP = {
        "## Requisitos Funcionais": ["ID", "Requisito", "Critério de Aceite", "Prioridade", "Complexidade"],
        "## Requisitos Não-Funcionais": ["ID", "Categoria", "Requisito", "Métrica", "Target"],
        "## Riscos Consolidados": ["ID", "Risco", "Fonte", "Probabilidade", "Impacto", "Mitigação"],
        "## Análise de Segurança": ["ID", "Ameaça STRIDE", "Componente", "Severidade", "Mitigação"],
        "## ADRs": ["Campo", "Valor"],
        "## Plano de Implementação": ["Fase", "Duração", "Entregas", "Critério", "Dependência"],
        "## Métricas de Sucesso": ["Métrica", "Target", "Como Medir"],
        "## Público-Alvo": ["Segmento", "Perfil", "Prioridade"],
        "## Matriz de Rastreabilidade": ["RF-ID", "Componente", "Arquivo", "Teste que Valida", "Critério"],
        "## Limitações Conhecidas": ["ID", "Limitação", "Severidade", "Impacto", "Workaround", "Resolução"],
        "## Arquitetura e Tech Stack": ["Camada", "Tecnologia", "Versão", "Justificativa", "Alternativa Rejeitada"],
    }

    # Seções que usam bullets em vez de tabelas
    BULLET_SECTIONS = {
        "## Escopo MVP",
        "## Constraints Técnicos",
        "## Decisões do Debate",
        "## Princípios Arquiteturais",
    }

    def __init__(self, provider: ModelProvider, profile: PromptProfile):
        """
        Inicializa o decompositor.

        Args:
            provider: Provider LLM para chamadas individuais
            profile: Perfil de prompt ativo (deve ter use_atomic_decomposition==True)
        """
        if not profile.use_atomic_decomposition:
            raise ValueError(
                f"AtomicTaskDecomposer instanciado com perfil '{profile.model_range}' "
                f"que tem use_atomic_decomposition=False. "
                f"Apenas PROFILE_SMALL deve usar decomposição atômica."
            )
        self.provider = provider
        self.profile = profile

    def decompose_table_pass(
        self,
        section_heading: str,
        columns: List[str],
        context: str,
        target_row_count: int,
        system_directive: str
    ) -> List[str]:
        """
        Gera linhas de tabela Markdown uma a uma, via chamadas atômicas.

        Cada chamada gera EXATAMENTE uma linha no formato:
        | col1 | col2 | col3 | ... |

        Args:
            section_heading: Header da seção (deve começar com "## ")
            columns: Lista de nomes de colunas da tabela
            context: Contexto do projeto (truncado a profile.max_context_chars)
            target_row_count: Número de linhas a gerar [1..20]
            system_directive: Instrução de sistema para o modelo

        Returns:
            Lista de strings, cada uma é uma linha markdown válida
            (começa e termina com "|")

        Raises:
            ValueError: Se section_heading não começa com "## "
            ValueError: Se len(columns) < 2
        """
        # Validação de entrada
        if not section_heading.startswith("## "):
            raise ValueError(
                f"section_heading deve começar com '## '. Recebido: '{section_heading}'"
            )
        if len(columns) < 2:
            raise ValueError(
                f"columns deve ter pelo menos 2 elementos. Recebido: {columns}"
            )

        # Clamp target_row_count a [1, 20]
        target_row_count = max(1, min(20, target_row_count))

        # Truncar contexto
        context_truncated = context[:self.profile.max_context_chars]

        results: List[AtomicCallResult] = []
        section_name = section_heading.replace("## ", "")
        columns_str = " | ".join(columns)
        header_line = "| " + " | ".join(columns) + " |"

        self._emit(
            f"[ATOMIC] {section_heading} → decompondo {target_row_count} linhas de tabela"
        )

        for i in range(target_row_count):
            row_num = i + 1

            # Construir prompt atômico
            prompt = self._build_table_row_prompt(
                section_name=section_name,
                columns=columns,
                columns_str=columns_str,
                header_line=header_line,
                row_number=row_num,
                total_rows=target_row_count,
                context=context_truncated,
                system_directive=system_directive,
            )

            # Chamar provider com janela de saída limitada
            try:
                raw = self.provider.generate(
                    prompt=prompt,
                    role="product_manager",
                    max_tokens=self.profile.max_output_tokens,
                )
                row_content = self._extract_table_row(raw, len(columns))
                success = bool(row_content) and len(row_content) > 10
            except Exception:
                row_content = ""
                success = False

            result = AtomicCallResult(
                row_index=i,
                content=row_content,
                success=success,
                chars=len(row_content),
            )
            results.append(result)

            status = "OK" if success else "FALHOU"
            self._emit(
                f"[ATOMIC] Linha {row_num}/{target_row_count} → {result.chars} chars [{status}]"
            )

        # Filtrar apenas linhas bem-sucedidas
        successful_rows = [r.content for r in results if r.success]
        total_ok = len(successful_rows)
        self._emit(
            f"[ATOMIC] Montagem final → {total_ok}/{target_row_count} linhas bem-sucedidas"
        )

        return successful_rows

    def assemble_table(
        self,
        heading: str,
        columns: List[str],
        rows: List[str]
    ) -> str:
        """
        Monta uma seção completa com heading + header de tabela + linhas.

        Args:
            heading: Header da seção (ex: "## Requisitos Funcionais")
            columns: Lista de nomes de colunas
            rows: Lista de linhas markdown geradas por decompose_table_pass()

        Returns:
            String Markdown completa da seção.
            Se rows for vazio, retorna seção com placeholder.
        """
        if not rows:
            return (
                f"{heading}\n\n"
                f"[Dados não disponíveis — decomposição atômica não gerou linhas válidas]\n"
            )

        header_line = "| " + " | ".join(columns) + " |"
        separator_line = "|" + "|".join(["---"] * len(columns)) + "|"

        parts = [
            heading,
            "",
            header_line,
            separator_line,
        ]
        parts.extend(rows)

        return "\n".join(parts) + "\n"

    def decompose_paragraph_pass(
        self,
        section_heading: str,
        bullet_labels: List[str],
        context: str,
        system_directive: str
    ) -> List[str]:
        """
        Gera bullets/parágrafos um a um via chamadas atômicas.

        Cada chamada gera EXATAMENTE um bullet no formato:
        - Label: Conteúdo expandido em 1-3 frases

        Args:
            section_heading: Header da seção
            bullet_labels: Lista de rótulos para cada bullet
            context: Contexto do projeto (truncado)
            system_directive: Instrução de sistema

        Returns:
            Lista de strings, cada uma é um bullet markdown válido
        """
        if not section_heading.startswith("## "):
            raise ValueError(
                f"section_heading deve começar com '## '. Recebido: '{section_heading}'"
            )

        context_truncated = context[:self.profile.max_context_chars]
        results: List[AtomicCallResult] = []
        section_name = section_heading.replace("## ", "")
        total = len(bullet_labels)

        self._emit(
            f"[ATOMIC] {section_heading} → decompondo {total} bullets"
        )

        for i, label in enumerate(bullet_labels):
            prompt = self._build_bullet_prompt(
                section_name=section_name,
                label=label,
                item_number=i + 1,
                total_items=total,
                context=context_truncated,
                system_directive=system_directive,
            )

            try:
                raw = self.provider.generate(
                    prompt=prompt,
                    role="product_manager",
                    max_tokens=self.profile.max_output_tokens,
                )
                bullet = self._extract_bullet(raw, label)
                success = bool(bullet) and len(bullet) > 10
            except Exception:
                bullet = ""
                success = False

            result = AtomicCallResult(
                row_index=i,
                content=bullet,
                success=success,
                chars=len(bullet),
            )
            results.append(result)

        successful = [r.content for r in results if r.success]
        self._emit(
            f"[ATOMIC] Bullets → {len(successful)}/{total} gerados com sucesso"
        )
        return successful

    def assemble_bullets(
        self,
        heading: str,
        bullets: List[str]
    ) -> str:
        """
        Monta seção de bullets.

        Args:
            heading: Header da seção
            bullets: Lista de bullets gerados

        Returns:
            String Markdown completa
        """
        if not bullets:
            return f"{heading}\n\n[Dados não disponíveis]\n"

        parts = [heading, ""]
        parts.extend(bullets)
        return "\n".join(parts) + "\n"

    @staticmethod
    def get_columns_for_section(section_heading: str) -> Optional[List[str]]:
        """
        Retorna as colunas esperadas para uma seção conhecida.

        Args:
            section_heading: Heading da seção

        Returns:
            Lista de colunas ou None se seção não está no mapa
        """
        # Busca exata primeiro
        if section_heading in AtomicTaskDecomposer.SECTION_COLUMNS_MAP:
            return AtomicTaskDecomposer.SECTION_COLUMNS_MAP[section_heading]

        # Busca parcial (caso o heading tenha variação)
        for key, cols in AtomicTaskDecomposer.SECTION_COLUMNS_MAP.items():
            key_name = key.replace("## ", "").lower()
            heading_name = section_heading.replace("## ", "").lower()
            if key_name in heading_name or heading_name in key_name:
                return cols

        return None

    @staticmethod
    def is_bullet_section(section_heading: str) -> bool:
        """Retorna True se a seção usa bullets em vez de tabela."""
        return section_heading in AtomicTaskDecomposer.BULLET_SECTIONS

    # -----------------------------------------------------------------------
    # Métodos privados de construção de prompt
    # -----------------------------------------------------------------------

    def _build_table_row_prompt(
        self,
        section_name: str,
        columns: List[str],
        columns_str: str,
        header_line: str,
        row_number: int,
        total_rows: int,
        context: str,
        system_directive: str,
    ) -> str:
        """Constrói prompt atômico para geração de UMA linha de tabela."""
        prompt = (
            f"System: {system_directive}\n\n"
            f"TAREFA: Gere EXATAMENTE 1 linha da tabela Markdown para a seção "
            f"'{section_name}'.\n"
            f"Esta é a linha {row_number} de {total_rows}.\n\n"
            f"FORMATO OBRIGATÓRIO (apenas a linha, sem heading, sem código):\n"
            f"{header_line}\n"
            f"| valor1 | valor2 | ... | valorN |\n\n"
            f"COLUNAS: {columns_str}\n\n"
            f"CONTEXTO DO PROJETO:\n{context}\n\n"
            f"REGRAS:\n"
            f"- Gere APENAS a linha de dados (começando com |)\n"
            f"- NÃO inclua o header da tabela\n"
            f"- NÃO inclua ```markdown ou qualquer bloco de código\n"
            f"- Use dados específicos do projeto, não genéricos\n"
            f"- Responda em Português\n\n"
            f"LINHA {row_number}:"
        )
        return prompt

    def _build_bullet_prompt(
        self,
        section_name: str,
        label: str,
        item_number: int,
        total_items: int,
        context: str,
        system_directive: str,
    ) -> str:
        """Constrói prompt atômico para geração de UM bullet."""
        prompt = (
            f"System: {system_directive}\n\n"
            f"TAREFA: Gere EXATAMENTE 1 bullet para a seção '{section_name}'.\n"
            f"Item {item_number} de {total_items}: '{label}'\n\n"
            f"FORMATO OBRIGATÓRIO:\n"
            f"- {label}: [descrição concreta em 1-2 frases]\n\n"
            f"CONTEXTO DO PROJETO:\n{context}\n\n"
            f"REGRAS:\n"
            f"- Gere APENAS o bullet (começando com -)\n"
            f"- Responda em Português\n\n"
            f"BULLET:"
        )
        return prompt

    def _extract_table_row(self, raw: str, expected_columns: int) -> str:
        """
        Extrai a linha de tabela Markdown de uma resposta bruta.

        Critérios de validade:
        - Começa com |
        - Termina com |
        - Contém pelo menos (expected_columns - 1) separadores |
        """
        if not raw:
            return ""

        # Remover blocos de pensamento
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)

        # Procurar linha que começa com |
        for line in raw.strip().split('\n'):
            line = line.strip()
            if (line.startswith('|') and
                    line.endswith('|') and
                    '---|' not in line and  # Não é separator
                    line.count('|') >= expected_columns):
                return line

        # Fallback: se encontrou algo com |, pegar primeira ocorrência
        for line in raw.strip().split('\n'):
            line = line.strip()
            if line.startswith('|') and '---|' not in line:
                return line

        return ""

    def _extract_bullet(self, raw: str, label: str) -> str:
        """
        Extrai o bullet de uma resposta bruta.

        Critérios de validade:
        - Começa com - ou *
        - Contém o label ou conteúdo relevante
        """
        if not raw:
            return ""

        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)

        for line in raw.strip().split('\n'):
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                return line

        # Fallback: formatar como bullet mesmo sem marcador
        clean = raw.strip().split('\n')[0].strip()
        if clean and len(clean) > 5:
            return f"- {label}: {clean}"

        return ""

    def _emit(self, msg: str) -> None:
        """Emite mensagem de log no terminal (fail-safe)."""
        try:
            sys.stdout.write(f"{ANSIStyle.CYAN}{msg}{ANSIStyle.RESET}\n")
            sys.stdout.flush()
        except Exception:
            pass
