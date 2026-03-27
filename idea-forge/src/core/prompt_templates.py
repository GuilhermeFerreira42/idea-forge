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

# ─── Template: PRD Calibrado NEXUS Protocol v1.0 (Fase 7) ────────────────

PRD_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DO PRD (PADRÃO NEXUS v1.0):\n\n"

    "## Objetivo\n"
    "- [1 frase, verbo no infinitivo, máximo 30 palavras, que capture o diferencial]\n\n"

    "## Problema\n"
    "| ID | Problema | Impacto | Como o Sistema Resolve |\n"
    "|---|---|---|---|\n"
    "| P-01 | ... | ... | ... |\n"
    "| P-02 | ... | ... | ... |\n"
    "| P-03 | ... | ... | ... |\n"
    "| P-04 | ... | ... | ... |\n\n"

    "## Público-Alvo\n"
    "| Segmento | Perfil (nome fictício + dor específica) | Prioridade (P0/P1/P2) |\n"
    "|---|---|---|\n"
    "| ... | Ex: 'Lucas, dev backend, quer API sem boilerplate' | P0 |\n\n"

    "## Princípios Arquiteturais\n"
    "| Princípio | Descrição Concreta | Implicação Técnica |\n"
    "|---|---|---|\n"
    "| ... | ... | ... |\n\n"

    "## Diferenciais\n"
    "| Abordagem Atual/Concorrente | Problema | Como Este Sistema Supera |\n"
    "|---|---|---|\n"
    "| ... | ... | ... |\n\n"

    "## Requisitos Funcionais\n"
    "| ID | Requisito | Critério de Aceite (verificável) | Prioridade (MoSCoW) | Complexidade |\n"
    "|---|---|---|---|---|\n"
    "| RF-01 | ... | [teste automatizável: ex: 'POST /api/x retorna 201'] | Must | Low |\n\n"

    "## Requisitos Não-Funcionais\n"
    "| ID | Categoria | Requisito | Métrica | Target |\n"
    "|---|---|---|---|---|\n"
    "| RNF-01 | Performance/Segurança/Usabilidade | ... | ... | ... |\n\n"

    "## Escopo MVP\n"
    "**Inclui:** [lista com bullets, referenciando IDs RF-XX]\n"
    "**NÃO inclui:** [lista com bullets, com justificativa curta]\n\n"

    "## Métricas de Sucesso\n"
    "| Métrica | Target | Prazo | Como Medir |\n"
    "|---|---|---|---|\n\n"

    "## Dependências e Riscos\n"
    "| ID | Tipo (Dep/Risco) | Descrição | Probabilidade | Impacto | Mitigação |\n"
    "|---|---|---|---|---|---|\n"
    "| R-01 | Risco | ... | Alta/Média/Baixa | Alto/Médio/Baixo | ... |\n\n"

    "## Constraints Técnicos\n"
    "- Linguagem: [valor ou 'A DEFINIR']\n"
    "- Framework: [valor ou 'A DEFINIR']\n"
    "- Banco de dados: [valor ou 'A DEFINIR']\n"
    "- Infraestrutura: [valor ou 'A DEFINIR']\n"
    "- Restrições de segurança: [valor ou 'A DEFINIR']\n"
)

# ─── Template: System Design Calibrado NEXUS (Fase 7) ─────────────────

SYSTEM_DESIGN_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DO SYSTEM DESIGN (PADRÃO NEXUS):\n"
    "NÃO repita informações do PRD — referencie por ID (RF-XX, RNF-XX).\n\n"

    "## Arquitetura Geral\n"
    "- Estilo: [ex: Monolito Modular | Microsserviços | Serverless]\n"
    "- Containers: [lista de componentes de deploy]\n"
    "- Comunicação: [sync/async, protocolos]\n"
    "- Diagrama (descrever em texto):\n"
    "  1. [Componente A] → [Componente B] via [protocolo]\n\n"

    "## Tech Stack\n"
    "| Camada | Tecnologia | Versão | Justificativa | Alternativa Rejeitada | Motivo Rejeição |\n"
    "|---|---|---|---|---|---|\n\n"

    "## Módulos\n"
    "| Módulo | Responsabilidade | Interface Pública | Requisitos Atendidos (RF-XX) |\n"
    "|---|---|---|---|\n\n"

    "## Modelo de Dados\n"
    "| Entidade | Atributos-chave | Tipo | Relações | Constraints |\n"
    "|---|---|---|---|---|\n\n"

    "## Fluxo de Dados\n"
    "1. [Ator] → [Componente] → [Ação] → [Resultado]\n"
    "2. ...\n"
    "(mínimo 5 passos)\n\n"

    "## ADRs (Architecture Decision Records)\n"
    "| ID | Decisão | Contexto | Alternativa Rejeitada | Consequências | Mitigação |\n"
    "|---|---|---|---|---|---|\n"
    "(mínimo 3 ADRs)\n\n"

    "## Riscos Técnicos\n"
    "| ID | Risco | Probabilidade | Impacto | Mitigação | Owner |\n"
    "|---|---|---|---|---|---|\n\n"

    "## Requisitos de Infraestrutura\n"
    "| Recurso | Mínimo | Recomendado | Justificativa |\n"
    "|---|---|---|---|\n"
)

# ─── Template: Review Calibrado NEXUS (Fase 7) ──────────────────────

REVIEW_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DA REVISÃO (PADRÃO NEXUS):\n\n"

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
    "| RF-01 | ✅ Atendido / ❌ Não atendido / ⚠️ Parcial | ... |\n"
    "(verificar CADA RF e RNF listado no PRD)\n\n"

    "## Verificação de Princípios Arquiteturais\n"
    "| Princípio | Respeitado? | Evidência |\n"
    "|---|---|---|\n\n"

    "## Sumário\n"
    "- [1-2 frases sobre o estado geral do artefato]\n\n"

    "## Recomendação\n"
    "- [Ação específica e concreta necessária para aprovação]\n"
)

# ─── Template: Security Review Calibrado NEXUS (Fase 7) ─────────────

SECURITY_REVIEW_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DA REVISÃO DE SEGURANÇA (PADRÃO NEXUS):\n\n"

    "## Superfície de Ataque\n"
    "| Componente | Tipo de Exposição | Nível de Risco | Justificativa |\n"
    "|---|---|---|---|\n\n"

    "## Ameaças Identificadas (STRIDE)\n"
    "| ID | Categoria STRIDE | Componente | Ameaça | Severidade | Mitigação Concreta |\n"
    "|---|---|---|---|---|---|\n"
    "| T-01 | S/T/R/I/D/E | ... | ... | Alta/Média/Baixa | [ação específica, não genérica] |\n"
    "(mínimo 3 ameaças)\n\n"

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

# ─── Template: Development Plan Calibrado NEXUS (Fase 7) ────────────

PLAN_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DO PLANO DE DESENVOLVIMENTO (PADRÃO NEXUS):\n\n"

    "## Arquitetura Sugerida\n"
    "- Estilo: [tipo]\n"
    "- Componentes: [lista com bullets]\n"
    "- Justificativa: [1 frase referenciando ADRs do System Design]\n\n"

    "## Módulos Core\n"
    "| Módulo | Responsabilidade | Prioridade | Requisitos (RF-XX) | Estimativa (dias) |\n"
    "|---|---|---|---|---|\n\n"

    "## Fases de Implementação\n"
    "| Fase | Duração | Entregas Concretas | Critério de Conclusão | Dependência |\n"
    "|---|---|---|---|---|\n"
    "(cada fase só inicia após conclusão da anterior)\n\n"

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

    "## Guia de Replicação\n"
    "1. Pré-requisitos: [linguagens, versões, ferramentas]\n"
    "2. Instalação: [comandos exatos]\n"
    "3. Configuração: [variáveis de ambiente]\n"
    "4. Execução: [comando para rodar]\n"
    "5. Verificação: [como validar que funciona]\n"
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
