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
                 min_chars: int = 80,
                 input_budget: int = 600,
                 context_artifacts: List[str] = None):
        self.pass_id = pass_id
        self.sections = sections
        self.template = template
        self.example = example
        self.instruction = instruction
        self.max_output_tokens = max_output_tokens
        self.require_table = require_table
        self.min_chars = min_chars
        self.input_budget = input_budget
        self.context_artifacts = context_artifacts or []


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

    def generate_sectional_with_inputs(self, artifact_type: str,
                                        pass_inputs: List[str],
                                        passes: List[SectionPass]) -> Optional[str]:
        """
        FASE 9.2: Gera artefato com input diferente por pass (contexto seletivo).
        """
        if not passes or len(passes) != len(pass_inputs):
            return None

        accumulated_output = ""
        pass_results = []
        failed_passes = 0

        for i, section_pass in enumerate(passes):
            self._emit(f"[PASS {i+1}/{len(passes)}] "
                       f"Gerando: {', '.join(section_pass.sections)}")

            result = self._execute_pass_with_retry(
                section_pass=section_pass,
                user_input=pass_inputs[i],
                context="",
                previous_output=accumulated_output,
                pass_number=i + 1,
                total_passes=len(passes),
            )

            if result is None:
                failed_passes += 1
                self._emit_warn(
                    f"Pass {i+1} FALHOU. Seções: {section_pass.sections}"
                )
                failed_marker = "\n".join(
                    f"{s}\n- [GERAÇÃO FALHOU — seção não produzida pelo modelo]"
                    for s in section_pass.sections
                )
                pass_results.append(failed_marker)
            else:
                pass_results.append(result)
                accumulated_output += result + "\n\n"

        if failed_passes > len(passes) / 2:
            self._emit_warn(f"FALHA ESTRUTURAL: {failed_passes}/{len(passes)} passes falharam.")
            return None

        final_output = "\n\n".join(pass_results)

        validation = self.validator.validate(final_output, artifact_type)
        if validation.get("valid"):
            self._emit_ok(
                f"Artefato aprovado — density: {validation['density_score']:.2f}, "
                f"completude: {int(validation['completeness_score']*100)}%"
            )
        else:
            self._emit_warn(f"Artefato com problemas: {validation.get('fail_reasons', [])}")

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
            # FASE 9.1.1: Passar max_tokens ao provider
            result = self.provider.generate(
                prompt=prompt,
                role=self._get_role(section_pass.pass_id),
                max_tokens=section_pass.max_output_tokens
            )
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

    def _get_role(self, pass_id: str) -> str:
        """Determina o folder do modelo baseado no ID do pass."""
        if pass_id.startswith("prd"): return "product_manager"
        if pass_id.startswith("final"): return "product_manager"  # FASE 9.1
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
        # FASE 9.2: Usar CONSOLIDATOR_DIRECTIVE para passes do prd_final
        if section_pass.pass_id.startswith("final"):
            from src.core.prompt_templates import CONSOLIDATOR_DIRECTIVE
            system = CONSOLIDATOR_DIRECTIVE
        else:
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
            prompt += f"REFERÊNCIA DE FORMATO E PROFUNDIDADE:\n{section_pass.example}\n\n"

        # FASE 9.1.1: Usar input_budget do pass em vez de 600 fixo
        budget = getattr(section_pass, 'input_budget', 600)
        prompt += f"PROJETO:\n{user_input[:budget]}\n\n"

        if previous_output:
            summary = self._summarize_previous(previous_output, max_tokens=500)
            prompt += (
                f"SEÇÕES JÁ GERADAS (NÃO repita, apenas referencie IDs se necessário):\n"
                f"{summary}\n\n"
            )

        if context:
            prompt += f"CONTEXTO ADICIONAL:\n{context[:400]}\n\n"

        prompt += f"{section_pass.instruction}\n"

        return prompt

    def _summarize_previous(self, text: str, max_tokens: int = 500) -> str:
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
        elif artifact_type == "prd_final":          # FASE 9.1
            return NEXUS_FINAL_PASSES
        return []


# ═══════════════════════════════════════════════════════════
# PASSES POR TIPO DE ARTEFATO
# ═══════════════════════════════════════════════════════════

# FASE 7: PRD_PASSES recalibrado para padrão NEXUS (5 passes)
PRD_PASSES = [
    SectionPass(
        pass_id="prd_p1",
        sections=["## Objetivo", "## Problema"],
        template=(
            "## Objetivo\n"
            "- [1 frase, verbo no infinitivo, máximo 30 palavras, que capture o diferencial]\n\n"
            "## Problema\n"
            "| ID | Problema | Impacto | Como o Sistema Resolve |\n"
            "|---|---|---|---|\n"
            "| P-01 | ... | ... | ... |\n"
        ),
        example=(
            "## Objetivo\n"
            "- Permitir gerenciamento de tarefas pessoais com sincronização offline-first\n\n"
            "## Problema\n"
            "| ID | Problema | Impacto | Como o Sistema Resolve |\n"
            "|---|---|---|---|\n"
            "| P-01 | Apps existentes requerem internet | Perda de dados offline | Sync offline-first com CRDT |\n"
            "| P-02 | Complexidade excessiva | Abandono em 7 dias | Interface minimalista com 3 ações |\n"
        ),
        instruction="Gere APENAS Objetivo e Problema. Mínimo 4 problemas na tabela com coluna 'Como Resolve'.",
        min_chars=200,
        max_output_tokens=1500,
    ),
    SectionPass(
        pass_id="prd_p2",
        sections=["## Público-Alvo", "## Princípios Arquiteturais", "## Diferenciais"],
        template=(
            "## Público-Alvo\n"
            "| Segmento | Perfil (nome + dor) | Prioridade |\n"
            "|---|---|---|\n\n"
            "## Princípios Arquiteturais\n"
            "| Princípio | Descrição Concreta | Implicação Técnica |\n"
            "|---|---|---|---|\n\n"
            "## Diferenciais\n"
            "| Abordagem Atual | Problema | Como Este Sistema Supera |\n"
            "|---|---|---|---|\n"
        ),
        example=(
            "| Dev Indie | Lucas, dev solo, quer validar ideias antes de codar | P0 |\n"
            "| Startup | Time de 5 sem PM dedicado | P1 |\n"
        ),
        instruction="Gere APENAS Público-Alvo (mín 3), Princípios (mín 3) e Diferenciais (mín 3). Todas com tabelas.",
        min_chars=250,
        max_output_tokens=1500,
    ),
    SectionPass(
        pass_id="prd_p3",
        sections=["## Requisitos Funcionais", "## Requisitos Não-Funcionais"],
        template=(
            "## Requisitos Funcionais\n"
            "| ID | Requisito | Critério de Aceite (verificável) | Prioridade (MoSCoW) | Complexidade |\n"
            "|---|---|---|---|---|\n"
            "| RF-01 | ... | [teste automatizável] | Must/Should/Could | Low/Med/High |\n\n"
            "## Requisitos Não-Funcionais\n"
            "| ID | Categoria | Requisito | Métrica | Target |\n"
            "|---|---|---|---|---|\n"
        ),
        example=(
            "| RF-01 | CRUD de tarefas | POST/GET/PUT/DELETE retorna status HTTP correto | Must | Low |\n"
            "| RF-02 | Filtro por status | GET /tasks?status=done retorna subset | Should | Low |\n"
            "| RNF-01 | Performance | Latência API | p95 | <200ms |\n"
        ),
        instruction="Gere APENAS RF (mínimo 8) e RNF (mínimo 5). IDs sequenciais. Critérios de aceite DEVEM ser testes automatizáveis.",
        min_chars=400,
        max_output_tokens=1500,
    ),
    SectionPass(
        pass_id="prd_p4",
        sections=["## Escopo MVP", "## Métricas de Sucesso"],
        template=(
            "## Escopo MVP\n"
            "**Inclui:** [lista referenciando RF-XX]\n"
            "**NÃO inclui:** [lista com justificativa]\n\n"
            "## Métricas de Sucesso\n"
            "| Métrica | Target | Prazo | Como Medir |\n"
            "|---|---|---|---|\n"
        ),
        example=(
            "**Inclui:**\n- RF-01 a RF-05 — core CRUD + auth\n\n"
            "**NÃO inclui:**\n- Notificações push (v2) — complexidade alta, não essencial\n"
        ),
        instruction="Gere APENAS Escopo e Métricas. Referencie IDs RF-XX no escopo.",
        min_chars=200,
        max_output_tokens=1200,
    ),
    SectionPass(
        pass_id="prd_p5",
        sections=["## Dependências e Riscos", "## Constraints Técnicos"],
        template=(
            "## Dependências e Riscos\n"
            "| ID | Tipo | Descrição | Probabilidade | Impacto | Mitigação |\n"
            "|---|---|---|---|---|---|\n\n"
            "## Constraints Técnicos\n"
            "- Linguagem: [...]\n"
            "- Framework: [...]\n"
            "- Banco de dados: [...]\n"
            "- Infraestrutura: [...]\n"
            "- Restrições de segurança: [...]\n"
        ),
        example=(
            "| R-01 | Risco | SQLite sem escrita concorrente | Média | Alto | WAL mode |\n"
            "| R-02 | Dependência | Ollama deve estar rodando | Alta | Crítico | Health check no startup |\n"
        ),
        instruction="Gere APENAS Riscos (mínimo 5) e Constraints Técnicos.",
        min_chars=200,
        max_output_tokens=1200,
    ),
]

# ─── REVIEW: 2 passes calibrados (Fase 7) ──────────────────────────

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
        max_output_tokens=1000,
    ),
    SectionPass(
        pass_id="review_p2",
        sections=["## Verificação de Requisitos", "## Verificação de Princípios Arquiteturais", "## Sumário", "## Recomendação"],
        template=(
            "## Verificação de Requisitos\n"
            "| Requisito ID | Status | Notas |\n"
            "|---|---|---|\n"
            "| RF-01 | ✅ Atendido / ❌ Não atendido | ... |\n\n"
            "## Verificação de Princípios Arquiteturais\n"
            "| Princípio | Respeitado? | Evidência |\n"
            "|---|---|---|\n\n"
            "## Sumário\n"
            "- [1-2 frases]\n\n"
            "## Recomendação\n"
            "- [Ação específica]\n"
        ),
        example="",
        instruction=(
            "Verifique cada RF/RNF e Princípio Arquitetural. "
            "Gere Verificação + Sumário + Recomendação."
        ),
        min_chars=200,
        max_output_tokens=1000,
        require_table=True,
    ),
]

# ─── SECURITY: 2 passes calibrados (Fase 7) ────────────────────────

SECURITY_PASSES = [
    SectionPass(
        pass_id="security_p1",
        sections=["## Superfície de Ataque", "## Ameaças Identificadas"],
        template=(
            "## Superfície de Ataque\n"
            "| Componente | Tipo de Exposição | Nível de Risco | Justificativa |\n"
            "|---|---|---|---|\n\n"
            "## Ameaças Identificadas (STRIDE)\n"
            "| ID | Categoria STRIDE | Componente | Ameaça | Severidade | Mitigação Concreta |\n"
            "|---|---|---|---|---|---|\n"
            "| T-01 | S/T/R/I/D/E | ... | ... | Alta/Média/Baixa | ... |\n"
        ),
        example=(
            "| API /auth | HTTP | Alto | Exposta à internet |\n\n"
            "| T-01 | S (Spoofing) | /auth/login | Brute force | Alta | Rate limit 5/min |\n"
        ),
        instruction=(
            "Analise o System Design e identifique superfície de ataque + ameaças STRIDE. "
            "Mínimo 3 ameaças."
        ),
        min_chars=250,
        max_output_tokens=1000,
    ),
    SectionPass(
        pass_id="security_p2",
        sections=["## Requisitos de Segurança Derivados", "## Dados Sensíveis", "## Plano de Autenticação/Autorização"],
        template=(
            "## Requisitos de Segurança Derivados\n"
            "| ID | Requisito | Prioridade | Ameaça Mitigada |\n"
            "|---|---|---|---|\n"
            "| RS-01 | ... | Must/Should | T-XX |\n\n"
            "## Dados Sensíveis\n"
            "| Dado | Classificação | Criptografia | Retenção |\n"
            "|---|---|---|---|\n\n"
            "## Plano de Autenticação/Autorização\n"
            "- Mecanismo: [...]\n"
            "- Granularidade: [...]\n"
        ),
        example="",
        instruction=(
            "Gere requisitos derivados, classificação de dados e plano de auth."
        ),
        min_chars=200,
        max_output_tokens=1000,
    ),
]

# ─── DESIGN: 3 passes calibrados (Fase 7) ──────────────────────────

DESIGN_PASSES = [
    SectionPass(
        pass_id="design_p1",
        sections=["## Arquitetura Geral", "## Tech Stack"],
        template=(
            "## Arquitetura Geral\n"
            "- Estilo: [tipo]\n"
            "- Containers: [lista]\n"
            "- Diagrama (texto): ...\n\n"
            "## Tech Stack\n"
            "| Camada | Tecnologia | Versão | Justificativa | Alternativa Rejeitada | Motivo Rejeição |\n"
            "|---|---|---|---|---|---|\n"
        ),
        example=(
            "| Backend | FastAPI | 0.104 | Async nativo | Django | Overhead |\n"
        ),
        instruction="Gere Arquitetura e Tech Stack com alternativas rejeitadas.",
        min_chars=250,
        max_output_tokens=1200,
    ),
    SectionPass(
        pass_id="design_p2",
        sections=["## Módulos", "## Modelo de Dados"],
        template=(
            "## Módulos\n"
            "| Módulo | Responsabilidade | Interface | Requisitos (RF-XX) |\n"
            "|---|---|---|---|\n\n"
            "## Modelo de Dados\n"
            "| Entidade | Atributos-chave | Tipo | Relações | Constraints |\n"
            "|---|---|---|---|---|\n"
        ),
        example=(
            "| AuthModule | Autenticação | REST /auth/* | RF-01 |\n"
        ),
        instruction="Gere Módulos e Modelo de Dados.",
        min_chars=250,
        max_output_tokens=1200,
    ),
    SectionPass(
        pass_id="design_p3",
        sections=["## Fluxo de Dados", "## ADRs", "## Riscos Técnicos", "## Requisitos de Infraestrutura"],
        template=(
            "## Fluxo de Dados\n"
            "1. [Ator] → [Ação] → [Resultado]\n\n"
            "## ADRs (Architecture Decision Records)\n"
            "| ID | Decisão | Contexto | Alternativa Rejeitada | Consequências | Mitigação |\n"
            "|---|---|---|---|---|---|\n\n"
            "## Riscos Técnicos\n"
            "| ID | Risco | Probabilidade | Impacto | Mitigação | Owner |\n"
            "|---|---|---|---|---|---|\n\n"
            "## Requisitos de Infraestrutura\n"
            "| Recurso | Mínimo | Recomendado | Justificativa |\n"
            "|---|---|---|---|\n"
        ),
        example=(
            "| ADR-01 | SQLite | MVP local | PostgreSQL | Simplicidade | WAL mode |\n"
        ),
        instruction="Gere Fluxo (mín 5), ADRs (mín 3), Riscos e Infra.",
        min_chars=400,
        max_output_tokens=1200,
    ),
]

# ─── PLAN: 4 passes calibrados (Fase 7) ────────────────────────────

PLAN_PASSES = [
    SectionPass(
        pass_id="plan_p1",
        sections=["## Arquitetura Sugerida", "## Módulos Core"],
        template=(
            "## Arquitetura Sugerida\n"
            "- Estilo: [tipo]\n"
            "- Componentes: [bullets]\n\n"
            "## Módulos Core\n"
            "| Módulo | Responsabilidade | Prioridade | Requisitos (RF-XX) | Estimativa (dias) |\n"
            "|---|---|---|---|---|\n"
        ),
        example="",
        instruction="Gere Arquitetura e Módulos Core.",
        min_chars=250,
        max_output_tokens=1200,
    ),
    SectionPass(
        pass_id="plan_p2",
        sections=["## Fases de Implementação", "## Dependências Técnicas"],
        template=(
            "## Fases de Implementação\n"
            "| Fase | Duração | Entregas Concretas | Critério de Conclusão | Dependência |\n"
            "|---|---|---|---|---|\n\n"
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

# ─── NEXUS FINAL: 12 passes para PRD Final consolidado (Fase 9.3) ─────────
NEXUS_FINAL_PASSES = [
    # === PASS 1: Visão e Identidade ===
    SectionPass(
        pass_id="final_p01",
        sections=["## Visão do Produto", "## Problema e Solução"],
        template=(
            "## Visão do Produto\n"
            "- **Codinome:** [nome memorável]\n"
            "- **Declaração de visão:** [1 frase, máx 30 palavras]\n\n"
            "## Problema e Solução\n"
            "| ID | Problema | Impacto | Como o Sistema Resolve |\n"
            "|---|---|---|---|\n"
            "(mínimo 5 problemas com impacto mensurável e solução técnica concreta)\n"
        ),
        example=(
            "- **Codinome:** OmniPrice Next\n"
            "- **Declaração de visão:** Unificar ofertas de marketplaces com ISR para SEO e performance de ponta.\n\n"
            "| P-01 | APIs heterogêneas por marketplace | Dados inconsistentes e falha na normalização | Pipeline ETL com schema normalizado (Zod) |\n"
            "| P-02 | Latência na atualização de preços | Preço divergente no checkout gerando reclamações | ISR com revalidate automático a cada 60s |\n"
            "| P-03 | Falta de histórico de preço | Usuário não sabe se o preço atual é bom | Snapshots diários com gráfico de tendência de 90 dias |\n"
            "| P-04 | Bloqueio por scraping | Interrupção do serviço e perda de receita | Proxy rotation com pool de 100+ IPs e backoff |\n"
            "| P-05 | SEO ruim em páginas dinâmicas | Perda de tráfego orgânico | SSR/ISR no Next.js com sitemap dinâmico |\n"
        ),
        instruction=(
            "Sintetize visão e problemas do projeto a partir dos artefatos.\n"
            "Mínimo 5 problemas. Cada problema deve ter impacto mensurável e solução técnica concreta.\n"
            "Escreva com profundidade técnica. NÃO use generalidades."
        ),
        min_chars=600,
        max_output_tokens=2500,
        input_budget=2500,
        context_artifacts=["prd"],
    ),

    # === PASS 2: Público-Alvo ===
    SectionPass(
        pass_id="final_p02",
        sections=["## Público-Alvo"],
        template=(
            "## Público-Alvo\n"
            "| Segmento | Perfil (nome fictício + dor com contexto) | Prioridade |\n"
            "|---|---|---|\n"
            "(mínimo 3 personas com nome, idade e narrativa de 2-3 frases)\n"
        ),
        example=(
            "| Caçador de Oferta | Marina, 28 anos — Abre 6 abas para comparar preço de um fone "
            "Bluetooth. Gasta 40min por compra e não tem certeza se achou o menor preço. Já perdeu "
            "promoções de Black Friday por não monitorar preços. | P0 |\n"
            "| Afiliado Digital | Carlos, 34 anos — Cria reviews no Instagram e precisa de links rastreáveis "
            "com páginas rápidas. Taxa de bounce em sites lentos é 65%, perdendo cerca de R$800/mês em comissões. | P0 |\n"
            "| Comprador Recorrente | Dona Fátima, 52 anos — Compra produtos de limpeza todo mês. Quer alerta "
            "quando o preço cair abaixo do valor aceitável. Já perdeu ofertas de supermercado por não ter monitoramento automático. | P1 |\n"
        ),
        instruction=(
            "Crie personas ricas com nome fictício, idade e narrativa de 1-2 frases sobre a dor real.\n"
            "NÃO use rótulos genéricos. Mínimo 3 personas."
        ),
        min_chars=200,
        max_output_tokens=1000,
        input_budget=1500,
        context_artifacts=["prd"],
    ),

    # === PASS 3: Princípios e Diferenciais ===
    SectionPass(
        pass_id="final_p03",
        sections=["## Princípios Arquiteturais", "## Diferenciais"],
        template=(
            "## Princípios Arquiteturais\n"
            "| Princípio | Descrição | Implicação Técnica | Regra Verificável |\n"
            "|---|---|---|---|\n"
            "(mínimo 3 princípios, cada um com REGRA: verificável por teste)\n\n"
            "## Diferenciais\n"
            "| Abordagem Atual | Problema | Como Este Sistema Supera |\n"
            "|---|---|---|\n"
            "(mínimo 3 diferenciais vs concorrentes ou abordagem manual)\n"
        ),
        example=(
            "| ISR First | Páginas pré-renderizadas a cada 60s | revalidate no Next.js | "
            "REGRA: Nenhuma página usa force-dynamic. Teste verifica header x-nextjs-cache |\n"
            "| Schema-First | Contratos de API garantem tipagem | Zod para validação em runtime | "
            "REGRA: Todo entrypoint de API tem schema validado. Teste envia payload inválido |\n\n"
            "| Scraping em tempo real | Lentidão 3-8s e bloqueio de IP | "
            "Cache ISR: dados servidos em <100ms com invalidação por webhook | Supera concorrentes em 40x |\n"
        ),
        instruction=(
            "Princípios: cada um DEVE ter coluna 'Regra Verificável' com texto 'REGRA:'.\n"
            "Diferenciais: compare com concorrentes reais ou abordagem manual atual."
        ),
        min_chars=700,
        max_output_tokens=2500,
        input_budget=2500,
        context_artifacts=["prd", "system_design"],
    ),

    # === PASS 4: Requisitos Funcionais ===
    SectionPass(
        pass_id="final_p04",
        sections=["## Requisitos Funcionais"],
        template=(
            "## Requisitos Funcionais (Consolidados)\n"
            "| ID | Requisito | Critério de Aceite | Prioridade | Complexidade | Status Pós-Review |\n"
            "|---|---|---|---|---|---|\n"
            "(mínimo 6 RFs. Critérios DEVEM ser testes automatizáveis com endpoint e status HTTP)\n"
        ),
        example=(
            "| RF-01 | Busca Unificada | GET /api/search retorna 200 com resultados de >=2 marketplaces no JSON | Must | Med | Aprovado |\n"
            "| RF-02 | Página de Produto ISR | /produto/[slug] retorna 200 com header x-nextjs-cache: HIT ou STALE | Must | High | Aprovado |\n"
            "| RF-03 | Alerta de Preço | POST /api/alerts cria registro no DB e retorna 201 Created | Should | High | Aprovado |\n"
        ),
        instruction=(
            "Consolide RFs do PRD original com status do Review. Mínimo 6 RFs.\n"
            "Critérios de aceite DEVEM incluir endpoint, status HTTP e formato de resposta."
        ),
        min_chars=600,
        max_output_tokens=2500,
        input_budget=2500,
        context_artifacts=["prd", "prd_review"],
    ),

    # === PASS 5: Requisitos Não-Funcionais ===
    SectionPass(
        pass_id="final_p05",
        sections=["## Requisitos Não-Funcionais"],
        template=(
            "## Requisitos Não-Funcionais\n"
            "| ID | Categoria | Requisito | Métrica | Target |\n"
            "|---|---|---|---|---|\n"
            "(mínimo 4 RNFs com target NUMÉRICO. Categorias: Performance, SEO, Disponibilidade, Segurança)\n"
        ),
        example=(
            "| RNF-01 | Performance | LCP em páginas de produto | p95 Lighthouse | <2.5s |\n"
            "| RNF-02 | SEO | Indexabilidade | Google Search Console | 100% válidos |\n"
            "| RNF-03 | Disponibilidade | Uptime do Gateway de Busca | SLA mensal | 99.9% |\n"
            "| RNF-04 | Segurança | Resposta de erro ofuscada | Penetration Test | 100% sem vazamento |\n"
        ),
        instruction="Mínimo 4 RNFs. Target DEVE ser numérico, nunca 'bom' ou 'adequado'.",
        min_chars=200,
        max_output_tokens=1000,
        input_budget=1500,
        context_artifacts=["prd"],
    ),

    # === PASS 6: Arquitetura e Tech Stack ===
    SectionPass(
        pass_id="final_p06",
        sections=["## Arquitetura e Tech Stack", "## ADRs"],
        template=(
            "## Arquitetura e Tech Stack\n"
            "- **Estilo:** [tipo de arquitetura]\n"
            "| Camada | Tecnologia | Justificativa |\n"
            "|---|---|---|\n"
            "(mínimo 3 camadas)\n\n"
            "## ADRs (Decisões Arquiteturais)\n"
            "| ID | Decisão | Alternativa Rejeitada | Consequências |\n"
            "|---|---|---|---|\n"
            "(mínimo 3 ADRs com trade-off real)\n"
        ),
        example=(
            "| Frontend | Next.js 14 + Vercel Edge | SSR/ISR nativo para SEO e Core Web Vitals |\n"
            "| API Layer | FastAPI (Python) | Alta performance em I/O assíncrono para scraping |\n"
            "| ADR-01 | ISR | SSR puro | Reduz latência drasticamente; trade-off de dados de até 60s |\n"
            "| ADR-02 | PostgreSQL | MongoDB | Garantia de integridade referencial para catálogo complexo |\n"
        ),
        instruction=(
            "Sintetize do System Design. ADRs: incluir trade-off real, não apenas 'melhor opção'.\n"
            "Mínimo 3 camadas e 3 ADRs."
        ),
        min_chars=800,
        max_output_tokens=2500,
        input_budget=3000,
        context_artifacts=["system_design"],
    ),

    # === PASS 7: Análise de Segurança ===
    SectionPass(
        pass_id="final_p07",
        sections=["## Análise de Segurança"],
        template=(
            "## Análise de Segurança\n"
            "| ID | Ameaça STRIDE | Componente | Severidade | Mitigação Concreta |\n"
            "|---|---|---|---|---|\n"
            "(mínimo 3 ameaças. Mitigação DEVE ser específica, não genérica)\n"
        ),
        example=(
            "| SEC-01 | Spoofing | API Gateway | Alta | JWT + Rate Limiting 60 req/min via slowapi |\n"
            "| SEC-02 | Injection | Banco de Dados | Alta | Consultas parametrizadas com ORM |\n"
            "| SEC-03 | Information Disclosure | Log de Erro | Média | Limpar stacktraces em prod via middleware |\n"
            "| SEC-04 | Denial of Service | Crawler | Alta | Cloudflare WAF + bloqueio de geo-IP suspeito |\n"
        ),
        instruction="Sintetize do Security Review. Mitigação deve ser ESPECÍFICA com ferramenta/lib mencionada.",
        min_chars=500,
        max_output_tokens=2000,
        input_budget=2500,
        context_artifacts=["security_review"],
    ),

    # === PASS 8: Escopo MVP ===
    SectionPass(
        pass_id="final_p08",
        sections=["## Escopo MVP"],
        template=(
            "## Escopo MVP\n"
            "**Inclui:** [lista com RF-XX — APENAS IDs existentes na tabela de RFs]\n"
            "**NÃO inclui:** [lista com justificativa técnica para cada exclusão]\n"
        ),
        example=(
            "**Inclui:**\n- RF-01 (Busca Unificada)\n- RF-02 (Página ISR)\n- RF-03 (Histórico de Preço)\n"
            "- RF-04 (Autenticação)\n- RF-05 (Favoritos)\n- RF-06 (Alertas)\n\n"
            "**NÃO inclui:**\n- RF-07 (Checkout) — complexidade de integração exige 8 semanas adicionais\n"
            "- RF-08 (Marketplace) — modelo de negócio focado em agregação na V1\n"
        ),
        instruction="Referencie APENAS RF-IDs da tabela de RFs gerada anteriormente. NÃO invente IDs novos.",
        min_chars=300,
        max_output_tokens=1500,
        input_budget=2000,
        require_table=False,
        context_artifacts=["prd"],
    ),

    # === PASS 9: Riscos Consolidados e Métricas ===
    SectionPass(
        pass_id="final_p09",
        sections=["## Riscos Consolidados", "## Métricas de Sucesso"],
        template=(
            "## Riscos Consolidados (PRD + Design + Security)\n"
            "| ID | Risco | Fonte | Probabilidade | Impacto | Mitigação |\n"
            "|---|---|---|---|---|---|\n"
            "(mínimo 4 riscos)\n\n"
            "## Métricas de Sucesso\n"
            "| Métrica | Target | Prazo | Como Medir |\n"
            "|---|---|---|---|\n"
            "(mínimo 4 métricas com target numérico e método concreto de medição)\n"
        ),
        example=(
            "| R-01 | Bloqueio de IP | Security | Alta | Crítico | Proxy rotation + delay 2-5s |\n"
            "| R-02 | Injeção de Código | Backend | Alta | Sanitização rigorosa com Zod schemas |\n\n"
            "| LCP | <2.5s | Contínuo | Lighthouse CI no pipeline de CI/CD via GitHub Actions |\n"
            "| Conversão | >3% | Mensal | Google Analytics 4 com funil de eventos customizados |\n"
        ),
        instruction=(
            "Consolide riscos de PRD, Design e Security. Mínimo 4 riscos e 4 métricas.\n"
            "Métricas: 'Como Medir' deve descrever ferramenta E frequência."
        ),
        min_chars=600,
        max_output_tokens=2500,
        input_budget=3000,
        context_artifacts=["prd", "system_design", "security_review"],
    ),

    # === PASS 10: Plano e Decisões do Debate ===
    SectionPass(
        pass_id="final_p10",
        sections=["## Plano de Implementação", "## Decisões do Debate"],
        template=(
            "## Plano de Implementação\n"
            "| Fase | Duração | Entregas | Critério de Conclusão | Dependência |\n"
            "|---|---|---|---|---|\n"
            "(mínimo 3 fases com critério verificável)\n\n"
            "## Decisões do Debate\n"
            "| Round | Tipo | Decisão | Justificativa Técnica |\n"
            "|---|---|---|---|\n"
            "(extrair pontos de consenso do debate)\n"
        ),
        example=(
            "| Fase 1 | 2 semanas | Infra + DB | docker-compose up funcional; migrations rodadas | Nenhuma |\n"
            "| Fase 2 | 3 semanas | API Core | Cobertura >=80%; Swagger documentado | Fase 1 |\n\n"
            "| R2 | ACEITO | Near Real-Time em vez de Real-Time | ISR não garante sincronia milissegundo real-time |\n"
            "| R3 | REPROVADO | Auth via Telefone | Complexidade técnica fora do escopo MVP atual |\n"
        ),
        instruction=(
            "Plano: critério de conclusão VERIFICÁVEL (ex: 'cobertura >=80%').\n"
            "Decisões: extraia dos Pontos Aceitos e Melhorias do transcript do debate."
        ),
        min_chars=600,
        max_output_tokens=2500,
        input_budget=3000,
        context_artifacts=["development_plan", "debate_transcript"],
    ),

    # === PASS 11: Constraints + Matriz + Limitações ===
    SectionPass(
        pass_id="final_p11",
        sections=["## Constraints Técnicos", "## Matriz de Rastreabilidade", "## Limitações Conhecidas"],
        template=(
            "## Constraints Técnicos\n"
            "- Linguagem: [valor com versão]\n"
            "- Framework: [valor com versão]\n"
            "- Banco de dados: [valor]\n"
            "- Infraestrutura: [provedores]\n"
            "- Segurança: [lista concreta]\n\n"
            "## Matriz de Rastreabilidade\n"
            "| RF-ID | Componente | Teste Associado | Status |\n"
            "|---|---|---|---|\n"
            "(cada RF da tabela anterior DEVE aparecer)\n\n"
            "## Limitações Conhecidas\n"
            "| ID | Limitação | Severidade | Impacto | Workaround | Quando Resolvida |\n"
            "|---|---|---|---|---|---|\n"
            "(mínimo 3 limitações com workaround concreto)\n"
        ),
        example=(
            "- Linguagem: TypeScript 5+ (Strict Mode ativado)\n"
            "- Framework: Next.js 14 (App Router + Server Components)\n"
            "- Infraestrutura: Vercel + AWS Lambda (Edge Computing)\n\n"
            "| RF-01 | SearchModule | Unit (Jest): retorna resultados de >=2 marketplaces | Planejado |\n"
            "| RF-02 | SearchAPI | Integration (Supertest): GET /api/search return 200 OK | Planejado |\n\n"
            "| LIM-01 | Bloqueio de IP | Alta | Coleta falha temporariamente | Proxy rotation + cache | v1.1 |\n"
            "| LIM-02 | Latência de Index | Média | Preço stale por 60s | Badge 'stale data' | v1.2 |\n"
        ),
        instruction=(
            "Constraints: valores CONCRETOS com versão.\n"
            "Rastreabilidade: cada RF DEVE aparecer exatamente 1 vez.\n"
            "Limitações: workaround concreto que o sistema já faz, não plano futuro."
        ),
        min_chars=600,
        max_output_tokens=2500,
        input_budget=2500,
        context_artifacts=["prd", "system_design"],
    ),

    # === PASS 12: Guia de Replicação + Cláusula ===
    SectionPass(
        pass_id="final_p12",
        sections=["## Guia de Replicação Resumido", "## Cláusula de Integridade"],
        template=(
            "## Guia de Replicação Resumido\n"
            "1. **Pré-requisitos:** [linguagem, versões exatas, ferramentas]\n"
            "2. **Instalação:** [comandos exatos]\n"
            "3. **Execução:** [comando para rodar]\n"
            "4. **Verificação:** [URL + resposta esperada]\n\n"
            "## Cláusula de Integridade\n"
            "| Item | Status |\n"
            "|---|---|\n"
            "| Todos os RF-IDs do Escopo existem na tabela de RFs | [checkmark/X] |\n"
            "| Todos os riscos HIGH possuem mitigação | [checkmark/X] |\n"
            "| Tech Stack consistente entre seções | [checkmark/X] |\n"
            "| Métricas possuem target quantitativo | [checkmark/X] |\n"
            "| Security Review endereça ameaças HIGH | [checkmark/X] |\n"
        ),
        example=(
            "1. **Pré-requisitos:** Node.js 18.17+, Python 3.11+, Docker 24+, PostgreSQL 16+\n"
            "2. **Instalação:** git clone repo && npm install && pip install -e '.[dev]' && docker compose pull\n"
            "3. **Execução:** docker compose up -d && npm run dev (frontend) && python main.py (backend)\n"
            "4. **Verificação:** Acessar http://localhost:3000 — header x-nextjs-cache deve ser HIT ou STALE\n"
        ),
        instruction=(
            "Guia: comandos EXATOS. Inclua URL de verificação.\n"
            "Cláusula: marque com checkmark ou X baseado no conteúdo REAL gerado nas seções anteriores."
        ),
        min_chars=400,
        max_output_tokens=2500,
        input_budget=2500,
        require_table=True,
        context_artifacts=["development_plan"],
    ),
]
