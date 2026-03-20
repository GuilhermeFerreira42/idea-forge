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

# ─── Template: PRD Densificado (Fase 4) ────────────────────────────

PRD_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DO PRD v2 (não adicionar outras seções):\n\n"
    "## Objetivo\n"
    "- [1 frase, verbo no infinitivo, máximo 25 palavras]\n\n"
    "## Problema\n"
    "| ID | Problema | Impacto | Evidência |\n"
    "|---|---|---|---|\n"
    "| P-01 | ... | ... | ... |\n\n"
    "## Requisitos Funcionais\n"
    "| ID | Requisito | Critério de Aceite | Prioridade (MoSCoW) | Complexidade |\n"
    "|---|---|---|---|---|\n"
    "| RF-01 | ... | ... | Must/Should/Could/Won't | Low/Med/High |\n\n"
    "## Requisitos Não-Funcionais\n"
    "| ID | Categoria | Requisito | Métrica | Target |\n"
    "|---|---|---|---|---|\n"
    "| RNF-01 | Performance/Segurança/Usabilidade | ... | ... | ... |\n\n"
    "## Escopo MVP\n"
    "**Inclui:** [lista com bullets, referenciando IDs RF-XX]\n"
    "**NÃO inclui:** [lista com bullets]\n\n"
    "## Métricas de Sucesso (SMART)\n"
    "| Métrica | Specific | Measurable | Target | Prazo |\n"
    "|---|---|---|---|---|\n\n"
    "## Dependências e Riscos\n"
    "| ID | Tipo (Dep/Risco) | Descrição | Probabilidade | Impacto | Mitigação |\n"
    "|---|---|---|---|---|---|\n"
    "| R-01 | Risco | ... | Alta/Média/Baixa | Alto/Médio/Baixo | ... |\n\n"
    "## Constraints Técnicos\n"
    "- Linguagem: [A DEFINIR se não especificado]\n"
    "- Framework: [A DEFINIR se não especificado]\n"
    "- Banco de dados: [A DEFINIR se não especificado]\n"
    "- Infraestrutura: [A DEFINIR se não especificado]\n"
)

# ─── Template: System Design Densificado (Fase 4) ──────────────────

SYSTEM_DESIGN_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DO SYSTEM DESIGN v2:\n"
    "NÃO repita Business Goals, Target Audience ou Product Overview do PRD.\n"
    "REFERENCIE requisitos por ID (RF-XX, RNF-XX).\n\n"
    "## Arquitetura Geral (C4 — Container Level)\n"
    "- Estilo: [ex: Monolito Modular | Microsserviços | Serverless]\n"
    "- Containers: [lista de componentes de deploy]\n"
    "- Comunicação: [sync/async, protocolos]\n\n"
    "## Tech Stack\n"
    "| Camada | Tecnologia | Versão | Justificativa | Alternativa Rejeitada |\n"
    "|---|---|---|---|---|\n\n"
    "## Módulos (C4 — Component Level)\n"
    "| Módulo | Responsabilidade | Interface | Requisitos Atendidos |\n"
    "|---|---|---|---|\n"
    "| ... | ... | REST/gRPC/Event | RF-01, RF-02 |\n\n"
    "## Modelo de Dados\n"
    "| Entidade | Atributos-chave | Tipo | Relações | Constraints |\n"
    "|---|---|---|---|---|\n\n"
    "## Fluxo de Dados (Sequencial)\n"
    "1. [Ator] → [Componente] → [Ação] → [Resultado]\n"
    "2. ...\n\n"
    "## ADRs (Architecture Decision Records)\n"
    "| ID | Decisão | Contexto | Alternativa Rejeitada | Consequências |\n"
    "|---|---|---|---|---|\n"
    "| ADR-01 | ... | ... | ... | ... |\n\n"
    "## Riscos Técnicos\n"
    "| ID | Risco | Probabilidade | Impacto | Mitigação | Owner |\n"
    "|---|---|---|---|---|---|\n\n"
    "## Requisitos de Infraestrutura\n"
    "| Recurso | Mínimo | Recomendado | Justificativa |\n"
    "|---|---|---|---|\n"
)

# ─── Template: Review Densificado (Fase 4) ─────────────────────────

REVIEW_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DA REVISÃO v2:\n\n"
    "## Score de Qualidade\n"
    "- **quality_score:** [0-100]\n"
    "- **verdict:** [APPROVED | NEEDS_CORRECTION | REJECTED]\n\n"
    "## Issues Identificadas\n"
    "| ID | Severidade | Categoria | Localização | Descrição | Sugestão de Correção |\n"
    "|---|---|---|---|---|---|\n"
    "| ISS-01 | HIGH/MED/LOW | SECURITY/CORRECTNESS/COMPLETENESS/CONSISTENCY/FEASIBILITY | Seção X | ... | ... |\n\n"
    "## Verificação de Requisitos\n"
    "| Requisito ID | Status | Notas |\n"
    "|---|---|---|\n"
    "| RF-01 | ✅ Atendido / ❌ Não atendido / ⚠️ Parcial | ... |\n\n"
    "## Sumário\n"
    "- [1-2 frases sobre o estado geral do artefato]\n\n"
    "## Recomendação\n"
    "- [Ação específica necessária para aprovação]\n"
)

# ─── Template: Security Review (Fase 4) ────────────────────────────

SECURITY_REVIEW_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DA REVISÃO DE SEGURANÇA:\n\n"
    "## Superfície de Ataque\n"
    "| Componente | Tipo de Exposição | Nível de Risco |\n"
    "|---|---|---|\n\n"
    "## Ameaças Identificadas (STRIDE)\n"
    "| ID | Categoria STRIDE | Componente | Ameaça | Severidade | Mitigação |\n"
    "|---|---|---|---|---|---|\n"
    "| T-01 | ... | ... | ... | Alta/Média/Baixa | ... |\n\n"
    "## Requisitos de Segurança Derivados\n"
    "| ID | Requisito | Prioridade | Ameaça Mitigada |\n"
    "|---|---|---|---|\n"
    "| RS-01 | ... | Must/Should | T-XX |\n\n"
    "## Dados Sensíveis\n"
    "| Dado | Classificação | Criptografia | Retenção |\n"
    "|---|---|---|---|\n\n"
    "## Plano de Autenticação/Autorização\n"
    "- Mecanismo: [ex: JWT, OAuth2, Session]\n"
    "- Granularidade: [ex: RBAC, ABAC, ACL]\n"
    "- Armazenamento de credenciais: [ex: bcrypt, argon2]\n"
)

# ─── Template: Development Plan Densificado (Fase 4) ───────────────

PLAN_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DO PLANO v2:\n\n"
    "## Arquitetura Sugerida\n"
    "- Estilo: [ex: Monolito Modular]\n"
    "- Componentes: [lista com bullets]\n"
    "- Justificativa: [1 frase referenciando ADRs]\n\n"
    "## Módulos Core\n"
    "| Módulo | Responsabilidade | Prioridade | Requisitos (RF-XX) | Estimativa |\n"
    "|---|---|---|---|---|\n\n"
    "## Fases de Implementação\n"
    "| Fase | Duração | Entregas | Critério de Conclusão | Riscos |\n"
    "|---|---|---|---|---|\n\n"
    "## Dependências Técnicas\n"
    "| Dependência | Versão | Propósito | Alternativa |\n"
    "|---|---|---|---|\n\n"
    "## Configurações de Ambiente\n"
    "| Variável | Obrigatória | Default | Descrição |\n"
    "|---|---|---|---|\n\n"
    "## Riscos e Mitigações (consolidado)\n"
    "| ID | Risco | Fonte (PRD/Design/Security) | Impacto | Mitigação | Owner |\n"
    "|---|---|---|---|---|---|\n\n"
    "## Plano de Testes\n"
    "| Tipo | Escopo | Ferramenta | Cobertura Mínima |\n"
    "|---|---|---|---|\n"
    "| Unitário | Módulos core | pytest | 80% |\n"
    "| Integração | APIs | pytest + httpx | Endpoints críticos |\n"
    "| Segurança | Autenticação | OWASP ZAP / manual | STRIDE mitigações |\n"
)

# ─── Template: Resposta de Debate (Mantido de 3.1) ──────────────────

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
