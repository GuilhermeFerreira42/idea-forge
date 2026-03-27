from src.models.model_provider import ModelProvider
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, PRD_TEMPLATE, STYLE_CONTRACT
)
from src.core.sectional_generator import SectionalGenerator

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

    def consolidate_prd(self, artifacts_context: str, original_idea: str = "") -> str:
        """
        FASE 7.1: Consolida todos os artefatos do pipeline em um PRD final
        no padrão NEXUS Protocol v1.0.
        
        Chamada ÚNICA ao LLM (sem SectionalGenerator) para máxima coerência.
        """
        from src.core.prompt_templates import NEXUS_CONSOLIDATION_TEMPLATE
        
        prompt = (
            f"System: Você é o Agente PRODUCT MANAGER do sistema IdeaForge.\n"
            f"Sua tarefa é consolidar os artefatos de um projeto em um PRD FINAL definitivo.\n"
            f"Responda em Português. Use APENAS tabelas e bullets.\n\n"
            f"{NEXUS_CONSOLIDATION_TEMPLATE}\n\n"
        )
        
        if original_idea:
            prompt += f"IDEIA ORIGINAL DO USUÁRIO:\n{original_idea[:500]}\n\n"
        
        prompt += (
            f"ARTEFATOS DO PIPELINE (sintetize, não copie):\n"
            f"{artifacts_context}\n\n"
            f"GERE O PRD FINAL CONSOLIDADO AGORA."
        )
        
        result = self.provider.generate(
            prompt=prompt,
            role="product_manager"
        )
        
        # Fallback se resultado for muito curto
        if not result or len(result.strip()) < 200:
            return (
                "## PRD FINAL — CONSOLIDAÇÃO FALHOU\n\n"
                "O modelo não produziu um PRD consolidado válido.\n"
                "Consulte os artefatos individuais no relatório.\n"
            )
        
        return result
