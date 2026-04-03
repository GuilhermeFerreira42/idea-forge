from src.models.model_provider import ModelProvider
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, PRD_TEMPLATE, STYLE_CONTRACT
)
from src.core.sectional_generator import SectionalGenerator
from src.core.context_extractors import (
    extract_for_arquitetura_tech_stack,
    extract_for_plano_implementacao,
    extract_for_decisoes_debate,
    extract_for_guia_replicacao,
    generate_clausula_integridade,
)

# Diretiva adicionada ao system prompt quando em modo direto (sem reasoning)
DIRECT_MODE_SUFFIX = (
    "\n\nIMPORTANT: Respond directly without internal reasoning blocks. "
    "Do NOT use <think> tags. Go straight to your PRD."
)

class ProductManagerAgent:
    """
    Gera PRD (Product Requirements Document) a partir da ideia bruta.
    Opera sob SOP com Schema Enforcement (Fase 3.1).
    """

    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self._base_system_prompt = (
            "Você é o Agente PRODUCT MANAGER do sistema IdeaForge.\n\n"
            "## REGRAS INVIOLÁVEIS\n"
            "1. Sua saída DEVE seguir EXATAMENTE o schema de seções abaixo.\n"
            "2. Cada requisito DEVE ter ID único (RF-XX, RNF-XX).\n"
            "3. Cada requisito DEVE ter critério de aceite VERIFICÁVEL programaticamente.\n"
            "4. NUNCA gere mais de 20 requisitos funcionais por PRD.\n"
            "5. Se faltar informação, escreva 'A DEFINIR' — NUNCA invente dados.\n"
            "6. Sua saída DEVE ser Markdown válido. Nenhum texto fora das seções.\n"
            "7. Responda em Português.\n\n"
            "## FORMATO DE SAÍDA OBRIGATÓRIO\n"
            f"{PRD_TEMPLATE}\n\n"
            "## FRAMEWORKS DE ANÁLISE APLICADOS\n"
            "- Use MOSCOW (Must/Should/Could/Won't) para priorização\n"
            "- Use critérios SMART para métricas de sucesso\n"
            "- Identifique RISCOS usando Probabilidade × Impacto\n\n"
            f"{ANTI_PROLIXITY_DIRECTIVE}\n"
            f"{STYLE_CONTRACT}"
        )

    @property
    def system_prompt(self) -> str:
        if self.direct_mode:
            return self._base_system_prompt + DIRECT_MODE_SUFFIX
        return self._base_system_prompt

    def generate_prd(self, user_idea: str, context: str = "") -> str:
        """
        FASE 5.1: Geração de PRD seccional (4 passes).
        """
        generator = SectionalGenerator(
            provider=self.provider, 
            direct_mode=self.direct_mode
        )
        
        result = generator.generate_sectional(
            artifact_type="prd",
            user_input=user_idea,
            context=context
        )
        
        if result and len(result) > 200:
            return result
            
        # Fallback: chamada única
        return self._generate_single_pass(user_idea, context)

    def _generate_single_pass(self, user_idea: str, context: str) -> str:
        """Fallback de geração em chamada única."""
        from src.core.golden_examples import PRD_EXAMPLE_FRAGMENT
        
        prompt = (
            f"System: {self.system_prompt}\n\n"
            f"IDÉIA DO USUÁRIO:\n{user_idea}\n\n"
        )
        if context:
            prompt += f"CONTEXTO ADICIONAL:\n{context}\n\n"
            
        prompt += PRD_EXAMPLE_FRAGMENT
        prompt += "\nPreencha EXATAMENTE as seções do template acima."
        
        return self.provider.generate(prompt=prompt, role="product_manager")

    def _emit(self, message: str) -> None:
        """
        Emite mensagem de log para o terminal.
        Fail-safe: nunca lança exceção, mesmo em ambiente headless.
        FASE 9.6-FIX: Resolve AttributeError em consolidate_prd().
        """
        try:
            import sys
            from src.core.stream_handler import ANSIStyle
            sys.stdout.write(
                f"{ANSIStyle.CYAN}  {message}{ANSIStyle.RESET}\n"
            )
            sys.stdout.flush()
        except Exception:
            pass  # Log falhou — pipeline continua normalmente

    def _parse_artifact_sections(self, context: str) -> dict:
        """
        FASE 9.2: Divide o contexto consolidado em seções nomeadas.
        Procura por delimitadores como '--- ARTEFATO: [NOME] ---' ou similar.
        """
        import re
        sections = {}
        # Tenta capturar seções delimitadas por headings ou marcadores
        pattern = r"(?i)---?\s*(?:ARTEFATO|SEÇÃO):\s*([\w\s_]+)\s*---?\n(.*?)(?=\n---?\s*(?:ARTEFATO|SEÇÃO)|\Z)"
        matches = re.findall(pattern, context, re.DOTALL)

        if matches:
            for name, content in matches:
                sections[name.strip().lower()] = content.strip()
        else:
            # Fallback se não usar delimitadores: tenta headings ##
            pattern_h2 = r"(?m)^##\s*(.*?)\s*\n(.*?)(?=\n^##|\Z)"
            matches_h2 = re.findall(pattern_h2, context, re.DOTALL)
            for name, content in matches_h2:
                sections[name.strip().lower()] = content.strip()

        return sections

    def consolidate_prd(self, artifacts_context: str, original_idea: str = "") -> str:
        """
        FASE 9.2: Consolidação Granular (12 passes) com contexto seletivo.
        """
        from src.core.sectional_generator import NEXUS_FINAL_PASSES
        generator = SectionalGenerator(
            provider=self.provider,
            direct_mode=self.direct_mode
        )
        
        # 1. Parsear artefatos em dicionário
        parsed = self._parse_artifact_sections(artifacts_context)
        
        # 2. Preparar inputs específicos por pass
        pass_inputs = []
        for p in NEXUS_FINAL_PASSES:
            # Adicionar ideia original se disponível em todos os passes para coerência
            p_input = ""
            if original_idea:
                p_input += f"IDEIA ORIGINAL:\n{original_idea[:500]}\n\n"
            
            # Adicionar apenas artefatos solicitados por este pass
            for art_name in p.context_artifacts:
                art_content = parsed.get(art_name.lower())
                if art_content:
                    # FASE 9.5.3: Aplicação de extratores cirúrgicos por Pass ID
                    processed_content = art_content
                    if p.pass_id == "final_p06b" and art_name.lower() == "system_design":
                        processed_content = extract_for_arquitetura_tech_stack(art_content)
                    elif p.pass_id == "final_p10":
                        if art_name.lower() == "development_plan":
                            processed_content = extract_for_plano_implementacao(art_content)
                        elif art_name.lower() == "debate_transcript":
                            processed_content = extract_for_decisoes_debate(art_content)
                    elif p.pass_id == "final_p12" and art_name.lower() == "development_plan":
                        processed_content = extract_for_guia_replicacao(art_content)
                        
                    p_input += f"--- {art_name.upper()} ---\n{processed_content}\n\n"
                else:
                    # Fallback: se não achou via parse, tenta injetar do context inteiro
                    # (isso garante que não falte nada se o delimitador falhar)
                    p_input += f"--- {art_name.upper()} ---\n{artifacts_context[:1000]} (excerto)\n\n"
            
            pass_inputs.append(p_input)

        # 3. Gerar via orquestrador seletivo
        result = generator.generate_sectional_with_inputs(
            artifact_type="prd_final",
            pass_inputs=pass_inputs,
            passes=NEXUS_FINAL_PASSES
        )
        
        if result:
            # ═══ FASE 9.6: Retry Inteligente ═══
            if "[GERAÇÃO FALHOU" in result:
                from src.core.retry_orchestrator import RetryOrchestrator
                
                orchestrator = RetryOrchestrator(
                    provider=self.provider,
                    direct_mode=self.direct_mode
                )
                
                # Reusar o dict 'parsed' que já foi construído
                result = orchestrator.recover(result, parsed)
                
                # Log de recuperação
                for entry in orchestrator.get_recovery_log():
                    status = f"Nível {entry['level_used']}" if entry['level_used'] > 0 else "Deduplicada"
                    self._emit(
                        f"  Seção '{entry['heading']}' recuperada via {status} "
                        f"({entry['chars_recovered']} chars)"
                    )
            # ═══ FIM FASE 9.6 ═══

            # FASE 9.5.3: Adicionar Cláusula de Integridade via template estático
            from datetime import datetime
            
            # Contar falhas
            count_failed = result.count("[GERAÇÃO FALHOU]")
            
            clausula = generate_clausula_integridade(
                prd_final_chars=len(result),
                total_sections=20, # Fixo para o pipeline NEXUS
                failed_sections=count_failed,
                model_name=getattr(self.provider, "model_name", "Ollama 20B"),
                generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            # Se a última seção (Guia de Replicação) falhou, podemos anexar a cláusula
            # Caso contrário, tentamos substituir ou anexar ao final
            if "## Cláusula de Integridade" in result:
                # Substituir o placeholder gerado (ou falhado) pela versão estática
                import re
                result = re.sub(r"## Cláusula de Integridade.*", clausula, result, flags=re.DOTALL)
            else:
                result += "\n\n" + clausula

        if result and len(result) > 1000:
            return result
        
        # Fallback: chamada única (emergência)
        return self._consolidate_single_pass(artifacts_context, original_idea)

    def _consolidate_single_pass(self, artifacts_context: str, original_idea: str) -> str:
        """Fallback de consolidação em chamada única (Fase 7.1 original)."""
        from src.core.prompt_templates import NEXUS_CONSOLIDATION_TEMPLATE
        from src.core.golden_examples import NEXUS_FINAL_EXAMPLE_FRAGMENT
        
        prompt = (
            f"System: Você é o Agente PRODUCT MANAGER do sistema IdeaForge.\n"
            f"Sua tarefa é consolidar os artefatos de um projeto em um PRD FINAL definitivo.\n"
            f"Responda em Português. Use tabelas e bullets. "
            f"PERMITIDO prosa dentro de células para dar contexto real.\n\n"
            f"{NEXUS_CONSOLIDATION_TEMPLATE}\n\n"
        )
        
        if original_idea:
            prompt += f"IDEIA ORIGINAL DO USUÁRIO:\n{original_idea[:500]}\n\n"
        
        prompt += NEXUS_FINAL_EXAMPLE_FRAGMENT
        
        prompt += (
            f"ARTEFATOS DO PIPELINE (sintetize, não copie):\n"
            f"{artifacts_context}\n\n"
            f"GERE O PRD FINAL CONSOLIDADO AGORA."
        )
        
        result = self.provider.generate(
            prompt=prompt,
            role="product_manager"
        )
        
        if not result or len(result.strip()) < 200:
            return (
                "## PRD FINAL — CONSOLIDAÇÃO FALHOU\n\n"
                "O modelo não produziu um PRD consolidado válido.\n"
                "Consulte os artefatos individuais no relatório.\n"
            )
        
        return result

