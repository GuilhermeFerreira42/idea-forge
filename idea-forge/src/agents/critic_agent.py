from src.models.model_provider import ModelProvider
from src.conversation.conversation_manager import ConversationManager
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, REVIEW_TEMPLATE, STYLE_CONTRACT
)

# Diretiva adicionada ao system prompt quando em modo direto (sem reasoning)
DIRECT_MODE_SUFFIX = (
    "\n\nIMPORTANT: Respond directly without internal reasoning blocks. "
    "Do NOT use <think> tags. Go straight to your critique."
)


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
            "8. Responda em Português.\n\n"
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

    def review_artifact(self, artifact_content: str, artifact_type: str = "document", context: str = "") -> str:
        """
        FASE 3.1: Analisa artefato com formato de lista/tabela forçado.
        """
        from src.core.golden_examples import REVIEW_EXAMPLE_FRAGMENT

        review_prompt = (
            f"System: {self.system_prompt}\n\n"
            f"ARTEFATO PARA REVISÃO (tipo: {artifact_type}):\n"
            f"{artifact_content}\n\n"
        )

        if context:
            review_prompt += (
                "CONTEXTO ADICIONAL (NÃO repita):\n"
                f"{context}\n\n"
            )

        # FASE 4: Injeção de golden example
        review_prompt += REVIEW_EXAMPLE_FRAGMENT

        review_prompt += (
            "Preencha EXATAMENTE as seções do template de revisão acima. "
            "NÃO escreva introduções ou conclusões."
        )

        return self.provider.generate(prompt=review_prompt, role="critic")
