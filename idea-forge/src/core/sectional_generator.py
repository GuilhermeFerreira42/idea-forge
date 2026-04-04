"""
sectional_generator.py — Gerador de artefatos por seções.

FASE 5.1/9.6:
- Retry por pass com prompt corretivo específico
- Validação hard por pass via OutputValidator.validate_pass()
- FASE 9.6: Reduzido para 1 retry para dar vazão ao RetryOrchestrator
"""
import sys
import re
from typing import List, Dict, Optional
from src.models.model_provider import ModelProvider
from src.core.stream_handler import ANSIStyle
from src.core.output_validator import OutputValidator

# FASE 9.7: Perfis de prompt e decomposição atômica
from src.core.prompt_profiles import PromptProfile, PROFILE_LARGE, PromptProfiles
from src.core.atomic_task_decomposer import AtomicTaskDecomposer

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

# FASE 9.6: Reduzido para 1 para evitar loops infinitos quando a LLM está instável
MAX_RETRIES_PER_PASS = 1


class SectionPass:
    """Definição de um passo de geração."""
    def __init__(self, pass_id: str, sections: List[str],
                 template: str, example: str,
                 instruction: str, max_output_tokens: int = 800,
                 require_table: bool = True,
                 min_chars: int = 200,
                 min_words: int = 0,
                 input_budget: int = 1000,
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
        self._active_profile: Optional[PromptProfile] = None  # FASE 9.7
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
                    normalized = section.strip().upper()
                    if normalized in seen_sections:
                        all_errors.append(f"{map_name}:{p.pass_id} -> '{section}' (DUPLICADA)")
                    seen_sections.add(normalized)
        
        if all_errors:
            raise ValueError(f"Configuração de passes inválida: {all_errors}.")

    def generate_sectional(self, artifact_type: str,
                           user_input: str,
                           context: str = "",
                           passes: List[SectionPass] = None,
                           profile: Optional[PromptProfile] = None) -> Optional[str]:
        # FASE 9.7: Default para PROFILE_LARGE (preserva comportamento pré-fase)
        if profile is None:
            profile = PROFILE_LARGE
        self._active_profile = profile  # FASE 9.7: Armazenar perfil ativo

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
                failed_passes += 1
                self._emit_warn(f"Pass {i+1} FALHOU. Usando marcador de falha.")
                # Marcador consistente para o RetryOrchestrator
                failed_marker = "\n".join(
                    f"{s}\n[GERAÇÃO FALHOU — seção não produzida]"
                    for s in section_pass.sections
                )
                pass_results.append(failed_marker)
                accumulated_output += failed_marker + "\n\n"
            else:
                pass_results.append(result)
                accumulated_output += result + "\n\n"

        if failed_passes > len(passes) / 2:
            self._emit_warn(f"FALHA ESTRUTURAL: {failed_passes}/{len(passes)} passes falharam.")
            return None

        final_output = "\n\n".join(pass_results)
        final_output = self._sanitize_placeholders(final_output)
        return final_output

    def generate_sectional_with_inputs(self, artifact_type: str,
                                        pass_inputs: List[str],
                                        passes: List[SectionPass],
                                        profile: Optional[PromptProfile] = None) -> Optional[str]:
        # FASE 9.7: Default para PROFILE_LARGE
        if profile is None:
            profile = PROFILE_LARGE
        self._active_profile = profile  # FASE 9.7: Armazenar perfil ativo

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
                self._emit_warn(f"Pass {i+1} FALHOU.")
                failed_marker = "\n".join(
                    f"{s}\n[GERAÇÃO FALHOU — seção não produzida]"
                    for s in section_pass.sections
                )
                pass_results.append(failed_marker)
                accumulated_output += failed_marker + "\n\n"
            else:
                pass_results.append(result)
                accumulated_output += result + "\n\n"

        if failed_passes > len(passes) / 2:
            self._emit_warn(f"FALHA ESTRUTURAL: {failed_passes}/{len(passes)} passes falharam.")
            return None

        final_output = "\n\n".join(pass_results)
        final_output = self._sanitize_placeholders(final_output)
        return final_output

    def _execute_pass_with_retry(self, section_pass: SectionPass,
                                 user_input: str, context: str,
                                 previous_output: str,
                                 pass_number: int,
                                 total_passes: int) -> Optional[str]:
        # FASE 9.7: Usar perfil ativo (default PROFILE_LARGE por compatibilidade)
        profile = self._active_profile if self._active_profile is not None else PROFILE_LARGE

        # FASE 9.7: Verificar se decomposição atômica é necessária
        if self._should_use_atomic(section_pass, profile):
            heading = section_pass.sections[0] if section_pass.sections else ""
            self._emit(f"[ATOMIC] Ativando decomposição atômica para '{heading}'")

            atomic = AtomicTaskDecomposer(
                provider=self.provider,
                profile=profile,
            )
            columns = AtomicTaskDecomposer.get_columns_for_section(heading)

            if columns is not None:
                rows = atomic.decompose_table_pass(
                    section_heading=heading,
                    columns=columns,
                    context=user_input[:profile.max_context_chars],
                    target_row_count=8,
                    system_directive=(
                        "Você é um gerador de documentação técnica. "
                        "Responda em Português. "
                        "Gere APENAS uma linha de tabela Markdown. "
                        "Comece com | e termine com |."
                    ),
                )
                atomic_result = atomic.assemble_table(heading=heading, columns=columns, rows=rows)
            elif AtomicTaskDecomposer.is_bullet_section(heading):
                bullet_labels = [f"Item {i+1}" for i in range(5)]
                bullets = atomic.decompose_paragraph_pass(
                    section_heading=heading,
                    bullet_labels=bullet_labels,
                    context=user_input[:profile.max_context_chars],
                    system_directive=(
                        "Responda em Português. Gere APENAS um bullet markdown. "
                        "Comece com -."
                    ),
                )
                atomic_result = atomic.assemble_bullets(heading=heading, bullets=bullets)
            else:
                atomic_result = None  # Seção não mapeada — cai no fluxo normal

            if atomic_result and len(atomic_result) > 50:
                validation = self.validator.validate_pass(
                    content=atomic_result,
                    expected_sections=section_pass.sections,
                    require_table=section_pass.require_table,
                    min_chars=section_pass.min_chars // 2,  # Limiar reduzido para SMALL
                )
                if validation["valid"]:
                    return self._filter_section_output(atomic_result, section_pass.sections)
            # Falha na validação atômica → retornar None (RetryOrchestrator assume)
            # Apenas se não havia seção mapeada, cai no fluxo normal.
            if atomic_result is not None:
                return None

        # Fluxo normal (não atômico)
        last_fail_reasons = []

        # FASE 9.7: max_tokens dinâmico por perfil
        effective_max_tokens = (
            profile.max_output_tokens
            if profile.model_range != "LARGE"
            else section_pass.max_output_tokens
        )

        for attempt in range(1, MAX_RETRIES_PER_PASS + 2):
            prompt = self._build_pass_prompt(
                section_pass=section_pass,
                user_input=user_input,
                context=context,
                previous_output=previous_output,
                pass_number=pass_number,
                total_passes=total_passes,
            )

            if attempt > 1 and last_fail_reasons:
                prompt += self._build_retry_instruction(section_pass, last_fail_reasons, attempt)

            result = self.provider.generate(
                prompt=prompt,
                role=self._get_role(section_pass.pass_id),
                max_tokens=effective_max_tokens
            )
            result = self._clean_pass_output(result)

            validation = self.validator.validate_pass(
                content=result,
                expected_sections=section_pass.sections,
                require_table=section_pass.require_table,
                min_chars=section_pass.min_chars,
            )

            if validation["valid"]:
                return self._filter_section_output(result, section_pass.sections)

            last_fail_reasons = validation.get("fail_reasons", ["UNKNOWN"])
            if attempt <= MAX_RETRIES_PER_PASS:
                self._emit_warn(f"  Pass {pass_number} tentativa {attempt} falhou: {last_fail_reasons}.")

        return None

    def _should_use_atomic(
        self,
        section_pass: SectionPass,
        profile: PromptProfile
    ) -> bool:
        """
        Determina se a decomposição atômica deve ser usada para este pass.

        Retorna True se e somente se:
        - profile.use_atomic_decomposition == True
        - section_pass.require_table == True

        Args:
            section_pass: Definição do pass atual
            profile: Perfil de prompt ativo

        Returns:
            bool: True se decomposição atômica deve ser usada
        """
        return (
            profile.use_atomic_decomposition is True
            and section_pass.require_table is True
        )

    def _get_role(self, pass_id: str) -> str:
        if pass_id.startswith("prd") or pass_id.startswith("final"): return "product_manager"
        if pass_id.startswith("design"): return "architect"
        if pass_id.startswith("review"): return "critic"
        if pass_id.startswith("security"): return "security_reviewer"
        if pass_id.startswith("plan"): return "planner"
        return "user"

    def _build_retry_instruction(self, section_pass: SectionPass,
                                 fail_reasons: List[str],
                                 attempt: int) -> str:
        instruction = f"\n\n⚠️ ATENÇÃO (tentativa {attempt}): Corrija: {fail_reasons}. Inicie direto com ##."
        return instruction

    def _build_pass_prompt(self, section_pass: SectionPass,
                           user_input: str, context: str,
                           previous_output: str,
                           pass_number: int, total_passes: int) -> str:
        # FASE 9.7: Usar perfil ativo para calibrar prompt por capacidade do modelo
        profile = self._active_profile if self._active_profile is not None else PROFILE_LARGE

        if section_pass.pass_id.startswith("final"):
            from src.core.prompt_templates import CONSOLIDATOR_DIRECTIVE
            if profile.system_prompt_mode == "FULL_SOP":
                system = CONSOLIDATOR_DIRECTIVE
            elif profile.system_prompt_mode == "HYBRID":
                # HYBRID: versão resumida do SOP (primeiras 300 chars)
                system = CONSOLIDATOR_DIRECTIVE[:300] + "\nResponda em Português. Use tabelas/bullets."
            else:  # FEW_SHOT
                # FEW_SHOT: instrução mínima para modelos 1B
                system = "Responda em Português. Use tabelas Markdown. Comece com ##."
        else:
            system = "Responda em Português. Formato: Markdown com tabelas/bullets. Comece com ##."

        if self.direct_mode:
            system += "\nResponda sem blocos <think>."

        prompt = f"System: {system}\n\n"
        prompt += f"GERE EXATAMENTE: {', '.join(section_pass.sections)}\n\n"

        # FASE 9.7: Exemplar truncado ao perfil
        exemplar = self._get_exemplar(section_pass.pass_id)
        if exemplar:
            exemplar_truncated = exemplar[:profile.max_exemplar_chars]
            prompt += f"EXEMPLO:\n{exemplar_truncated}\n\n"

        # FASE 9.7: Contexto com input_budget do perfil
        effective_budget = profile.input_budget_override
        prompt += f"PROJETO:\n{user_input[:effective_budget]}\n\n"

        if previous_output:
            prompt += f"JÁ GERADO:\n{previous_output[-1000:]}\n\n"

        prompt += f"INSTRUÇÃO: {section_pass.instruction}\n"
        return prompt

    def _get_exemplar(self, pass_id: str) -> str:
        _MAP = {
            "final_p01": EXEMPLAR_P01, "final_p02b": EXEMPLAR_P02,
            "final_p03b": EXEMPLAR_P03, "final_p04": EXEMPLAR_P04,
            "final_p05a": EXEMPLAR_P05, "final_p06b": EXEMPLAR_P06,
            "final_p07": EXEMPLAR_P07, "final_p08": EXEMPLAR_P08,
            "final_p09a": EXEMPLAR_P09, "final_p10": EXEMPLAR_P10,
            "final_p11a": EXEMPLAR_P11, "final_p12": EXEMPLAR_P12,
        }
        return _MAP.get(pass_id, "")

    def _clean_pass_output(self, text: str) -> str:
        if not text: return ""
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        lines = text.split('\n')
        for i, line in enumerate(lines[:5]):
            if line.strip().startswith('##'): return '\n'.join(lines[i:]).strip()
        return text.strip()

    def _filter_section_output(self, output: str, expected_sections: List[str]) -> str:
        """
        FASE 9.5.3c: Filtra o output para conter apenas as seções esperadas.
        Remove cabeçalhos (##) que não pertencem a este pass para evitar vazamentos.
        """
        if not output:
            return ""
            
        lines = output.split('\n')
        filtered_lines = []
        capture = False
        
        # Normalizar seções esperadas para comparação
        expected_norm = [s.strip().lower() for s in expected_sections]
        
        for line in lines:
            stripped = line.strip().lower()
            if stripped.startswith('##'):
                # É um cabeçalho. Devemos capturar?
                # Verifica se o cabeçalho (ou parte dele) está nas seções esperadas
                is_expected = any(ext in stripped for ext in expected_norm)
                if is_expected:
                    capture = True
                    filtered_lines.append(line)
                else:
                    # Cabeçalho invasor — para de capturar
                    capture = False
            elif capture:
                # Conteúdo de uma seção que estamos capturando
                filtered_lines.append(line)
                
        # Se o filtro removeu tudo (ex: o modelo não usou os headers esperados),
        # retorna o original para não perder informação, deixando o validador agir.
        result = '\n'.join(filtered_lines).strip()
        if not result and output:
            return output.strip()
            
        return result

    def _sanitize_placeholders(self, prd_content: str) -> str:
        if not prd_content: return ""
        for p in ["A DEFINIR", "TODO", "TBD", "PENDENTE"]: prd_content = prd_content.replace(p, "N/A")
        return prd_content

    def _emit(self, msg: str): sys.stdout.write(f"{ANSIStyle.CYAN}  {msg}{ANSIStyle.RESET}\n"); sys.stdout.flush()
    def _emit_ok(self, msg: str): sys.stdout.write(f"{ANSIStyle.GREEN}  ✅ {msg}{ANSIStyle.RESET}\n"); sys.stdout.flush()
    def _emit_warn(self, msg: str): sys.stdout.write(f"{ANSIStyle.YELLOW}  ⚠ {msg}{ANSIStyle.RESET}\n"); sys.stdout.flush()

    def _get_default_passes(self, artifact_type: str) -> List[SectionPass]:
        map_ = {"prd": PRD_PASSES, "system_design": DESIGN_PASSES, "plan": PLAN_PASSES, 
                "review": REVIEW_PASSES, "security_review": SECURITY_PASSES, "prd_final": NEXUS_FINAL_PASSES}
        return map_.get(artifact_type, [])

# PASSES (Simplificados para teste de certificação)
PRD_PASSES = [
    SectionPass("prd_p1", ["## Objetivo", "## Problema"], "", "", "Gere Objetivo/Problema.", 800),
    SectionPass("prd_p2", ["## Público-Alvo", "## Princípios Arquiteturais", "## Diferenciais"], "", "", "Gere Público/Princípios/Diferenciais.", 800),
    SectionPass("prd_p3", ["## Requisitos Funcionais", "## Requisitos Não-Funcionais"], "", "", "Gere RF/RNF.", 800),
    SectionPass("prd_p4", ["## Escopo MVP", "## Métricas de Sucesso"], "", "", "Gere Escopo/Métricas.", 800),
    SectionPass("prd_p5", ["## Dependências e Riscos", "## Constraints Técnicos"], "", "", "Gere Riscos/Constraints.", 800),
]

REVIEW_PASSES = [SectionPass("review_p1", ["## Score de Qualidade", "## Issues Identificadas"], "", "", "Gere Score/Issues.", 800)]
SECURITY_PASSES = [SectionPass("security_p1", ["## Superfície de Ataque", "## Ameaças Identificadas"], "", "", "Identifique superfície/ameaças.", 800)]
DESIGN_PASSES = [SectionPass("design_p1", ["## Arquitetura Geral", "## Tech Stack"], "", "", "Gere Arquitetura/Tech Stack.", 800)]
PLAN_PASSES = [SectionPass("plan_p1", ["## Arquitetura Sugerida", "## Módulos Core"], "", "", "Gere Arquitetura/Módulos.", 800)]

NEXUS_FINAL_PASSES = [
    SectionPass("final_p01", ["## Visão do Produto", "## Problema e Solução"], "", "", "Sintetize visão/problema.", 1000, context_artifacts=["prd"]),
    SectionPass("final_p02b", ["## Público-Alvo"], "", "", "Expanda personas.", 1000, context_artifacts=["prd"]),
    SectionPass("final_p03b", ["## Princípios Arquiteturais", "## Diferenciais"], "", "", "Expanda princípios.", 1000, context_artifacts=["prd", "system_design"]),
    SectionPass("final_p04", ["## Requisitos Funcionais"], "", "", "Consolide RFs.", 1000, context_artifacts=["prd"]),
    SectionPass("final_p05b", ["## Requisitos Não-Funcionais"], "", "", "Expanda RNFs.", 1000, context_artifacts=["prd"]),
    SectionPass("final_p06b", ["## Arquitetura e Tech Stack"], "", "", "Expanda arquitetura.", 1000, context_artifacts=["system_design"]),
    SectionPass("final_p06c", ["## ADRs"], "", "", "Gere ADRs.", 1000, context_artifacts=["system_design"]),
    SectionPass("final_p07", ["## Análise de Segurança"], "", "", "Sintetize STRIDE.", 1000, context_artifacts=["security_review"]),
    SectionPass("final_p08", ["## Escopo MVP"], "", "", "Referencie IDs.", 1000, context_artifacts=["prd"]),
    SectionPass("final_p09a", ["## Riscos Consolidados"], "", "", "Consolide riscos.", 1000, context_artifacts=["prd"]),
    SectionPass("final_p09b", ["## Métricas de Sucesso"], "", "", "Gere métricas.", 1000, context_artifacts=["prd"]),
    SectionPass("final_p10", ["## Plano de Implementação", "## Decisões do Debate"], "", "", "Gere plano/decisões.", 1000, context_artifacts=["development_plan", "debate_transcript"]),
    SectionPass("final_p11a", ["## Constraints Técnicos", "## Matriz de Rastreabilidade"], "", "", "Gere matriz.", 1000, context_artifacts=["prd"]),
    SectionPass("final_p11b", ["## Limitações Conhecidas"], "", "", "Gere limitações.", 1000, context_artifacts=["prd"]),
    SectionPass("final_p12", ["## Guia de Replicação Resumido", "## Cláusula de Integridade"], "", "", "Gere guia.", 1000, context_artifacts=["development_plan"]),
]
