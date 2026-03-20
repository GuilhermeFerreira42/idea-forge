# FASE 5.1 — HARD GATE VALIDATOR + RETRY POR PASS

---

## 1. DIAGNÓSTICO CIRÚRGICO

```
PROBLEMA: O pipeline aceita artefatos vazios/incompletos silenciosamente.

3 PONTOS DE FALHA IDENTIFICADOS:

PONTO 1: SectionalGenerator não faz retry quando pass falha
  → Pass retorna vazio ou sem headings → concatena mesmo assim

PONTO 2: Planner aceita qualquer string como artefato válido
  → Artefato de 0 tokens é persistido e pipeline continua

PONTO 3: Agentes de Review/Security não usam geração seccional
  → Chamada única com prompt pesado → modelo retorna vazio
```

---

## 2. ARQUIVOS MODIFICADOS/CRIADOS

| Arquivo | Ação | Mudança |
|---|---|---|
| `src/core/sectional_generator.py` | **MODIFICAR** | Retry por pass com prompt corretivo + validação hard |
| `src/core/output_validator.py` | **MODIFICAR** | Método `validate_pass()` + `is_placeholder()` + thresholds configuráveis |
| `src/core/planner.py` | **MODIFICAR** | Hard gate antes de persistir artefato |
| `src/agents/critic_agent.py` | **MODIFICAR** | `review_artifact()` usa SectionalGenerator |
| `src/agents/security_reviewer_agent.py` | **MODIFICAR** | `review_security()` usa SectionalGenerator com 2 passes lite |
| `src/core/prompt_templates.py` | **MODIFICAR** | Adicionar templates lite para review/security |

### Arquivos NÃO alterados
- `src/models/model_provider.py`
- `src/models/ollama_provider.py`
- `src/core/stream_handler.py`
- `src/core/blackboard.py`
- `src/core/artifact_store.py`
- `src/core/golden_examples.py`
- `src/cli/main.py`
- `src/debate/debate_engine.py`

---

## 3. CÓDIGO DE IMPLEMENTAÇÃO

### 3.1 — `src/core/output_validator.py` (MODIFICAR)

```python
"""
output_validator.py — Validador de conformidade de artefatos gerados.

FASE 5.1:
- Adicionado validate_pass() para validação individual de passes
- Adicionado is_placeholder() para detectar outputs "A DEFINIR" em massa
- Adicionado min_chars por tipo de artefato
- Thresholds configuráveis por artifact_type
"""
import re
from typing import Dict, List


class OutputValidator:
    """Valida conformidade de artefatos contra templates esperados."""

    REQUIRED_SECTIONS = {
        "prd": [
            "## Objetivo",
            "## Problema",
            "## Requisitos Funcionais",
            "## Requisitos Não-Funcionais",
            "## Escopo MVP",
            "## Métricas de Sucesso",
            "## Dependências e Riscos",
        ],
        "system_design": [
            "## Arquitetura Geral",
            "## Tech Stack",
            "## Módulos",
            "## Modelo de Dados",
            "## Fluxo de Dados",
            "## ADRs",
            "## Riscos Técnicos",
        ],
        "review": [
            "## Score de Qualidade",
            "## Issues Identificadas",
            "## Verificação de Requisitos",
            "## Sumário",
            "## Recomendação",
        ],
        "security_review": [
            "## Superfície de Ataque",
            "## Ameaças Identificadas",
            "## Requisitos de Segurança Derivados",
            "## Dados Sensíveis",
        ],
        "plan": [
            "## Arquitetura Sugerida",
            "## Módulos Core",
            "## Fases de Implementação",
            "## Riscos e Mitigações",
        ],
    }

    # FASE 5.1: Thresholds mínimos por tipo de artefato
    MIN_CHARS = {
        "prd": 400,
        "system_design": 400,
        "review": 200,
        "security_review": 200,
        "plan": 300,
    }

    # FASE 5.1: Completude mínima para aprovar (0.0 - 1.0)
    MIN_COMPLETENESS = {
        "prd": 0.70,
        "system_design": 0.70,
        "review": 0.60,
        "security_review": 0.50,
        "plan": 0.70,
    }

    def validate(self, content: str, artifact_type: str) -> Dict:
        """Valida artefato completo contra seções obrigatórias."""
        required = self.REQUIRED_SECTIONS.get(artifact_type, [])
        present = []
        missing = []

        if not required:
            return {"valid": True, "note": "No validation rules for this type"}

        if not content or not content.strip():
            return {
                "valid": False,
                "missing_sections": required,
                "present_sections": [],
                "completeness_score": 0.0,
                "density_score": 0.0,
                "has_tables": False,
                "table_count": 0,
                "fail_reason": "EMPTY_CONTENT",
            }

        for section in required:
            pattern = re.compile(re.escape(section), re.IGNORECASE)
            if pattern.search(content):
                present.append(section)
            else:
                missing.append(section)

        completeness = len(present) / len(required)
        density = self._calculate_density(content)
        table_count = content.count("|---|")
        min_chars = self.MIN_CHARS.get(artifact_type, 200)
        min_completeness = self.MIN_COMPLETENESS.get(artifact_type, 0.60)

        # FASE 5.1: Múltiplas condições de falha
        fail_reasons = []
        if len(content.strip()) < min_chars:
            fail_reasons.append(f"TOO_SHORT ({len(content.strip())} < {min_chars})")
        if completeness < min_completeness:
            fail_reasons.append(f"INCOMPLETE ({completeness:.0%} < {min_completeness:.0%})")
        if self.is_placeholder_heavy(content):
            fail_reasons.append("PLACEHOLDER_HEAVY (>50% A DEFINIR)")

        is_valid = len(fail_reasons) == 0

        return {
            "valid": is_valid,
            "missing_sections": missing,
            "present_sections": present,
            "completeness_score": round(completeness, 2),
            "density_score": round(density, 2),
            "has_tables": table_count > 0,
            "table_count": table_count,
            "fail_reasons": fail_reasons,
        }

    def validate_pass(self, content: str, expected_sections: List[str],
                      require_table: bool = True,
                      min_chars: int = 80) -> Dict:
        """
        FASE 5.1: Valida um pass individual da geração seccional.

        Args:
            content: Output do pass
            expected_sections: Lista de headings ## esperados
            require_table: Se True, exige pelo menos 1 tabela (|---|)
            min_chars: Tamanho mínimo do output

        Returns:
            {
                "valid": bool,
                "missing_sections": list,
                "has_table": bool,
                "char_count": int,
                "is_placeholder": bool,
                "fail_reasons": list
            }
        """
        fail_reasons = []

        # Check 1: conteúdo vazio ou muito curto
        if not content or len(content.strip()) < min_chars:
            return {
                "valid": False,
                "missing_sections": expected_sections,
                "has_table": False,
                "char_count": len(content.strip()) if content else 0,
                "is_placeholder": False,
                "fail_reasons": [f"TOO_SHORT ({len(content.strip()) if content else 0} < {min_chars})"],
            }

        # Check 2: seções esperadas presentes
        missing = []
        for section in expected_sections:
            pattern = re.compile(re.escape(section), re.IGNORECASE)
            if not pattern.search(content):
                missing.append(section)

        if missing:
            fail_reasons.append(f"MISSING_SECTIONS: {missing}")

        # Check 3: tabela obrigatória
        has_table = "|---|" in content
        if require_table and not has_table:
            fail_reasons.append("NO_TABLE")

        # Check 4: placeholders excessivos
        is_placeholder = self.is_placeholder_heavy(content)
        if is_placeholder:
            fail_reasons.append("PLACEHOLDER_HEAVY")

        return {
            "valid": len(fail_reasons) == 0,
            "missing_sections": missing,
            "has_table": has_table,
            "char_count": len(content.strip()),
            "is_placeholder": is_placeholder,
            "fail_reasons": fail_reasons,
        }

    def is_placeholder_heavy(self, content: str) -> bool:
        """
        FASE 5.1: Detecta se o output é majoritariamente placeholders.

        Retorna True se mais de 50% das linhas de tabela contêm
        'A DEFINIR', '...', ou células vazias.
        """
        if not content:
            return True

        lines = content.split('\n')
        table_lines = [l for l in lines if l.strip().startswith('|')
                       and '---|' not in l]

        if len(table_lines) < 2:
            return False

        placeholder_count = 0
        for line in table_lines:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if not cells:
                continue
            placeholder_cells = sum(
                1 for c in cells
                if c in ('...', 'A DEFINIR', '', '-')
                or c.startswith('...')
            )
            if placeholder_cells > len(cells) / 2:
                placeholder_count += 1

        return placeholder_count > len(table_lines) / 2

    def _calculate_density(self, content: str) -> float:
        """Calcula razão linhas técnicas / total linhas."""
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        if not lines:
            return 0.0
        technical = 0
        for line in lines:
            if (line.startswith('|') or
                line.startswith('-') or
                line.startswith('##') or
                line.startswith('```') or
                line.startswith('**') or
                (len(line) > 1 and line[0].isdigit() and line[1] in '.)')):
                technical += 1
        return technical / len(lines)
```

---

### 3.2 — `src/core/sectional_generator.py` (MODIFICAR)

Substituir o método `generate_sectional` e adicionar retry com prompt corretivo:

```python
"""
sectional_generator.py — Gerador de artefatos por seções.

FASE 5.1:
- Retry por pass com prompt corretivo específico
- Validação hard por pass via OutputValidator.validate_pass()
- Limite de 2 retries por pass
- Pass falhado após retries → marcado com [PASS_FAILED]
- Se >50% dos passes falharam → retorna None (trigger de fallback)
"""
import sys
from typing import List, Dict, Optional
from src.models.model_provider import ModelProvider
from src.core.stream_handler import ANSIStyle
from src.core.output_validator import OutputValidator


MAX_RETRIES_PER_PASS = 2


class SectionPass:
    """Definição de um passo de geração."""
    def __init__(self, pass_id: str, sections: List[str],
                 template: str, example: str,
                 instruction: str, max_output_tokens: int = 800,
                 require_table: bool = True,
                 min_chars: int = 80):
        self.pass_id = pass_id
        self.sections = sections
        self.template = template
        self.example = example
        self.instruction = instruction
        self.max_output_tokens = max_output_tokens
        self.require_table = require_table
        self.min_chars = min_chars


class SectionalGenerator:
    """Gera artefatos densos quebrando em múltiplos passes sequenciais."""

    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self.validator = OutputValidator()

    def generate_sectional(self, artifact_type: str,
                           user_input: str,
                           context: str = "",
                           passes: List[SectionPass] = None) -> Optional[str]:
        """
        Gera artefato denso em múltiplos passes com retry.

        Returns:
            Artefato completo concatenado, ou None se >50% passes falharam.
        """
        if passes is None:
            passes = self._get_default_passes(artifact_type)

        if not passes:
            return None

        accumulated_output = ""
        pass_results = []
        failed_passes = 0

        for i, section_pass in enumerate(passes):
            self._emit(f"[PASS {i+1}/{len(passes)}] "
                       f"Gerando: {', '.join(section_pass.sections)}")

            result = self._execute_pass_with_retry(
                section_pass=section_pass,
                user_input=user_input,
                context=context,
                previous_output=accumulated_output,
                pass_number=i + 1,
                total_passes=len(passes),
            )

            if result is None:
                # Pass falhou após todos os retries
                failed_passes += 1
                self._emit_warn(
                    f"Pass {i+1} FALHOU após {MAX_RETRIES_PER_PASS} retries. "
                    f"Seções afetadas: {section_pass.sections}"
                )
                # Inserir marcador de falha no output
                failed_marker = "\n".join(
                    f"{s}\n- [GERAÇÃO FALHOU — seção não produzida pelo modelo]"
                    for s in section_pass.sections
                )
                pass_results.append(failed_marker)
            else:
                pass_results.append(result)
                accumulated_output += result + "\n\n"

        # FASE 5.1: Se mais da metade dos passes falhou, retornar None
        # para que o agente use fallback de chamada única
        if failed_passes > len(passes) / 2:
            self._emit_warn(
                f"FALHA ESTRUTURAL: {failed_passes}/{len(passes)} passes falharam. "
                f"Acionando fallback."
            )
            return None

        final_output = "\n\n".join(pass_results)

        # Validar artefato final
        validation = self.validator.validate(final_output, artifact_type)
        if validation.get("valid"):
            self._emit_ok(
                f"Artefato aprovado — "
                f"density: {validation['density_score']:.2f}, "
                f"completude: {int(validation['completeness_score']*100)}%, "
                f"tabelas: {validation['table_count']}"
            )
        else:
            reasons = validation.get('fail_reasons', [])
            self._emit_warn(
                f"Artefato com problemas: {reasons}"
            )

        return final_output

    def _execute_pass_with_retry(self, section_pass: SectionPass,
                                 user_input: str, context: str,
                                 previous_output: str,
                                 pass_number: int,
                                 total_passes: int) -> Optional[str]:
        """
        FASE 5.1: Executa um pass com até MAX_RETRIES_PER_PASS retries.

        Retorna o conteúdo validado, ou None se todos os retries falharam.
        """
        last_fail_reasons = []

        for attempt in range(1, MAX_RETRIES_PER_PASS + 2):  # attempt 1 = original, 2-3 = retries
            # Construir prompt
            prompt = self._build_pass_prompt(
                section_pass=section_pass,
                user_input=user_input,
                context=context,
                previous_output=previous_output,
                pass_number=pass_number,
                total_passes=total_passes,
            )

            # Se é retry, adicionar instrução corretiva
            if attempt > 1 and last_fail_reasons:
                prompt += self._build_retry_instruction(
                    section_pass, last_fail_reasons, attempt
                )

            # Gerar
            result = self.provider.generate(prompt=prompt, role="user")
            result = self._clean_pass_output(result)

            # Validar
            validation = self.validator.validate_pass(
                content=result,
                expected_sections=section_pass.sections,
                require_table=section_pass.require_table,
                min_chars=section_pass.min_chars,
            )

            if validation["valid"]:
                if attempt > 1:
                    self._emit_ok(f"  Pass {pass_number} corrigido na tentativa {attempt}")
                return result

            # Falhou — preparar retry
            last_fail_reasons = validation.get("fail_reasons", ["UNKNOWN"])

            if attempt <= MAX_RETRIES_PER_PASS:
                self._emit_warn(
                    f"  Pass {pass_number} tentativa {attempt} falhou: "
                    f"{last_fail_reasons}. Retentando..."
                )

        # Todos os retries falharam
        return None

    def _build_retry_instruction(self, section_pass: SectionPass,
                                 fail_reasons: List[str],
                                 attempt: int) -> str:
        """
        FASE 5.1: Gera instrução corretiva baseada nos motivos de falha.
        """
        instruction = (
            f"\n\n⚠️ ATENÇÃO (tentativa {attempt}): "
            f"Sua resposta anterior falhou pelos seguintes motivos:\n"
        )

        for reason in fail_reasons:
            instruction += f"- {reason}\n"

        instruction += (
            "\nCORRIJA os problemas acima. Regras obrigatórias:\n"
            "1. Comece IMEDIATAMENTE com ## heading. NENHUM texto antes.\n"
        )

        # Instrução específica por tipo de falha
        if any("MISSING_SECTIONS" in r for r in fail_reasons):
            instruction += (
                "2. Inclua OBRIGATORIAMENTE estas seções:\n"
            )
            for section in section_pass.sections:
                instruction += f"   {section}\n"

        if any("NO_TABLE" in r for r in fail_reasons):
            instruction += (
                "3. Inclua PELO MENOS 1 tabela Markdown com | coluna | coluna |.\n"
            )

        if any("TOO_SHORT" in r for r in fail_reasons):
            instruction += (
                f"4. Sua resposta deve ter NO MÍNIMO {section_pass.min_chars} caracteres.\n"
            )

        if any("PLACEHOLDER" in r for r in fail_reasons):
            instruction += (
                "5. NÃO use 'A DEFINIR' ou '...' — preencha com dados reais baseados no projeto.\n"
            )

        return instruction

    def _build_pass_prompt(self, section_pass: SectionPass,
                           user_input: str, context: str,
                           previous_output: str,
                           pass_number: int, total_passes: int) -> str:
        """Constrói prompt otimizado para um pass individual."""
        system = (
            "Responda em Português. Formato: APENAS Markdown com tabelas e bullets.\n"
            "PROIBIDO: introduções, conclusões, meta-comentários, prosa.\n"
            "OBRIGATÓRIO: começar DIRETO com ## heading da primeira seção.\n"
        )
        if self.direct_mode:
            system += "Responda diretamente sem blocos <think>.\n"

        prompt = f"System: {system}\n\n"
        prompt += f"GERE EXATAMENTE ESTAS SEÇÕES:\n{section_pass.template}\n\n"

        if section_pass.example:
            prompt += f"REFERÊNCIA DE FORMATO:\n{section_pass.example}\n\n"

        prompt += f"PROJETO:\n{user_input[:600]}\n\n"

        if previous_output:
            summary = self._summarize_previous(previous_output, max_tokens=300)
            prompt += (
                f"SEÇÕES JÁ GERADAS (NÃO repita, apenas referencie IDs se necessário):\n"
                f"{summary}\n\n"
            )

        if context:
            prompt += f"CONTEXTO ADICIONAL:\n{context[:400]}\n\n"

        prompt += f"{section_pass.instruction}\n"

        return prompt

    def _summarize_previous(self, text: str, max_tokens: int = 300) -> str:
        """Extrai apenas headings e primeiras linhas."""
        lines = text.split('\n')
        summary_lines = []
        chars_budget = max_tokens * 4
        current_chars = 0
        capture_next = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('##'):
                summary_lines.append(stripped)
                current_chars += len(stripped)
                capture_next = True
            elif capture_next and stripped:
                summary_lines.append(stripped[:100])
                current_chars += min(len(stripped), 100)
                capture_next = False
            if current_chars >= chars_budget:
                break

        return '\n'.join(summary_lines)

    def _clean_pass_output(self, text: str) -> str:
        """Remove ruído do output."""
        import re as re_module

        if not text:
            return ""

        lines = text.split('\n')
        start_idx = 0

        noise_prefixes = [
            'certamente', 'com certeza', 'aqui está', 'entendido',
            'com base', 'analisando', 'como solicitado', 'segue',
            'okay', "let's", 'i will', 'based on', 'here is', 'sure',
            'entendi', 'de acordo', '[pass'
        ]

        for i, line in enumerate(lines[:5]):
            stripped = line.strip().lower()
            if not stripped:
                start_idx = i + 1
                continue
            if any(stripped.startswith(p) for p in noise_prefixes):
                start_idx = i + 1
            else:
                break

        result = '\n'.join(lines[start_idx:]).strip()

        if '<think>' in result:
            result = re_module.sub(r'<think>.*?</think>', '', result, flags=re_module.DOTALL).strip()

        return result

    # ─── Emitters ───────────────────────────────────────
    def _emit(self, msg: str):
        sys.stdout.write(f"{ANSIStyle.CYAN}  {msg}{ANSIStyle.RESET}\n")
        sys.stdout.flush()

    def _emit_ok(self, msg: str):
        sys.stdout.write(f"{ANSIStyle.GREEN}  ✅ {msg}{ANSIStyle.RESET}\n")
        sys.stdout.flush()

    def _emit_warn(self, msg: str):
        sys.stdout.write(f"{ANSIStyle.YELLOW}  ⚠ {msg}{ANSIStyle.RESET}\n")
        sys.stdout.flush()

    # ─── Default Passes ────────────────────────────────
    def _get_default_passes(self, artifact_type: str) -> List[SectionPass]:
        if artifact_type == "prd":
            return PRD_PASSES
        elif artifact_type == "system_design":
            return DESIGN_PASSES
        elif artifact_type == "plan":
            return PLAN_PASSES
        elif artifact_type == "review":
            return REVIEW_PASSES
        elif artifact_type == "security_review":
            return SECURITY_PASSES
        return []


# ═══════════════════════════════════════════════════════════
# PASSES POR TIPO DE ARTEFATO
# ═══════════════════════════════════════════════════════════

PRD_PASSES = [
    SectionPass(
        pass_id="prd_p1",
        sections=["## Objetivo", "## Problema"],
        template=(
            "## Objetivo\n"
            "- [1 frase, verbo no infinitivo, máximo 25 palavras]\n\n"
            "## Problema\n"
            "| ID | Problema | Impacto | Evidência |\n"
            "|---|---|---|---|\n"
            "| P-01 | ... | ... | ... |\n"
        ),
        example=(
            "## Objetivo\n"
            "- Permitir gerenciamento de tarefas pessoais com sincronização offline-first\n\n"
            "## Problema\n"
            "| ID | Problema | Impacto | Evidência |\n"
            "|---|---|---|---|\n"
            "| P-01 | Apps existentes requerem internet | Perda de dados offline | 40% dos usuários reportam |\n"
            "| P-02 | Complexidade excessiva | Abandono em 7 dias | Retenção <20% |\n"
        ),
        instruction="Gere APENAS Objetivo e Problema. Mínimo 2 problemas na tabela.",
        min_chars=150,
    ),
    SectionPass(
        pass_id="prd_p2",
        sections=["## Requisitos Funcionais", "## Requisitos Não-Funcionais"],
        template=(
            "## Requisitos Funcionais\n"
            "| ID | Requisito | Critério de Aceite | Prioridade (MoSCoW) | Complexidade |\n"
            "|---|---|---|---|---|\n"
            "| RF-01 | ... | ... | Must/Should/Could | Low/Med/High |\n\n"
            "## Requisitos Não-Funcionais\n"
            "| ID | Categoria | Requisito | Métrica | Target |\n"
            "|---|---|---|---|---|\n"
            "| RNF-01 | Performance | ... | ... | ... |\n"
        ),
        example=(
            "| RF-01 | CRUD de tarefas | POST/GET/PUT/DELETE retorna status correto | Must | Low |\n"
            "| RF-02 | Filtro por status | GET /tasks?status=done retorna subset | Should | Low |\n"
            "| RNF-01 | Performance | Latência API | p95 | <200ms |\n"
        ),
        instruction="Gere APENAS RF e RNF. Mínimo 5 RF e 3 RNF. IDs sequenciais.",
        min_chars=300,
        max_output_tokens=800,
    ),
    SectionPass(
        pass_id="prd_p3",
        sections=["## Escopo MVP", "## Métricas de Sucesso"],
        template=(
            "## Escopo MVP\n"
            "**Inclui:** [lista com bullets referenciando RF-XX]\n"
            "**NÃO inclui:** [lista com bullets]\n\n"
            "## Métricas de Sucesso (SMART)\n"
            "| Métrica | Specific | Measurable | Target | Prazo |\n"
            "|---|---|---|---|---|\n"
        ),
        example=(
            "**Inclui:**\n- RF-01, RF-02, RF-03 — core CRUD\n\n"
            "**NÃO inclui:**\n- Notificações push (v2)\n"
        ),
        instruction="Gere APENAS Escopo e Métricas. Referencie IDs RF-XX.",
        min_chars=150,
    ),
    SectionPass(
        pass_id="prd_p4",
        sections=["## Dependências e Riscos", "## Constraints Técnicos"],
        template=(
            "## Dependências e Riscos\n"
            "| ID | Tipo | Descrição | Probabilidade | Impacto | Mitigação |\n"
            "|---|---|---|---|---|---|\n"
            "| R-01 | Risco | ... | Alta/Média/Baixa | Alto/Médio/Baixo | ... |\n\n"
            "## Constraints Técnicos\n"
            "- Linguagem: [valor ou 'A DEFINIR']\n"
            "- Framework: [valor ou 'A DEFINIR']\n"
            "- Banco de dados: [valor ou 'A DEFINIR']\n"
            "- Infraestrutura: [valor ou 'A DEFINIR']\n"
        ),
        example=(
            "| R-01 | Risco | SQLite sem escrita concorrente | Média | Alto | WAL mode |\n"
            "| R-02 | Dependência | Ollama deve estar rodando | Alta | Crítico | Health check |\n"
        ),
        instruction="Gere APENAS Riscos e Constraints. Mínimo 3 riscos.",
        min_chars=150,
    ),
]

# ─── REVIEW: 2 passes lite ──────────────────────────────

REVIEW_PASSES = [
    SectionPass(
        pass_id="review_p1",
        sections=["## Score de Qualidade", "## Issues Identificadas"],
        template=(
            "## Score de Qualidade\n"
            "- **quality_score:** [0-100]\n"
            "- **verdict:** [APPROVED | NEEDS_CORRECTION | REJECTED]\n\n"
            "## Issues Identificadas\n"
            "| ID | Severidade | Categoria | Localização | Descrição | Sugestão |\n"
            "|---|---|---|---|---|---|\n"
            "| ISS-01 | HIGH/MED/LOW | SECURITY/CORRECTNESS/COMPLETENESS | ... | ... | ... |\n"
        ),
        example=(
            "- **quality_score:** 72\n"
            "- **verdict:** NEEDS_CORRECTION\n\n"
            "| ISS-01 | HIGH | SECURITY | Modelo de Dados | Senha sem hash | Usar bcrypt |\n"
        ),
        instruction=(
            "Analise o artefato e gere Score + Issues. "
            "Mínimo 2 issues. Cada issue com sugestão concreta."
        ),
        min_chars=200,
    ),
    SectionPass(
        pass_id="review_p2",
        sections=["## Verificação de Requisitos", "## Sumário", "## Recomendação"],
        template=(
            "## Verificação de Requisitos\n"
            "| Requisito ID | Status | Notas |\n"
            "|---|---|---|\n"
            "| RF-01 | ✅ Atendido / ❌ Não atendido | ... |\n\n"
            "## Sumário\n"
            "- [1-2 frases]\n\n"
            "## Recomendação\n"
            "- [Ação específica]\n"
        ),
        example="",
        instruction=(
            "Verifique cada RF/RNF do artefato. "
            "Gere Verificação + Sumário + Recomendação."
        ),
        min_chars=150,
        require_table=True,
    ),
]

# ─── SECURITY: 2 passes lite ────────────────────────────

SECURITY_PASSES = [
    SectionPass(
        pass_id="security_p1",
        sections=["## Superfície de Ataque", "## Ameaças Identificadas"],
        template=(
            "## Superfície de Ataque\n"
            "| Componente | Tipo de Exposição | Nível de Risco |\n"
            "|---|---|---|\n\n"
            "## Ameaças Identificadas (STRIDE)\n"
            "| ID | Categoria STRIDE | Componente | Ameaça | Severidade | Mitigação |\n"
            "|---|---|---|---|---|---|\n"
            "| T-01 | S/T/R/I/D/E | ... | ... | Alta/Média/Baixa | ... |\n"
        ),
        example=(
            "| API /auth | HTTP | Alto |\n\n"
            "| T-01 | S (Spoofing) | /auth/login | Brute force | Alta | Rate limit 5/min |\n"
            "| T-02 | I (Info Disclosure) | /users/{id} | IDOR | Alta | Ownership check |\n"
        ),
        instruction=(
            "Analise o System Design e identifique superfície de ataque + ameaças STRIDE. "
            "Mínimo 3 ameaças."
        ),
        min_chars=200,
    ),
    SectionPass(
        pass_id="security_p2",
        sections=["## Requisitos de Segurança Derivados", "## Dados Sensíveis"],
        template=(
            "## Requisitos de Segurança Derivados\n"
            "| ID | Requisito | Prioridade | Ameaça Mitigada |\n"
            "|---|---|---|---|\n"
            "| RS-01 | ... | Must/Should | T-XX |\n\n"
            "## Dados Sensíveis\n"
            "| Dado | Classificação | Criptografia | Retenção |\n"
            "|---|---|---|---|\n"
        ),
        example="",
        instruction=(
            "Gere requisitos de segurança derivados das ameaças + "
            "classificação de dados sensíveis."
        ),
        min_chars=150,
    ),
]

# ─── DESIGN: mantém mesmos passes de antes ────────────
DESIGN_PASSES = [
    SectionPass(
        pass_id="design_p1",
        sections=["## Arquitetura Geral", "## Tech Stack"],
        template=(
            "## Arquitetura Geral (C4 — Container Level)\n"
            "- Estilo: [ex: Monolito Modular]\n"
            "- Containers: [lista]\n"
            "- Comunicação: [protocolos]\n\n"
            "## Tech Stack\n"
            "| Camada | Tecnologia | Versão | Justificativa | Alternativa Rejeitada |\n"
            "|---|---|---|---|---|\n"
        ),
        example=(
            "| Backend | FastAPI | 0.104 | Async nativo | Django: overhead |\n"
            "| DB | SQLite | 3.40 | Zero config | PostgreSQL: requer servidor |\n"
        ),
        instruction="Gere APENAS Arquitetura e Tech Stack.",
        min_chars=200,
    ),
    SectionPass(
        pass_id="design_p2",
        sections=["## Módulos", "## Modelo de Dados"],
        template=(
            "## Módulos (C4 — Component Level)\n"
            "| Módulo | Responsabilidade | Interface | Requisitos Atendidos |\n"
            "|---|---|---|---|\n\n"
            "## Modelo de Dados\n"
            "| Entidade | Atributos-chave | Tipo | Relações | Constraints |\n"
            "|---|---|---|---|---|\n"
        ),
        example=(
            "| AuthModule | Autenticação JWT | REST /auth/* | RF-01, RF-02 |\n"
            "| User | id, email, password_hash | PK, UNIQUE | 1:N → Task | email UNIQUE |\n"
        ),
        instruction="Gere APENAS Módulos e Modelo de Dados.",
        min_chars=200,
    ),
    SectionPass(
        pass_id="design_p3",
        sections=["## Fluxo de Dados", "## ADRs", "## Riscos Técnicos"],
        template=(
            "## Fluxo de Dados (Sequencial)\n"
            "1. [Ator] → [Componente] → [Ação] → [Resultado]\n\n"
            "## ADRs (Architecture Decision Records)\n"
            "| ID | Decisão | Contexto | Alternativa Rejeitada | Consequências |\n"
            "|---|---|---|---|---|\n\n"
            "## Riscos Técnicos\n"
            "| ID | Risco | Probabilidade | Impacto | Mitigação | Owner |\n"
            "|---|---|---|---|---|---|\n"
        ),
        example=(
            "1. Usuário → /auth/login → Valida credenciais → JWT\n"
            "| ADR-01 | SQLite para MVP | Deploy local | PostgreSQL | Migrar v2 |\n"
        ),
        instruction="Gere Fluxo (mín 5), ADRs (mín 2) e Riscos (mín 3).",
        min_chars=250,
    ),
]

PLAN_PASSES = [
    SectionPass(
        pass_id="plan_p1",
        sections=["## Arquitetura Sugerida", "## Módulos Core", "## Fases de Implementação"],
        template=(
            "## Arquitetura Sugerida\n"
            "- Estilo: [tipo]\n"
            "- Componentes: [bullets]\n\n"
            "## Módulos Core\n"
            "| Módulo | Responsabilidade | Prioridade | Requisitos (RF-XX) | Estimativa |\n"
            "|---|---|---|---|---|\n\n"
            "## Fases de Implementação\n"
            "| Fase | Duração | Entregas | Critério de Conclusão | Riscos |\n"
            "|---|---|---|---|---|\n"
        ),
        example="",
        instruction="Gere Arquitetura, Módulos Core e Fases.",
        min_chars=250,
    ),
    SectionPass(
        pass_id="plan_p2",
        sections=["## Dependências Técnicas", "## Riscos e Mitigações", "## Plano de Testes"],
        template=(
            "## Dependências Técnicas\n"
            "| Dependência | Versão | Propósito | Alternativa |\n"
            "|---|---|---|---|\n\n"
            "## Riscos e Mitigações\n"
            "| ID | Risco | Fonte | Impacto | Mitigação | Owner |\n"
            "|---|---|---|---|---|---|\n\n"
            "## Plano de Testes\n"
            "| Tipo | Escopo | Ferramenta | Cobertura Mínima |\n"
            "|---|---|---|---|\n"
        ),
        example="",
        instruction="Gere Dependências, Riscos consolidados e Plano de Testes.",
        min_chars=200,
    ),
]
```

---

### 3.3 — `src/core/planner.py` (MODIFICAR)

Adicionar hard gate no `_execute_task()`. Encontre o trecho após `# 3. Store result` e substitua:

```python
        # 2. Pós-processamento: Limpeza de ruído narrativo residual
        clean_result = self._post_process_output(str(result))

        # ═══════════════════════════════════════════════
        # FASE 5.1: HARD GATE — Validação bloqueante
        # ═══════════════════════════════════════════════
        from src.core.output_validator import OutputValidator
        validator = OutputValidator()
        artifact_type_tag = self._get_artifact_tag_for_validator(task)
        validation = validator.validate(clean_result, artifact_type_tag)

        if not validation.get("valid", True):
            fail_reasons = validation.get("fail_reasons", [])
            import sys
            from src.core.stream_handler import ANSIStyle

            # Verificar se é falha total (vazio) ou parcial
            is_empty = any("EMPTY" in r or "TOO_SHORT" in r for r in fail_reasons)

            if is_empty:
                # FALHA TOTAL: artefato vazio — NÃO persistir
                sys.stdout.write(
                    f"\n{ANSIStyle.YELLOW}⚠ [HARD GATE] Artefato "
                    f"'{task.output_artifact}' está VAZIO ou muito curto. "
                    f"Motivos: {fail_reasons}\n"
                    f"Persistindo marcador de falha.{ANSIStyle.RESET}\n"
                )
                sys.stdout.flush()

                # Persistir marcador de falha em vez de string vazia
                clean_result = (
                    f"## {task.output_artifact.upper()} — GERAÇÃO FALHOU\n\n"
                    f"O modelo não produziu conteúdo válido para este artefato.\n"
                    f"Motivos de falha: {', '.join(fail_reasons)}\n\n"
                    f"**Ação necessária:** Re-executar com modelo maior ou "
                    f"fornecer mais contexto.\n"
                )
            else:
                # FALHA PARCIAL: conteúdo existe mas incompleto
                sys.stdout.write(
                    f"\n{ANSIStyle.YELLOW}⚠ [HARD GATE] Artefato "
                    f"'{task.output_artifact}' incompleto. "
                    f"Motivos: {fail_reasons}\n"
                    f"Completude: {int(validation.get('completeness_score', 0)*100)}% "
                    f"(mínimo: {int(validator.MIN_COMPLETENESS.get(artifact_type_tag, 0.6)*100)}%)\n"
                    f"Persistindo com aviso.{ANSIStyle.RESET}\n"
                )
                sys.stdout.flush()

                # Adicionar aviso no topo do artefato
                warning_header = (
                    f"<!-- AVISO: Artefato com completude abaixo do threshold. "
                    f"Seções faltantes: {validation.get('missing_sections', [])} -->\n\n"
                )
                clean_result = warning_header + clean_result

        # 3. Store result
        self.artifact_store.write(
            name=task.output_artifact,
            content=clean_result,
            artifact_type=self._get_artifact_type_from_task(task),
            created_by=task.agent_name
        )

        self.blackboard.set_task_status(task.task_id, TaskStatus.COMPLETED)
```

---

### 3.4 — `src/agents/critic_agent.py` (MODIFICAR)

Adicionar geração seccional no `review_artifact()`:

```python
    def review_artifact(self, artifact_content: str,
                        artifact_type: str = "document",
                        context: str = "") -> str:
        """
        FASE 5.1: Review com geração seccional (2 passes).
        Fallback para chamada única se seccional falhar.
        """
        from src.core.sectional_generator import SectionalGenerator

        # Montar input combinado para o generator
        combined_input = (
            f"ARTEFATO PARA REVISÃO (tipo: {artifact_type}):\n"
            f"{artifact_content[:1500]}"
        )

        generator = SectionalGenerator(
            provider=self.provider,
            direct_mode=self.direct_mode
        )

        result = generator.generate_sectional(
            artifact_type="review",
            user_input=combined_input,
            context=context[:500] if context else "",
        )

        if result and len(result) > 100:
            return result

        # Fallback: chamada única
        return self._review_single_pass(artifact_content, artifact_type, context)

    def _review_single_pass(self, artifact_content: str,
                            artifact_type: str, context: str) -> str:
        """Fallback de review em chamada única."""
        from src.core.golden_examples import REVIEW_EXAMPLE_FRAGMENT

        review_prompt = (
            f"System: {self.system_prompt}\n\n"
            f"ARTEFATO PARA REVISÃO (tipo: {artifact_type}):\n"
            f"{artifact_content}\n\n"
        )
        if context:
            review_prompt += f"CONTEXTO ADICIONAL (NÃO repita):\n{context}\n\n"

        review_prompt += REVIEW_EXAMPLE_FRAGMENT
        review_prompt += (
            "Preencha EXATAMENTE as seções do template de revisão. "
            "NÃO escreva introduções ou conclusões."
        )
        return self.provider.generate(prompt=review_prompt, role="critic")
```

---

### 3.5 — `src/agents/security_reviewer_agent.py` (MODIFICAR)

```python
    def review_security(self, system_design: str, prd_context: str = "") -> str:
        """
        FASE 5.1: Security review com geração seccional (2 passes lite).
        Fallback para chamada única se seccional falhar.
        """
        from src.core.sectional_generator import SectionalGenerator

        combined_input = (
            f"SYSTEM DESIGN PARA ANÁLISE:\n"
            f"{system_design[:1500]}"
        )

        generator = SectionalGenerator(
            provider=self.provider,
            direct_mode=self.direct_mode
        )

        result = generator.generate_sectional(
            artifact_type="security_review",
            user_input=combined_input,
            context=prd_context[:500] if prd_context else "",
        )

        if result and len(result) > 100:
            return result

        # Fallback: chamada única
        return self._review_single_pass(system_design, prd_context)

    def _review_single_pass(self, system_design: str, prd_context: str) -> str:
        """Fallback de security review em chamada única."""
        from src.core.golden_examples import SECURITY_EXAMPLE_FRAGMENT

        prompt = f"System: {self.system_prompt}\n\n"
        prompt += SECURITY_EXAMPLE_FRAGMENT
        if prd_context:
            prompt += f"PRD (REFERÊNCIA):\n{prd_context[:500]}\n\n"
        prompt += (
            f"SYSTEM DESIGN:\n{system_design}\n\n"
            "Preencha EXATAMENTE as seções do template de segurança."
        )
        return self.provider.generate(prompt=prompt, role="security_reviewer")
```

---

## 4. CHECKLIST DE TESTE — FASE 5.1

### ETAPA 1: Imports e Unitários

```
1.  [ ] python -c "from src.core.sectional_generator import SectionalGenerator, REVIEW_PASSES, SECURITY_PASSES; print('OK')"
2.  [ ] python -c "from src.core.output_validator import OutputValidator; v = OutputValidator(); print(v.validate_pass('', ['## Test'], True, 80))"
       → ESPERADO: valid=False, fail_reasons contém TOO_SHORT
3.  [ ] python -m pytest tests/ -v → 100% PASSED
```

### ETAPA 2: Validador de Pass (Sem Ollama)

```python
from src.core.output_validator import OutputValidator
v = OutputValidator()

# Teste 1: pass bom
bom = "## Objetivo\n- Criar app\n\n## Problema\n| ID | P | I | E |\n|---|---|---|---|\n| P-01 | X | Y | Z |"
r = v.validate_pass(bom, ["## Objetivo", "## Problema"], True, 80)
print(f"Pass bom: valid={r['valid']}, fail={r['fail_reasons']}")
# ESPERADO: valid=True

# Teste 2: pass sem heading
ruim = "Aqui está minha análise do problema que é muito complexo e precisa de atenção."
r = v.validate_pass(ruim, ["## Objetivo"], True, 80)
print(f"Pass sem heading: valid={r['valid']}, fail={r['fail_reasons']}")
# ESPERADO: valid=False, MISSING_SECTIONS + NO_TABLE

# Teste 3: pass vazio
r = v.validate_pass("", ["## Test"], True, 80)
print(f"Pass vazio: valid={r['valid']}, fail={r['fail_reasons']}")
# ESPERADO: valid=False, TOO_SHORT

# Teste 4: placeholder heavy
placeholders = "## RF\n| ID | RF | CA | P | C |\n|---|---|---|---|---|\n| ... | ... | ... | ... | ... |\n| ... | ... | ... | ... | ... |"
r = v.validate_pass(placeholders, ["## RF"], True, 80)
print(f"Placeholders: is_placeholder={r['is_placeholder']}")
# ESPERADO: is_placeholder=True
```

```
4.  [ ] Pass bom: valid=True
5.  [ ] Pass sem heading: valid=False
6.  [ ] Pass vazio: valid=False
7.  [ ] Placeholders detectados
```

### ETAPA 3: Sectional com Mock e Retry

```python
from src.core.sectional_generator import SectionalGenerator, SectionPass
from src.models.model_provider import ModelProvider

class FailThenSucceedProvider(ModelProvider):
    def __init__(self):
        self.calls = 0
    def generate(self, prompt, context=None, role="user", max_tokens=None):
        self.calls += 1
        # Primeira chamada de cada pass: retorna lixo
        # Segunda chamada (retry): retorna conteúdo válido
        if "tentativa" in prompt or "ATENÇÃO" in prompt:
            return "## Objetivo\n- Testar retry\n\n## Problema\n| ID | P | I | E |\n|---|---|---|---|\n| P-01 | Bug | Alto | Logs |"
        else:
            return "Certamente! Aqui está uma análise genérica sem tabelas."

provider = FailThenSucceedProvider()
gen = SectionalGenerator(provider, direct_mode=True)

test_pass = SectionPass(
    pass_id="test",
    sections=["## Objetivo", "## Problema"],
    template="## Objetivo\n- [...]\n\n## Problema\n| ID | P | I | E |\n|---|---|---|---|\n",
    example="",
    instruction="Gere Objetivo e Problema.",
    min_chars=80,
)

result = gen._execute_pass_with_retry(
    section_pass=test_pass,
    user_input="App de tarefas",
    context="",
    previous_output="",
    pass_number=1,
    total_passes=1,
)

print(f"Resultado: {result is not None}")
print(f"Chamadas ao LLM: {provider.calls}")
print(f"Contém heading: {'## Objetivo' in (result or '')}")
# ESPERADO: resultado não é None, calls >= 2, contém heading
```

```
8.  [ ] Retry funcionou (resultado não None)
9.  [ ] LLM chamado >= 2 vezes
10. [ ] Resultado contém ## Objetivo
```

### ETAPA 4: E2E com Ollama

```bash
cd idea-forge
python src/cli/main.py
# Inserir ideia simples: "Criar API REST de gerenciamento de tarefas"
```

```
11. [ ] PRD_REVIEW NÃO está vazio no relatório final
12. [ ] SECURITY_REVIEW NÃO está vazio no relatório final
13. [ ] Se algum pass falhou, apareceu "⚠" com motivo no terminal
14. [ ] Se algum pass fez retry, apareceu "Retentando..." no terminal
15. [ ] Relatório contém tabela de Métricas de Qualidade
16. [ ] PRD completude >= 70% na tabela de métricas
17. [ ] SECURITY_REVIEW completude >= 50% na tabela de métricas
18. [ ] Pipeline completou até TASK_06 (development_plan)
19. [ ] .forge/blackboard_state.json atualizado
20. [ ] python -m pytest tests/ -v → 100% PASSED (pós E2E)
```

---

## RESUMO DE RESULTADOS — FASE 5.1

```
ETAPA 1 (Imports/Unitários):    [ ] OK / [ ] ERRO — ___
ETAPA 2 (Validator Pass):       [ ] OK / [ ] ERRO — ___
ETAPA 3 (Retry Mock):           [ ] OK / [ ] ERRO — ___
ETAPA 4 (E2E Ollama):           [ ] OK / [ ] ERRO — ___

Resultado esperado pós 5.1:
- PRD_REVIEW: de 0% para >= 60% completude
- SECURITY_REVIEW: de 0% para >= 50% completude
- Passes falhados: retry visível no terminal
- Artefatos vazios: marcados com "[GERAÇÃO FALHOU]"
```