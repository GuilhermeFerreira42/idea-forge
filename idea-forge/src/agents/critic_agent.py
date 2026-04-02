import logging
import re
from src.models.model_provider import ModelProvider
from src.conversation.conversation_manager import ConversationManager
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, REVIEW_TEMPLATE, STYLE_CONTRACT
)

logger = logging.getLogger(__name__)

# Diretiva adicionada ao system prompt quando em modo direto (sem reasoning)
DIRECT_MODE_SUFFIX = (
    "\n\nIMPORTANT: Respond directly without internal reasoning blocks. "
    "Do NOT use <think> tags. Go straight to your critique."
)

CRITIC_PROMPT_TEMPLATE = """Você é um revisor técnico sênior de PRDs.

Abaixo está um RESUMO ESTRUTURADO do PRD. Analise e gere sua revisão usando EXATAMENTE os headers abaixo, nesta ordem:

## Score de Qualidade
Nota de 0 a 10 com justificativa em uma linha.

## Issues Identificadas
Tabela com colunas: | ID | Severidade | Seção | Descrição |
Liste 5-10 issues encontradas.

## Verificação de Requisitos
Tabela com colunas: | Requisito | Presente | Completo | Observação |
Verifique se Público-Alvo, RFs, RNFs, Escopo MVP, Métricas existem.

## Sumário
3-5 frases resumindo os pontos fortes e fracos do PRD.

## Recomendação
APROVADO | APROVADO COM RESSALVAS | REPROVADO
Justificativa em 2-3 frases.

---
RESUMO DO PRD:
{prd_summary}
---

Sua análise crítica (use os headers exatos acima):"""

def _summarize_prd_for_critic(prd_content: str, max_tokens: int = 800) -> str:
    """
    Extrai resumo estruturado do PRD para o Critic.
    Não usa LLM — extração determinística por seções-chave.
    """
    summary_parts = []
    
    # Seções prioritárias para o Critic avaliar
    priority_sections = [
        "Visão do Produto",
        "Problema e Solução", 
        "Escopo (MVP)",
        "Requisitos Funcionais",
        "Requisitos Não-Funcionais",
        "Riscos",
        "Métricas de Sucesso",
    ]
    
    for section_name in priority_sections:
        # Extrair conteúdo da seção (adaptar regex ao formato real do PRD)
        pattern = rf"##\s*{re.escape(section_name)}\s*\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, prd_content, re.DOTALL)
        if match:
            section_text = match.group(1).strip()
            # Truncar cada seção proporcionalmente
            max_per_section = max_tokens // len(priority_sections)
            # Converter tokens aproximado: 1 token ≈ 4 chars em português
            max_chars = max_per_section * 4
            if len(section_text) > max_chars:
                section_text = section_text[:max_chars] + "..."
            summary_parts.append(f"## {section_name}\n{section_text}")
    
    summary = "\n\n".join(summary_parts)
    
    # Fallback: se nenhuma seção foi encontrada, pegar início do PRD
    if not summary_parts:
        max_chars = max_tokens * 4
        summary = prd_content[:max_chars] + "\n\n[RESUMO TRUNCADO — seções não detectadas]"
    
    return summary


class CriticAgent:
    """
    Analisa ideias e encontra problemas, lacunas e vulnerabilidades estruturais.
    """

    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self._base_system_prompt = (
            "Você é o Agente REVISOR do sistema IdeaForge.\n\n"
            "## REGRAS INVIOLÁVEIS\n"
            "1. Seja OBJETIVO — baseie-se em fatos verificáveis, não opiniões.\n"
            "2. Cada issue DEVE ter severidade: HIGH, MEDIUM, LOW.\n"
            "3. Cada issue DEVE ter sugestão de correção CONCRETA e ACIONÁVEL.\n"
            "4. NUNCA aprove artefato com lacunas de segurança classificadas HIGH.\n"
            "5. Verifique TODOS os requisitos referenciados, um por um.\n"
            "6. Emita quality_score numérico de 0 a 100.\n"
            "7. Sua saída DEVE ser Markdown válido seguindo o schema abaixo.\n"
            "8. Responda em Português.\n"
            "9. Se houver lista de ISSUES ABERTOS no contexto, NÃO os repita. "
            "Levante APENAS problemas NOVOS não listados.\n"
            "10. Cada novo issue DEVE ter ID incremental (ISS-XX) continuando a numeração existente.\n\n"
            "## CATEGORIAS DE ISSUE\n"
            "- SECURITY: Vulnerabilidades, dados sensíveis expostos\n"
            "- CORRECTNESS: Requisitos não atendidos, lógica incorreta\n"
            "- COMPLETENESS: Seções ausentes, informação insuficiente\n"
            "- CONSISTENCY: Contradições entre seções do artefato\n"
            "- FEASIBILITY: Proposta irrealizável com os constraints dados\n\n"
            "## MATRIZ DE SCORING\n"
            "| Critério | Peso | Threshold APROVADO |\n"
            "|---|---|---|\n"
            "| Completude de Requisitos | 30% | Todos RF/RNF preenchidos |\n"
            "| Segurança | 25% | Zero issues HIGH de segurança |\n"
            "| Viabilidade Técnica | 20% | Sem anti-patterns identificados |\n"
            "| Clareza/Testabilidade | 15% | Critérios de aceite verificáveis |\n"
            "| Consistência Interna | 10% | Zero contradições entre seções |\n\n"
            "## FORMATO DE SAÍDA OBRIGATÓRIO\n"
            f"{REVIEW_TEMPLATE}\n\n"
            f"{ANTI_PROLIXITY_DIRECTIVE}\n"
            f"{STYLE_CONTRACT}"
        )

    @property
    def system_prompt(self) -> str:
        """
        System prompt dinâmico baseado no modo de operação.
        FASE 2: Em direct_mode, adiciona diretiva de supressão de reasoning.
        """
        if self.direct_mode:
            return self._base_system_prompt + DIRECT_MODE_SUFFIX
        return self._base_system_prompt

    def analyze(self, idea: str, history: ConversationManager) -> str:
        """
        Analyze the idea and return a critique based on history.
        """
        prompt = (
            f"System: {self.system_prompt}\n\n"
            f"History Context:\n{history.get_context_string()}\n\n"
            f"Analyze this specific concept/idea:\n{idea}\n\n"
            "Provide your critique highlighting gaps and asking technical questions:"
        )

        response = self.provider.generate(
            prompt=prompt, context=history.get_history(), role="critic"
        )
        return response

    def review_artifact(self, artifact_content: str,
                        artifact_type: str = "document",
                        context: str = "") -> str:
        """
        FASE 5.1: Review com geração seccional (2 passes).
        Fallback para chamada única se seccional falhar.
        """
        from src.core.sectional_generator import SectionalGenerator

        # FASE 9.5: Usar resumo estruturado para evitar sobrecarga do Critic
        prd_summary = _summarize_prd_for_critic(artifact_content, max_tokens=800)
        logger.info(f"Critic input: {len(prd_summary)} chars (resumo de {len(artifact_content)} chars)")

        generator = SectionalGenerator(
            provider=self.provider,
            direct_mode=self.direct_mode
        )

        result = generator.generate_sectional(
            artifact_type="review",
            user_input=prd_summary,
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

        # FASE 9.5: Também usar resumo no fallback
        prd_summary = _summarize_prd_for_critic(artifact_content, max_tokens=800)
        
        review_prompt = CRITIC_PROMPT_TEMPLATE.format(prd_summary=prd_summary)
        
        if context:
            review_prompt += f"\n\nCONTEXTO ADICIONAL (NÃO repita):\n{context}\n\n"

        response = self.provider.generate(prompt=review_prompt, role="critic")
        
        if not response or len(response.strip()) < 50:
            logger.error(f"Critic retornou resposta insuficiente: {len(response)} chars")
            
        return response
