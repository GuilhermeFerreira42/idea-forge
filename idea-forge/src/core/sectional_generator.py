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
from src.core.pipeline_logger import get_pipeline_logger


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
            logger = get_pipeline_logger()

            # ═══ LOGGER: Pass iniciado ═══
            if logger:
                logger.log_pass(section_pass.pass_id, "START", {
                    "attempt": attempt,
                    "sections": section_pass.sections,
                    "pass_number": pass_number,
                    "total_passes": total_passes,
                })

            # Construir prompt
            prompt = self._build_pass_prompt(
                section_pass=section_pass,
                user_input=user_input,
                context=context,
                previous_output=previous_output,
                pass_number=pass_number,
                total_passes=total_passes,
            )

            # ═══ LOGGER: Prompt construído (Request) ═══
            if logger:
                logger.log_llm_request(
                    agent=section_pass.pass_id,
                    role=self._get_role(section_pass.pass_id),
                    prompt=prompt,
                    pass_info=f"pass_{pass_number}_attempt_{attempt}",
                    attempt=attempt,
                )

            # Se é retry, adicionar instrução corretiva
            if attempt > 1 and last_fail_reasons:
                prompt += self._build_retry_instruction(
                    section_pass, last_fail_reasons, attempt
                )

            # Gerar
            result = self.provider.generate(prompt=prompt, role=self._get_role(section_pass.pass_id))
            result = self._clean_pass_output(result)

            # ═══ LOGGER: Resposta recebida ═══
            if logger:
                logger.log_llm_response(
                    agent=section_pass.pass_id,
                    content=result,
                    tokens_processed=len(result) // 4 if result else 0,
                )

            # Validar
            validation = self.validator.validate_pass(
                content=result,
                expected_sections=section_pass.sections,
                require_table=section_pass.require_table,
                min_chars=section_pass.min_chars,
            )

            if validation["valid"]:
                # ═══ LOGGER: Pass aprovado ═══
                if logger:
                    logger.log_pass(section_pass.pass_id, "VALID", {
                        "attempt": attempt,
                        "char_count": validation.get("char_count", 0),
                        "has_table": validation.get("has_table", False),
                    })

                if attempt > 1:
                    self._emit_ok(f"  Pass {pass_number} corrigido na tentativa {attempt}")
                return result

            # Falhou — preparar retry
            last_fail_reasons = validation.get("fail_reasons", ["UNKNOWN"])

            # ═══ LOGGER: Pass falhou ═══
            if logger:
                logger.log_pass(section_pass.pass_id, "FAIL", {
                    "attempt": attempt,
                    "fail_reasons": last_fail_reasons,
                    "action": "RETRYING" if attempt <= MAX_RETRIES_PER_PASS else "GIVING_UP",
                    "char_count": validation.get("char_count", 0),
                })

            if attempt <= MAX_RETRIES_PER_PASS:
                self._emit_warn(
                    f"  Pass {pass_number} tentativa {attempt} falhou: "
                    f"{last_fail_reasons}. Retentando..."
                )

        # Todos os retries falharam
        return None

    def _get_role(self, pass_id: str) -> str:
        """Determina o folder do modelo baseado no ID do pass."""
        if pass_id.startswith("prd"): return "product_manager"
        if pass_id.startswith("design"): return "architect"
        if pass_id.startswith("review"): return "critic"
        if pass_id.startswith("security"): return "security_reviewer"
        if pass_id.startswith("plan"): return "planner"
        return "user"

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

# ─── DESIGN: 3 passes ────────────
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
