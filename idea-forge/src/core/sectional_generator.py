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

# FASE 9.5: Importar exemplares do padrão ouro
from src.core.exemplars.p01_visao_problemas import EXEMPLAR_P01
from src.core.exemplars.p02_publico_alvo import EXEMPLAR_P02
from src.core.exemplars.p03_principios_diferenciais import EXEMPLAR_P03
from src.core.exemplars.p04_requisitos_funcionais import EXEMPLAR_P04
from src.core.exemplars.p05_rnfs import EXEMPLAR_P05
from src.core.exemplars.p06_arquitetura_adrs import EXEMPLAR_P06
from src.core.exemplars.p07_seguranca import EXEMPLAR_P07
from src.core.exemplars.p08_escopo_mvp import EXEMPLAR_P08
from src.core.exemplars.p09_riscos_metricas import EXEMPLAR_P09
from src.core.exemplars.p10_plano_debate import EXEMPLAR_P10
from src.core.exemplars.p11_constraints_rastreabilidade import EXEMPLAR_P11
from src.core.exemplars.p12_guia_clausula import EXEMPLAR_P12


MAX_RETRIES_PER_PASS = 3


class SectionPass:
    """Definição de um passo de geração."""
    def __init__(self, pass_id: str, sections: List[str],
                 template: str, example: str,
                 instruction: str, max_output_tokens: int = 800,
                 require_table: bool = True,
                 min_chars: int = 80,
                 min_words: int = 0,
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
        self.min_words = min_words
        self.input_budget = input_budget
        self.context_artifacts = context_artifacts or []


class SectionalGenerator:
    """Gera artefatos densos quebrando em múltiplos passes sequenciais."""

    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self.validator = OutputValidator()
        self._validate_passes_config()

    def _validate_passes_config(self):
        """FASE 9.5.3: Impede seções duplicadas e cabeçalhos redundantes."""
        all_maps = {
            "PRD_PASSES": PRD_PASSES,
            "DESIGN_PASSES": DESIGN_PASSES,
            "PLAN_PASSES": PLAN_PASSES,
            "REVIEW_PASSES": REVIEW_PASSES,
            "SECURITY_PASSES": SECURITY_PASSES,
            "NEXUS_FINAL_PASSES": NEXUS_FINAL_PASSES
        }
        all_errors = []
        
        for map_name, pass_list in all_maps.items():
            seen_sections = set()
            for p in pass_list:
                for section in p.sections:
                    # Normalizar para comparação
                    normalized = section.strip().upper()
                    if normalized in seen_sections:
                        all_errors.append(f"{map_name}:{p.pass_id} -> '{section}' (DUPLICADA)")
                    seen_sections.add(normalized)
                    
                    # FASE 9.5.3: Também checar se o título da seção está no template indevidamente
                    if section not in p.template and "##" in section:
                         # Isso pode ser um aviso ao invés de erro, mas ajuda a manter a consistência
                         pass 

        if all_errors:
            raise ValueError(
                f"Configuração de passes inválida: {all_errors}. "
                f"Remova as seções duplicadas para garantir 'is_clean: True'."
            )

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
        
        # FASE 9.5.3b: Safety net para placeholders residuais
        final_output = self._sanitize_placeholders(final_output)

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

        # FASE 9.5.3b: Safety net para placeholders residuais
        final_output = self._sanitize_placeholders(final_output)

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
                # FASE 9.5.1: Skip quality check para passes skeleton
                is_skeleton_pass = section_pass.pass_id.endswith("a") and any(
                    section_pass.pass_id.startswith(prefix) 
                    for prefix in ["final_p02", "final_p03", "final_p06", "final_p09"]
                )
                
                if not is_skeleton_pass:
                    # FASE 9.5: Verificação de qualidade por seção
                    quality_feedback = self._check_section_quality(
                        section_pass.sections, result
                    )
                    if quality_feedback and attempt <= MAX_RETRIES_PER_PASS:
                        self._emit_warn(
                            f"  Pass {pass_number} estrutura OK mas qualidade insuficiente. "
                            f"Retentando com feedback..."
                        )
                        last_fail_reasons = [f"QUALITY: {quality_feedback}"]
                        continue  # Vai para próxima iteração do loop de retry
                
                if attempt > 1:
                    self._emit_ok(f"  Pass {pass_number} corrigido na tentativa {attempt}")
                
                # FASE 9.5.3c: Filtro de vazamento de seções adjacentes
                filtered_result = self._filter_section_output(result, section_pass.sections)
                return filtered_result

            # Falhou — preparar retry
            last_fail_reasons = validation.get("fail_reasons", ["UNKNOWN"])

            if attempt <= MAX_RETRIES_PER_PASS:
                self._emit_warn(
                    f"  Pass {pass_number} tentativa {attempt} falhou: "
                    f"{last_fail_reasons}. Retentando..."
                )

        # Todos os retries falharam
        return None

    def _check_section_quality(self, sections: List[str], content: str) -> str:
        """FASE 9.5: Verifica qualidade via SectionQualityChecker."""
        from src.core.section_quality_checker import SectionQualityChecker
        checker = SectionQualityChecker()
        all_feedback = []
        for heading in sections:
            fb = checker.check_section_by_type(heading, content)
            all_feedback.extend(fb)
        if all_feedback:
            return "; ".join(all_feedback[:3])  # Limitar a 3 feedbacks para não estourar prompt
        return ""

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
            "1. Comece IMEDIATAMENTE with ## heading. NENHUM texto antes.\n"
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

        # FASE 9.5: Injetar exemplar gold-standard se disponível, senão usar example do pass
        exemplar = self._get_exemplar(section_pass.pass_id)
        if exemplar:
            prompt += f"{exemplar}\n\n"
        elif section_pass.example:
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

        # FASE 9.5.3c: Regra de Fronteira multi-seção
        if len(section_pass.sections) == 1:
            prompt += (
                f"\nREGRA CRÍTICA: Gere obrigatoriamente a seção '{section_pass.sections[0]}'.\n"
                "NÃO inclua nenhuma outra seção ## adicional.\n"
            )
        else:
            sections_list = ", ".join(f"'{s}'" for s in section_pass.sections)
            prompt += (
                f"\nREGRA CRÍTICA: Gere obrigatoriamente estas seções, nesta ordem: {sections_list}.\n"
                "Mantenha cada seção bem detalhada. NÃO inclua seções ## que não foram listadas aqui.\n"
                "Pare IMEDIATAMENTE após concluir a última seção da lista.\n"
            )

        return prompt

    def _get_exemplar(self, pass_id: str) -> str:
        """FASE 9.5: Retorna exemplar gold-standard para o pass, ou string vazia."""
        _EXEMPLAR_MAP = {
            "final_p01": EXEMPLAR_P01,
            "final_p02a": "",          
            "final_p02b": EXEMPLAR_P02, 
            "final_p03a": "",          
            "final_p03b": EXEMPLAR_P03, 
            "final_p04": EXEMPLAR_P04,
            "final_p05a": EXEMPLAR_P05, 
            "final_p05b": "",          
            "final_p06a": "",          # FASE 9.5.1: Skeleton
            "final_p06b": EXEMPLAR_P06, # FASE 9.5.1: Flesh
            "final_p06c": "",          # FASE 9.5.1: ADRs
            "final_p07": EXEMPLAR_P07,
            "final_p08": EXEMPLAR_P08,
            "final_p09a": EXEMPLAR_P09, 
            "final_p09b": "",          
            "final_p10": EXEMPLAR_P10,
            "final_p11a": EXEMPLAR_P11, 
            "final_p11b": "",          
            "final_p12": EXEMPLAR_P12,
        }
        return _EXEMPLAR_MAP.get(pass_id, "")

    def _summarize_previous(self, text: str, max_tokens: int = 500) -> str:
        """Extrai apenas headings e primeiras lines."""
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

    def _filter_section_output(self, output: str, expected_sections: list) -> str:
        """
        Fase 9.5.3c: Remove headers ## que não pertencem ao pass atual.
        Aceita lista de seções esperadas para suportar passes multi-seção.
        """
        if not output:
            return ""

        # Normalizar todas as seções esperadas
        normalized_expected = [self._normalize_header(s) for s in expected_sections]

        lines = output.split("\n")
        filtered = []
        found_any_expected = False

        for line in lines:
            stripped = line.strip()
            # Detectar headers ## (mas não ### ou #)
            if stripped.startswith("## ") and not stripped.startswith("### "):
                header_text = self._normalize_header(stripped)

                # Verificar se é um header esperado deste pass
                is_expected = any(
                    exp in header_text or header_text in exp
                    for exp in normalized_expected
                )

                if is_expected:
                    found_any_expected = True
                    filtered.append(line)
                elif found_any_expected:
                    # Header invasor de OUTRO pass — parar aqui
                    break
                # Se ainda não encontrou nenhum esperado, ignora (preâmbulo)
            else:
                if found_any_expected:
                    filtered.append(line)

        return "\n".join(filtered).strip()

    def _normalize_header(self, text: str) -> str:
        """Helper para comparação robusta de headers (remove #, espaços, e acentos básicos)."""
        import unicodedata
        t = text.strip().lstrip("# ").strip().lower()
        # Normalização unicode para remover acentos
        t = "".join(c for c in unicodedata.normalize('NFD', t)
                    if unicodedata.category(c) != 'Mn')
        return t

    def _sanitize_placeholders(self, prd_content: str) -> str:
        """
        Fase 9.5.3b: Substitui placeholders residuais por valores neutros (N/A).
        Safety net programático.
        """
        if not prd_content:
            return ""
            
        replacements = {
            "A DEFINIR": "N/A",
            "a definir": "N/A",
            "A definir": "N/A",
            "TODO": "N/A",
            "TBD": "N/A",
            "A SER ESPECIFICADO": "N/A",
            "PENDENTE": "N/A",
            "EM BREVE": "N/A",
        }
        result = prd_content
        for placeholder, replacement in replacements.items():
            result = result.replace(placeholder, replacement)
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
        elif artifact_type == "prd_final":          
            return NEXUS_FINAL_PASSES
        return []


# ═══════════════════════════════════════════════════════════
# PASSES POR TIPO DE ARTEFATO
# ═══════════════════════════════════════════════════════════

# PRD_PASSES
PRD_PASSES = [
    SectionPass("prd_p1", ["## Objetivo", "## Problema"], "## Objetivo\n- ...", "", "Gere Objetivo/Problema com profundidade.", 250, require_table=False),
    SectionPass("prd_p2", ["## Público-Alvo", "## Princípios Arquiteturais", "## Diferenciais"], "## Público-Alvo\n|...|", "", "Gere Público/Princípios/Diferenciais com profundidade.", 350, require_table=False),
    SectionPass("prd_p3", ["## Requisitos Funcionais", "## Requisitos Não-Funcionais"], "## Requisitos Funcionais\n|...|", "", "Gere RF/RNF com profundidade.", 500, require_table=False),
    SectionPass("prd_p4", ["## Escopo MVP", "## Métricas de Sucesso"], "## Escopo MVP\n**Inclui:** ...", "", "Gere Escopo/Métricas com profundidade.", 300, require_table=False),
    SectionPass("prd_p5", ["## Dependências e Riscos", "## Constraints Técnicos"], "## Dependências\n|...|", "", "Gere Riscos/Constraints com profundidade.", 300, require_table=False),
]

# REVIEW_PASSES
REVIEW_PASSES = [
    SectionPass("review_p1", ["## Score de Qualidade", "## Issues Identificadas"], "## Score\n...", "", "Gere Score/Issues.", 300, require_table=False),
    SectionPass("review_p2", ["## Verificação de Requisitos", "## Verificação de Princípios Arquiteturais", "## Sumário", "## Recomendação"], "## Verificação\n...", "", "Verifique requisitos/princípios.", 400, require_table=False),
]

# SECURITY_PASSES
SECURITY_PASSES = [
    SectionPass("security_p1", ["## Superfície de Ataque", "## Ameaças Identificadas"], "## Superfície\n...", "", "Identifique superfície/ameaças.", 300, require_table=False),
    SectionPass("security_p2", ["## Requisitos de Segurança Derivados", "## Dados Sensíveis", "## Plano de Autenticação/Autorização"], "## Requisitos\n...", "", "Gere requisitos/dados/auth.", 350, require_table=False),
]

# DESIGN_PASSES
DESIGN_PASSES = [
    SectionPass("design_p1", ["## Arquitetura Geral", "## Tech Stack"], "## Arquitetura\n...", "", "Gere Arquitetura/Tech Stack com profundidade.", 350, require_table=False),
    SectionPass("design_p2", ["## Módulos", "## Modelo de Dados"], "## Módulos\n...", "", "Gere Módulos/Dados com profundidade.", 450, require_table=False),
    SectionPass("design_p3", ["## Fluxo de Dados", "## ADRs", "## Riscos Técnicos", "## Requisitos de Infraestrutura"], "## Fluxo\n...", "", "Gere Fluxo/ADRs/Riscos/Infra.", 600, require_table=False),
]

# PLAN_PASSES
PLAN_PASSES = [
    SectionPass("plan_p1", ["## Arquitetura Sugerida", "## Módulos Core"], "## Arquitetura\n...", "", "Gere Arquitetura/Módulos.", 350, require_table=False),
    SectionPass("plan_p2", ["## Fases de Implementação", "## Dependências Técnicas"], "## Fases\n...", "", "Gere Fases/Dependências. REGRAS: NÃO use 'A DEFINIR'. Use 'N/A' se não aplicável.", 350, require_table=False),
]

# NEXUS FINAL: 20 seções expandidas (Fase 9.5.3b - Surgical Wave 1c)
NEXUS_FINAL_PASSES = [
    SectionPass(
        pass_id="final_p01",
        sections=["## Visão do Produto", "## Problema e Solução"],
        template="## Visão do Produto\n- **Codinome:** ...\n\n## Problema e Solução\n| ID | Problema | Impacto | Como Resolve |",
        example="",
        instruction="Sintetize visão e problemas (mín 6). Visão: 50-100 palavras. Problemas: 200-400 palavras.",
        min_chars=600,
        min_words=250,
        max_output_tokens=2500,
        input_budget=1200,
        require_table=False,
        context_artifacts=["prd"],
    ),
    SectionPass(
        pass_id="final_p02b",
        sections=["## Público-Alvo"],
        template="## Público-Alvo\n| Segmento | Perfil | Prioridade |",
        example="",
        instruction="Expanda as personas do outline em tabela rica. MÍNIMO 300 palavras.",
        min_chars=1200,
        max_output_tokens=1500,
        input_budget=1200,
        require_table=False,
        context_artifacts=["prd"],
    ),
    SectionPass(
        pass_id="final_p03b",
        sections=["## Princípios Arquiteturais", "## Diferenciais"],
        template="## Princípios Arquiteturais\n| Princípio | Descrição | Implicação | Regra |\n\n## Diferenciais\n| Atual | Problema | Superação |",
        example="",
        instruction="Expanda princípios e diferenciais em tabelas. Princípios: 300-500 palavras. Diferenciais: 150-250 palavras.",
        min_chars=2000,
        min_words=450,
        max_output_tokens=2500,
        input_budget=1200,
        require_table=False,
        context_artifacts=["prd", "system_design"],
    ),
    SectionPass(
        pass_id="final_p04",
        sections=["## Requisitos Funcionais"],
        template="## Requisitos Funcionais (Consolidados)\n| ID | Requisito | Critério | Prioridade | Complexidade | Status |",
        example="",
        instruction="Consolide RFs (mín 10). Critérios técnicos. MÍNIMO 500 palavras.",
        min_chars=2500,
        min_words=500,
        max_output_tokens=2500,
        input_budget=1200,
        require_table=False,
        context_artifacts=["prd", "prd_review"],
    ),
    SectionPass(
        pass_id="final_p05b",
        sections=["## Requisitos Não-Funcionais"],
        template="## Requisitos Não-Funcionais\n| ID | Categoria | Requisito | Métrica | Target |",
        example="",
        instruction="Expanda os RNFs em tabela. REGRAS: NÃO use 'A DEFINIR'. MÍNIMO 600 palavras.",
        min_chars=3000,
        min_words=600,
        max_output_tokens=2000,
        input_budget=1200,
        require_table=False,
        context_artifacts=["prd"],
    ),
    SectionPass(
        pass_id="final_p06b",
        sections=["## Arquitetura e Tech Stack"],
        template="## Arquitetura e Tech Stack\n- **Estilo:** ...\n```mermaid\ngraph TB\n...```",
        example="",
        instruction="Expanda a arquitetura com Mermaid e detalhamento técnico. MÍNIMO 400 palavras.",
        min_chars=2000,
        min_words=400,
        max_output_tokens=2500,
        input_budget=1200,
        require_table=False,
        context_artifacts=["system_design"],
    ),
    SectionPass(
        pass_id="final_p06c",
        sections=["## ADRs"],
        template="## ADRs (Decisões Arquiteturais)\n| Campo | Valor |",
        example="",
        instruction="Gere 5+ ADRs no formato ficha. MÍNIMO 500 palavras.",
        min_chars=2500,
        min_words=500,
        max_output_tokens=2500,
        input_budget=1200,
        require_table=False,
        context_artifacts=["system_design"],
    ),
    SectionPass(
        pass_id="final_p07",
        sections=["## Análise de Segurança"],
        template="## Análise de Segurança\n| ID | Ameaça STRIDE | Componente | Severidade | Mitigação |",
        example="",
        instruction="Sintetize 6+ ameaças STRIDE e dados sensíveis. MÍNIMO 500 palavras.",
        min_chars=2000,
        min_words=500,
        max_output_tokens=2000,
        input_budget=1200,
        require_table=False,
        context_artifacts=["security_review"],
    ),
    SectionPass(
        pass_id="final_p08",
        sections=["## Escopo MVP"],
        template="## Escopo MVP\n**Inclui:** ...",
        example="",
        instruction="Referencie IDs existentes. Justifique exclusões. MÍNIMO 300 palavras.",
        min_chars=1200,
        min_words=300,
        max_output_tokens=2500,
        input_budget=1200,
        require_table=False,
        context_artifacts=["prd"],
    ),
    SectionPass(
        pass_id="final_p09a",
        sections=["## Riscos Consolidados"],
        template="## Riscos Consolidados\n| ID | Risco | Fonte | Probabilidade | Impacto | Mitigação | Workaround |",
        example="",
        instruction="Consolide 8+ riscos with workaround. MÍNIMO 400 palavras.",
        min_chars=1800,
        min_words=400,
        max_output_tokens=2000,
        input_budget=1200,
        require_table=False,
        context_artifacts=["prd", "system_design", "security_review"],
    ),
    SectionPass(
        pass_id="final_p09b",
        sections=["## Métricas de Sucesso"],
        template="## Métricas de Sucesso\n| Métrica | Target | Como Medir |",
        example="",
        instruction="Gere 8+ métricas quantitativas. MÍNIMO 400 palavras.",
        min_chars=1800,
        min_words=400,
        max_output_tokens=2000,
        input_budget=1200,
        require_table=False,
        context_artifacts=["prd"],
    ),
    SectionPass(
        pass_id="final_p10",
        sections=["## Plano de Implementação", "## Decisões do Debate"],
        template="## Plano de Implementação\n| Fase | Duração | Entregas | Critério | Dependência |",
        example="",
        instruction="Gere plano e decisões. Plano: 300-500 palavras. Decisões: 200-400 palavras.",
        min_chars=2500,
        min_words=500,
        max_output_tokens=2500,
        input_budget=1200,
        require_table=False,
        context_artifacts=["development_plan", "debate_transcript"],
    ),
    SectionPass(
        pass_id="final_p11a",
        sections=["## Constraints Técnicos", "## Matriz de Rastreabilidade"],
        template="## Constraints Técnicos\n- ...",
        example="",
        instruction="Gere constraints e rastreabilidade total (mesmos RF-IDs). Constraints: 100-200. Matriz: 300-500.",
        min_chars=1800,
        min_words=400,
        max_output_tokens=2500,
        input_budget=1200,
        require_table=False,
        context_artifacts=["prd", "system_design"],
    ),
    SectionPass(
        pass_id="final_p11b",
        sections=["## Limitações Conhecidas"],
        template="## Limitações Conhecidas\n| ID | Limitação | Severidade | Impacto | Workaround | Resolução |",
        example="",
        instruction="Gere 6+ limitações with workaround. REGRAS: NÃO use 'A DEFINIR'. MÍNIMO 400 palavras.",
        min_chars=1800,
        min_words=400,
        max_output_tokens=2500,
        input_budget=1200,
        require_table=False,
        context_artifacts=["prd", "system_design"],
    ),
    SectionPass(
        pass_id="final_p12",
        sections=["## Guia de Replicação Resumido", "## Cláusula de Integridade"],
        template="## Guia de Replicação Resumido\n1. ...",
        example="",
        instruction="Guia (6+ passos) e Cláusula (8+ itens). Guia: 200-300. Cláusula: N/A (estática).",
        min_chars=1000,
        min_words=250,
        max_output_tokens=2500,
        input_budget=1200,
        require_table=False,
        context_artifacts=["development_plan"],
    ),
]

