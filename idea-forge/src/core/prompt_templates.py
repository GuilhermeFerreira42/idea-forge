"""
prompt_templates.py — Templates de formato obrigatório para agentes SOP.

REGRAS:
- Nenhum template contém instrução narrativa
- Todos os templates são para tabelas, bullet points ou listas numeradas
- Templates são strings puras, sem lógica
- Idioma: Português para instruções de sistema, templates em formato universal
"""

# ─── Diretiva Anti-Prolixidade (aplicada a TODOS os agentes) ───────────

ANTI_PROLIXITY_DIRECTIVE = (
    "\nREGRAS OBRIGATÓRIAS DE FORMATO:\n"
    "1. PROIBIDO escrever introduções, conclusões, saudações ou meta-comentários\n"
    "2. PROIBIDO iniciar com 'Okay', 'Let me', 'Este documento', 'Com base na', 'A seguir'\n"
    "3. PROIBIDO parágrafos narrativos (>2 linhas de texto corrido)\n"
    "4. PROIBIDO repetir informações que já estão no contexto/artefato de entrada\n"
    "5. OBRIGATÓRIO usar APENAS: headings ##, bullet points -, tabelas |, listas numeradas 1.\n"
    "6. OBRIGATÓRIO responder em Português\n"
    "7. OBRIGATÓRIO começar cada seção diretamente com dados, sem preâmbulo\n"
    "8. Se faltar informação, escreva 'A DEFINIR' — nunca invente dados fictícios\n"
)

STYLE_CONTRACT = (
    "\nSTYLE CONTRACT: No introductions, no conclusions, no narrative paragraphs. "
    "Output only the required sections as bullets/tables. "
    "If you add prose, you violate the spec.\n"
)

# ─── Template: PRD ─────────────────────────────────────────────────────

PRD_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DO PRD (não adicionar outras seções):\n\n"
    "## Objetivo\n"
    "- [1 frase, verbo no infinitivo, máximo 25 palavras]\n\n"
    "## Problema\n"
    "- [problema 1]\n"
    "- [problema 2]\n\n"
    "## Requisitos Funcionais\n"
    "| ID | Requisito | Critério de Aceite | Prioridade |\n"
    "|---|---|---|---|\n"
    "| RF-01 | ... | ... | Must/Should/Could |\n\n"
    "## Requisitos Não-Funcionais\n"
    "| ID | Requisito | Métrica |\n"
    "|---|---|---|\n"
    "| RNF-01 | ... | ... |\n\n"
    "## Escopo MVP\n"
    "**Inclui:** [lista com bullets]\n"
    "**NÃO inclui:** [lista com bullets]\n\n"
    "## Métricas de Sucesso\n"
    "| Métrica | Target | Prazo |\n"
    "|---|---|---|\n\n"
    "## Dependências e Riscos\n"
    "- [bullet curto; se nenhum, escreva 'Nenhum identificado']\n"
)

# ─── Template: System Design ──────────────────────────────────────────

SYSTEM_DESIGN_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DO SYSTEM DESIGN (não adicionar outras seções):\n"
    "NÃO repita Business Goals, Target Audience ou Product Overview do PRD.\n\n"
    "## Arquitetura Geral\n"
    "- Estilo: [ex: Monolito Modular | Microsserviços | Serverless]\n"
    "- Componentes principais: [lista curta]\n\n"
    "## Tech Stack\n"
    "| Camada | Tecnologia | Justificativa (máx 10 palavras) |\n"
    "|---|---|---|\n\n"
    "## Módulos\n"
    "| Módulo | Responsabilidade (máx 10 palavras) | Interface |\n"
    "|---|---|---|\n\n"
    "## Modelo de Dados\n"
    "| Entidade | Atributos-chave | Relações |\n"
    "|---|---|---|\n\n"
    "## Fluxo de Dados\n"
    "1. [ator] → [ação] → [resultado]\n"
    "2. ...\n\n"
    "## Decisões de Design\n"
    "| Decisão | Alternativa Rejeitada | Motivo (máx 10 palavras) |\n"
    "|---|---|---|\n\n"
    "## Riscos Técnicos\n"
    "| Risco | Probabilidade | Mitigação |\n"
    "|---|---|---|\n"
)

# ─── Template: Review ─────────────────────────────────────────────────

REVIEW_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DA REVISÃO (não adicionar outras seções):\n\n"
    "## Lacunas Identificadas\n"
    "- [lacuna]: [impacto em 1 frase]\n\n"
    "## Riscos Técnicos\n"
    "| Risco | Severidade (Alta/Média/Baixa) | Sugestão |\n"
    "|---|---|---|\n\n"
    "## Perguntas Bloqueantes\n"
    "1. [pergunta que impede a implementação]\n\n"
    "## Sugestões de Melhoria\n"
    "- [sugestão concreta e acionável]\n"
)

# ─── Template: Resposta de Debate ─────────────────────────────────────

DEBATE_RESPONSE_TEMPLATE = (
    "REGRAS PARA ESTA RESPOSTA DE DEBATE:\n"
    "- NÃO comece com 'Okay', 'Let's', 'This is a good starting point'\n"
    "- NÃO resuma o que o outro agente disse\n"
    "- NÃO repita pontos de rounds anteriores\n"
    "- Vá DIRETO para novos pontos técnicos\n"
    "- Use APENAS bullet points ou tabelas\n"
    "- Máximo 300 palavras\n"
    "- Responda em Português\n"
)

# ─── Template: Development Plan ───────────────────────────────────────

PLAN_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DO PLANO (não adicionar outras seções):\n\n"
    "## Arquitetura Sugerida\n"
    "- [estilo + componentes em bullets]\n\n"
    "## Módulos Core\n"
    "| Módulo | Responsabilidade | Prioridade |\n"
    "|---|---|---|\n\n"
    "## Fases de Implementação\n"
    "| Fase | Duração | Entregas | Critério de Conclusão |\n"
    "|---|---|---|---|\n\n"
    "## Responsabilidades Técnicas\n"
    "| Papel | Escopo | Entregas |\n"
    "|---|---|---|\n\n"
    "## Riscos e Mitigações\n"
    "| Risco | Impacto | Mitigação |\n"
    "|---|---|---|\n"
)
