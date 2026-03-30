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
                 input_budget: int = 600):
        self.pass_id = pass_id
        self.sections = sections
        self.template = template
        self.example = example
        self.instruction = instruction
        self.max_output_tokens = max_output_tokens
        self.require_table = require_table
        self.min_chars = min_chars
        self.input_budget = input_budget


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

# ─── NEXUS FINAL: 5 passes para PRD Final consolidado (Fase 9.1.1) ─────────
NEXUS_FINAL_PASSES = [
    SectionPass(
        pass_id="final_p1",
        sections=["## Visão do Produto", "## Problema e Solução", "## Público-Alvo",
                  "## Princípios Arquiteturais", "## Diferenciais"],
        template=(
            "## Visão do Produto\n"
            "- **Codinome:** [nome memorável do projeto]\n"
            "- **Declaração de visão:** [1 frase, máx 30 palavras, verbo infinitivo]\n\n"
            "## Problema e Solução\n"
            "| ID | Problema | Impacto | Como o Sistema Resolve |\n"
            "|---|---|---|---|\n"
            "| P-01 | [problema específico] | [impacto mensurável] | [solução técnica concreta] |\n"
            "(mínimo 4 problemas)\n\n"
            "## Público-Alvo\n"
            "| Segmento | Perfil (nome fictício + dor específica com contexto) | Prioridade |\n"
            "|---|---|---|\n"
            "| [segmento] | [Nome], [idade] — [narrativa de 1-2 frases sobre o problema real] | P0 |\n"
            "(mínimo 3 personas com narrativa)\n\n"
            "## Princípios Arquiteturais\n"
            "| Princípio | Descrição Concreta | Implicação Técnica | Regra Verificável |\n"
            "|---|---|---|---|\n"
            "| [princípio] | [descrição detalhada] | [impl. técnica] | REGRA: [teste automatizado que valida] |\n"
            "(mínimo 3 princípios com regra verificável)\n\n"
            "## Diferenciais\n"
            "| Abordagem Atual/Concorrente | Problema | Como Este Sistema Supera |\n"
            "|---|---|---|\n"
            "(mínimo 3 diferenciais)\n"
        ),
        example=(
            "- **Codinome:** OmniPrice Next\n"
            "- **Declaração de visão:** Unificar ofertas de marketplaces utilizando ISR para "
            "garantir SEO máximo e performance instantânea.\n\n"
            "| P-01 | APIs heterogêneas por marketplace (formatos, auth, paginação distintos) | "
            "Dados inconsistentes, falhas na exibição, custo alto de manutenção por integração | "
            "Pipeline ETL unificado com schema normalizado (NormalizedProduct) que abstrai "
            "diferenças entre Shopee, Magalu, Amazon e ML |\n"
            "| P-02 | Latência na atualização de preços entre coleta e exibição | "
            "Usuário encontra preço divergente no checkout, gerando frustração | "
            "Revalidação sob demanda (On-demand Revalidation) via ISR com revalidate: 60 |\n\n"
            "| Caçador de Oferta | Marina, 28 anos — Abre 6 abas para comparar preço de um fone "
            "Bluetooth entre Shopee, Amazon e ML. Gasta 40min por compra e ainda assim não tem "
            "certeza se encontrou o menor preço. | P0 |\n"
            "| Afiliado Digital | Carlos, 34 anos — Cria conteúdo de review no Instagram e precisa "
            "de links rastreáveis com páginas de carregamento rápido. Sua taxa de bounce atual "
            "em sites lentos é 65%. | P0 |\n\n"
            "| ISR First | Toda página de produto é pré-renderizada estaticamente e regenerada "
            "em background a cada 60 segundos | Uso de revalidate no getStaticProps do Next.js | "
            "REGRA: Nenhuma página pode usar force-dynamic. Teste automatizado verifica header "
            "x-nextjs-cache: HIT|STALE em 100% das rotas /produto/* |\n\n"
            "| Scraping em tempo real | Lentidão extrema (3-8s por busca) e bloqueio de IP | "
            "Cache estratégico com ISR: dados pré-renderizados servidos em <100ms; invalidação "
            "por evento de preço via webhook |\n"
        ),
        instruction=(
            "Sintetize os artefatos do pipeline para gerar as 5 seções acima.\n"
            "Para Público-Alvo: inclua nome fictício, idade e narrativa de contexto real "
            "com 1-2 frases sobre a dor — NÃO apenas rótulos genéricos.\n"
            "Para Princípios Arquiteturais: inclua coluna 'Regra Verificável' com texto "
            "'REGRA:' ou 'Teste:' descrevendo como validar automaticamente.\n"
            "Para Diferenciais: compare com concorrentes reais e explique a vantagem técnica.\n"
            "NÃO copie artefatos — sintetize e ELEVE a profundidade com dados do contexto.\n"
            "PERMITIDO prosa dentro de células de tabela para dar contexto real.\n"
            "PROIBIDO prosa fora de tabelas e bullets.\n"
            "Mínimo 4 problemas, 3 personas, 3 princípios, 3 diferenciais."
        ),
        min_chars=800,
        max_output_tokens=1800,
        input_budget=3000,
    ),
    SectionPass(
        pass_id="final_p2",
        sections=["## Requisitos Funcionais", "## Requisitos Não-Funcionais"],
        template=(
            "## Requisitos Funcionais (Consolidados)\n"
            "| ID | Requisito | Critério de Aceite | Prioridade | Complexidade | Status Pós-Review |\n"
            "|---|---|---|---|---|---|\n"
            "| RF-01 | [requisito] | [teste automatizável: ex: 'POST /api/x retorna 201'] | Must | Low | Aprovado |\n"
            "(mínimo 6 RFs com critérios de aceite VERIFICÁVEIS POR TESTE AUTOMATIZADO)\n\n"
            "## Requisitos Não-Funcionais\n"
            "| ID | Categoria | Requisito | Métrica | Target |\n"
            "|---|---|---|---|---|\n"
            "| RNF-01 | Performance | [requisito] | [métrica mensurável] | [valor numérico] |\n"
            "(mínimo 4 RNFs com target NUMÉRICO)\n"
        ),
        example=(
            "| RF-01 | Busca Unificada Multi-Loja | GET /api/search retorna resultados de "
            "Shopee, Magalu, Amazon e ML em <1s with status 200 e JSON validado via schema Zod | "
            "Must | Med | Aprovado |\n"
            "| RF-02 | Página de Produto com ISR | URL /produto/[slug] renderiza via ISR e atualiza "
            "cache a cada 60s. Header x-nextjs-cache presente com valor HIT ou STALE | "
            "Must | High | Aprovado |\n"
            "| RF-03 | Histórico de Preços | Gráfico exibe variação de preço dos últimos 90 dias "
            "por loja. GET /api/products/{slug}/history retorna data_points com min 12 entradas | "
            "Should | Med | Aprovado |\n\n"
            "| RNF-01 | Performance | Largest Contentful Paint (LCP) | p95 via Lighthouse | <2.5s |\n"
            "| RNF-02 | SEO | Indexabilidade de Páginas Dinâmicas | Google Search Console | 100% Válidos |\n"
        ),
        instruction=(
            "Consolide requisitos do PRD original com status do Review. "
            "NÃO copie artefatos — sintetize e consolide. "
            "Mínimo 6 RFs e 4 RNFs. IDs sequenciais. Inclua coluna Status Pós-Review.\n"
            "Critérios de aceite DEVEM ser testes automatizáveis — inclua endpoint, "
            "status HTTP esperado e formato de resposta.\n"
            "RNFs DEVEM ter target numérico — nunca 'bom' ou 'adequado'."
        ),
        min_chars=600,
        max_output_tokens=1800,
        input_budget=3000,
    ),
    SectionPass(
        pass_id="final_p3",
        sections=["## Arquitetura e Tech Stack", "## ADRs", "## Análise de Segurança", "## Escopo MVP"],
        template=(
            "## Arquitetura e Tech Stack (do System Design)\n"
            "- **Estilo:** [tipo de arquitetura]\n"
            "- **Stack resumida em tabela**\n"
            "| Camada | Tecnologia | Justificativa |\n"
            "|---|---|---|\n"
            "(mínimo 3 camadas)\n\n"
            "## ADRs (do System Design)\n"
            "| ID | Decisão | Alternativa Rejeitada | Consequências |\n"
            "|---|---|---|---|\n"
            "(mínimo 3 ADRs — cada um com alternativa rejeitada e motivo)\n\n"
            "## Análise de Segurança (do Security Review)\n"
            "| ID | Ameaça STRIDE | Componente | Severidade | Mitigação Concreta |\n"
            "|---|---|---|---|---|\n"
            "(mínimo 3 ameaças com mitigação ESPECÍFICA, não genérica)\n\n"
            "## Escopo MVP\n"
            "**Inclui:** [lista com RF-XX — APENAS IDs que existem na tabela de RFs acima]\n"
            "**NÃO inclui:** [lista com justificativa técnica para cada exclusão]\n"
        ),
        example=(
            "| Frontend/Edge | Next.js 14 + Vercel Edge | SSR/ISR nativo para SEO e "
            "Core Web Vitals otimizados |\n"
            "| Backend/Scraper | Python (FastAPI) + Playwright | Assincronia para I/O "
            "e bibliotecas robustas de automação |\n"
            "| Data/Cache | PostgreSQL + Redis | Consistência relacional para produtos "
            "e cache de respostas de APIs |\n\n"
            "| ADR-01 | ISR (Incremental Static Regeneration) | SSR (Server-Side Rendering) | "
            "Reduz latência e carga no servidor; dados atualizados em background. "
            "Trade-off: dados podem ter até 60s de atraso |\n\n"
            "| SEC-01 | Spoofing | API Gateway | Alta | Autenticação JWT + Rate Limiting "
            "rigoroso por IP (60 req/min). Implementação: middleware FastAPI com slowapi |\n\n"
            "**Inclui:**\n- RF-01 (Busca Unificada)\n- RF-02 (Página de Produto ISR)\n"
            "**NÃO inclui:**\n- RF-04 (Checkout Integrado) — complexidade de integração "
            "with gateways de pagamento exige 8 semanas adicionais\n"
        ),
        instruction=(
            "Sintetize arquitetura, ADRs, segurança e escopo dos artefatos. "
            "NÃO copie artefatos — sintetize e consolide. "
            "Mínimo 3 camadas, 3 ADRs, 3 ameaças. "
            "ADRs: incluir trade-off real da decisão, não apenas 'melhor opção'. "
            "Segurança: mitigação deve ser ESPECÍFICA (ex: 'Rate limiting 60 req/min via slowapi'), "
            "não genérica (ex: 'implementar segurança'). "
            "Escopo: referencie APENAS RF-IDs existentes na tabela de RFs."
        ),
        min_chars=600,
        max_output_tokens=1800,
        input_budget=3000,
    ),
    SectionPass(
        pass_id="final_p4",
        sections=["## Riscos Consolidados", "## Métricas de Sucesso",
                  "## Plano de Implementação", "## Decisões do Debate", "## Constraints Técnicos"],
        template=(
            "## Riscos Consolidados (PRD + Design + Security)\n"
            "| ID | Risco | Fonte | Probabilidade | Impacto | Mitigação | Workaround Atual |\n"
            "|---|---|---|---|---|---|---|\n"
            "(mínimo 4 riscos com mitigação E workaround)\n\n"
            "## Métricas de Sucesso\n"
            "| Métrica | Target | Prazo | Como Medir |\n"
            "|---|---|---|---|\n"
            "(mínimo 4 métricas com target NUMÉRICO e método de medição concreto)\n\n"
            "## Plano de Implementação (resumo do Development Plan)\n"
            "| Fase | Duração | Entregas | Critério de Conclusão | Dependência |\n"
            "|---|---|---|---|---|\n"
            "(mínimo 3 fases com critério de conclusão VERIFICÁVEL)\n\n"
            "## Decisões do Debate (pontos de consenso)\n"
            "| Round | Tipo | Decisão | Justificativa Técnica |\n"
            "|---|---|---|---|\n"
            "(extrair dos pontos aceitos e melhorias propostas do transcript)\n\n"
            "## Constraints Técnicos\n"
            "- Linguagem: [valor concreto com versão]\n"
            "- Framework: [valor concreto com versão]\n"
            "- Banco de dados: [valor concreto]\n"
            "- Infraestrutura: [provedores específicos]\n"
            "- Restrições de segurança: [lista concreta]\n"
        ),
        example=(
            "| R-01 | Bloqueio de IP por anti-bot | Security | Alta | Crítico | "
            "Proxy rotation com pool de 20+ IPs brasileiros + delay 2-5s entre requests | "
            "Cache stale serve dados antigos por até 1h enquanto proxy rotation recupera |\n"
            "| R-02 | Dados desatualizados (ISR stale) | Design | Média | Alto | "
            "Webhook de revalidação on-demand + cache TTL curto para itens populares | "
            "Badge 'Atualizado há X minutos' visível ao usuário |\n\n"
            "| LCP (Largest Contentful Paint) | <2.5s | Contínuo | Google Lighthouse CI "
            "em pipeline de deploy — bloqueia merge se LCP > 2.5s |\n"
            "| Precisão de Preço | >95% | Contínuo | Auditoria amostral manual: "
            "comparar 50 produtos/semana com preço real no marketplace |\n\n"
            "| Fase 1 — Infraestrutura | 2 semanas | PG, Redis, Docker, CI/CD | "
            "docker-compose up funciona e migrations rodam | Nenhuma |\n"
            "| Fase 2 — Backend API | 2 semanas | Endpoints REST, rate limiting | "
            "Todos os endpoints retornam 200 com dados seedados, cobertura >=80% | Fase 1 |\n\n"
            "| R2 | ACEITO | Alterar 'Tempo Real' para 'Near Real-Time (<5min)' | "
            "ISR não garante sincronia milissegundo; 5min é aceitável para comparação de preços |\n"
            "| R3 | MELHORIA | Implementar stale-while-revalidate no Cache-Control | "
            "Garante disponibilidade durante regeneração de página ISR |\n\n"
            "- Linguagem: TypeScript 5+ (Strict Mode)\n"
            "- Framework: Next.js 14+ (App Router)\n"
            "- Banco de dados: PostgreSQL 16 + Redis 7.2\n"
            "- Infraestrutura: Vercel (Frontend/Edge) + Railway (Backend/Workers)\n"
            "- Segurança: Rate Limiting por IP (60 req/min), CSP Headers, LGPD compliance\n"
        ),
        instruction=(
            "Consolide riscos, métricas, plano e decisões do debate. "
            "NÃO copie artefatos — sintetize e consolide.\n"
            "Riscos: inclua coluna 'Workaround Atual' com ação concreta se o risco se materializar.\n"
            "Métricas: 'Como Medir' deve descrever ferramenta E frequência (ex: 'Lighthouse CI no deploy').\n"
            "Plano: cada fase deve ter critério de conclusão VERIFICÁVEL (ex: 'cobertura >=80%').\n"
            "Decisões: extraia dos 'Pontos Aceitos' e 'Melhorias Propostas' do transcript do debate. "
            "Se o debate não gerou decisões estruturadas, inferir dos pontos de consenso.\n"
            "Constraints: valores CONCRETOS com versão — nunca 'a definir'.\n"
            "PERMITIDO prosa dentro de células de tabela para dar contexto real.\n"
            "Mínimo 4 riscos, 4 métricas, 3 fases, 3 decisões."
        ),
        min_chars=600,
        max_output_tokens=1800,
        input_budget=3000,
    ),
    SectionPass(
        pass_id="final_p5",
        sections=["## Matriz de Rastreabilidade", "## Limitações Conhecidas",
                  "## Guia de Replicação Resumido", "## Cláusula de Integridade"],
        template=(
            "## Matriz de Rastreabilidade\n"
            "| RF-ID | Componente/Módulo | Teste Associado | Status |\n"
            "|---|---|---|---|\n"
            "| RF-01 | [módulo responsável] | [tipo de teste: unit/integration/e2e] | Planejado |\n"
            "(OBRIGATÓRIO: cada RF da tabela de Requisitos Funcionais DEVE aparecer aqui)\n\n"
            "## Limitações Conhecidas\n"
            "| ID | Limitação | Severidade | Impacto | Workaround Atual | Quando Será Resolvida |\n"
            "|---|---|---|---|---|---|\n"
            "| LIM-01 | [limitação] | Alta/Média/Baixa | [impacto no usuário] | [workaround] | v2 / Nunca |\n"
            "(mínimo 3 limitações com workaround E roadmap)\n\n"
            "## Guia de Replicação Resumido\n"
            "1. **Pré-requisitos:** [linguagem, versões exatas, ferramentas obrigatórias]\n"
            "2. **Instalação:** [comandos exatos para setup]\n"
            "3. **Execução:** [comando para rodar o sistema]\n"
            "4. **Verificação:** [como confirmar que está funcionando — URL e resposta esperada]\n\n"
            "## Cláusula de Integridade\n"
            "| Item | Status |\n"
            "|---|---|\n"
            "| Todos os RF-IDs do Escopo existem na tabela de RFs | [checkmark] |\n"
            "| Todos os riscos HIGH possuem mitigação definida | [checkmark] |\n"
            "| Tech Stack é consistente entre seções | [checkmark] |\n"
            "| Métricas de sucesso possuem target quantitativo | [checkmark] |\n"
            "| Nenhuma seção contém placeholder 'A DEFINIR' | [checkmark] |\n"
            "| Security Review endereça todas as ameaças HIGH | [checkmark] |\n"
        ),
        example=(
            "| RF-01 | SearchModule (Next.js) | Unit (Jest): search retorna resultados de >=2 "
            "marketplaces. Integration (Supertest): endpoint /api/search retorna 200 | Planejado |\n"
            "| RF-02 | ProductPage (Next.js ISR) | E2E (Playwright): /produto/slug retorna header "
            "x-nextjs-cache with valor HIT ou STALE | Planejado |\n\n"
            "| LIM-01 | Bloqueio de IP por anti-bot dos marketplaces | Alta | "
            "Coleta falha temporariamente, dados ficam stale por até 1h | "
            "Proxy rotation + backoff exponencial + cache stale with badge 'dados podem estar "
            "desatualizados' | v1.1 — Pool de proxies residenciais (Bright Data) with 100+ IPs |\n"
            "| LIM-02 | ISR tem atraso de até 60s entre coleta e exibição | Média | "
            "Usuário pode ver preço desatualizado por até 1 minuto | "
            "Badge 'Atualizado há X min' + webhook on-demand reduz gap real para ~30s | "
            "v1.5 — Server-Sent Events (SSE) para push de preço em tempo real |\n\n"
            "1. **Pré-requisitos:** Node.js 18.17+, Python 3.11+, Docker 24+, npm 9.6+\n"
            "2. **Instalação:** git clone repo && npm install && cd backend && pip install -e '.[dev]'\n"
            "3. **Execução:** docker compose up -d && npm run dev\n"
            "4. **Verificação:** Acessar http://localhost:3000/produto/slug-teste e confirmar "
            "que header x-nextjs-cache existe e ofertas são exibidas\n"
        ),
        instruction=(
            "Gere rastreabilidade, limitações, guia de replicação e cláusula de integridade.\n"
            "Rastreabilidade: cada RF da tabela anterior DEVE aparecer exatamente 1 vez. "
            "Teste Associado deve descrever TIPO + FERRAMENTA + O QUE VALIDA.\n"
            "Limitações: inclua Severidade, Workaround Atual E versão de resolução. "
            "Workaround deve ser ação concreta que o sistema já faz, não plano futuro.\n"
            "Guia: comandos exatos, não 'instale as dependências'. Inclua URL de verificação.\n"
            "Cláusula: marque APENAS com checkmark ou X baseado no conteúdo REAL gerado "
            "nas seções anteriores — não assuma que está tudo ok.\n"
            "PERMITIDO prosa dentro de células de tabela para dar contexto real.\n"
            "NÃO copie artefatos — sintetize e consolide.\n"
            "Mínimo: todos os RFs na rastreabilidade, 3 limitações, 4 passos no guia."
        ),
        min_chars=500,
        max_output_tokens=1800,
        input_budget=3000,
    ),
]
