"""
prompt_templates.py — Templates de formato obrigatório para agentes SOP.

REGRAS:
- Nenhum template contém instrução narrativa
- Todos os templates são para tabelas, bullet points ou listas numeradas
- Templates são strings puras, sem lógica
- Idioma: Português para instruções de sistema, templates em formato universal
"""

# ─── Diretivas Anti-Prolixidade (aplicadas a TODOS os agentes) ───────────

ANTI_PROLIXITY_STRICT = (
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

ANTI_PROLIXITY_RICH = (
    "\nREGRAS OBRIGATÓRIAS DE FORMATO:\n"
    "1. PROIBIDO escrever introduções, conclusões, saudações ou meta-comentários\n"
    "2. PROIBIDO iniciar com 'Okay', 'Let me', 'Este documento', 'Com base na', 'A seguir'\n"
    "3. PERMITIDO prosa dentro de células de tabela para dar contexto real "
    "(ex: narrativa de persona, regra verificável, workaround técnico). "
    "PROIBIDO prosa FORA de tabelas e bullets.\n"
    "4. PROIBIDO repetir informações que já estão no contexto/artefato de entrada\n"
    "5. OBRIGATÓRIO usar: headings ##, bullet points -, tabelas |, listas numeradas 1.\n"
    "6. OBRIGATÓRIO responder em Português\n"
    "7. OBRIGATÓRIO começar cada seção diretamente com dados, sem preâmbulo\n"
    "8. Se faltar informação, escreva 'A DEFINIR' — nunca invente dados fictícios\n"
    "9. Para Público-Alvo: incluir nome fictício, idade e narrativa de 1-2 frases sobre a dor real.\n"
    "10. Para Princípios Arquiteturais: incluir REGRA verificável por teste automatizado.\n"
    "11. Para Limitações: incluir workaround atual e versão em que será resolvida.\n"
)

CONSOLIDATOR_DIRECTIVE = (
    "\nREGRAS DO CONSOLIDADOR (PRD FINAL):\n"
    "1. PROIBIDO introduções, conclusões, saudações ou meta-comentários.\n"
    "2. PROIBIDO iniciar com 'Okay', 'Let me', 'Este documento'.\n"
    "3. PERMITIDO prosa técnica dentro de células de tabela e em descrições de componentes, "
    "fluxos e justificativas de decisão. Máximo 3 linhas por parágrafo.\n"
    "4. PROIBIDO prosa fora de tabelas, bullets e headings — exceto em descrições de Responsabilidade "
    "de componentes (máximo 2 frases).\n"
    "5. OBRIGATÓRIO usar: headings ##, bullet points -, tabelas |, listas numeradas, "
    "blocos de código ``` para JSON/Mermaid/SQL.\n"
    "6. OBRIGATÓRIO responder em Português.\n"
    "7. OBRIGATÓRIO começar DIRETO com ## heading da primeira seção.\n"
    "8. Se faltar informação nos artefatos, INFERIR do contexto disponível — nunca escreva 'A DEFINIR'.\n"
    "9. JSON deve ser completo e funcional — nunca esqueleto com '...' ou comentários.\n"
    "10. Diagramas Mermaid devem estar em bloco de código ```mermaid.\n"
    "11. Cada princípio arquitetural DEVE ter regra verificável (REGRA: ...).\n"
    "12. Cada persona DEVE ter nome fictício, idade e narrativa de 1-2 frases.\n"
)

# Manter compatibilidade com agentes existentes
ANTI_PROLIXITY_DIRECTIVE = ANTI_PROLIXITY_STRICT

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

# ─── Template: Consolidação NEXUS (Fase 9.0 — Expandido) ────────────────────
NEXUS_CONSOLIDATION_TEMPLATE = (
    "TAREFA: Consolidar todos os artefatos abaixo em um PRD FINAL DEFINITIVO.\n\n"

    "REGRAS DE CONSOLIDAÇÃO:\n"
    "1. O documento final deve ser AUTOCONTIDO — alguém que leia apenas ele entende o projeto inteiro.\n"
    "2. INCORPORAR correções e issues do Critic (resolver, não apenas listar).\n"
    "3. INCORPORAR ADRs e decisões do System Design.\n"
    "4. INCORPORAR mitigações do Security Review.\n"
    "5. INCORPORAR pontos de consenso do Debate.\n"
    "6. NÃO copiar artefatos inteiros — sintetizar e consolidar.\n"
    "7. Cada seção deve refletir o estado FINAL (pós-debate, pós-review).\n"
    "8. Na Matriz de Rastreabilidade, cada RF DEVE aparecer exatamente uma vez.\n"
    "9. Na Cláusula de Integridade, marcar APENAS com ✅ ou ❌ — sem texto adicional.\n"
    "10. Responder em Português.\n\n"

    "FORMATO OBRIGATÓRIO DO PRD FINAL (PADRÃO NEXUS v1.0):\n\n"

    "## Visão do Produto\n"
    "- Codinome: [nome do projeto]\n"
    "- Declaração de visão: [1 frase, máx 30 palavras]\n\n"

    "## Problema e Solução\n"
    "| ID | Problema | Impacto | Como o Sistema Resolve |\n"
    "|---|---|---|---|\n\n"

    "## Público-Alvo\n"
    "| Segmento | Perfil | Prioridade |\n"
    "|---|---|---|\n\n"

    "## Princípios Arquiteturais\n"
    "| Princípio | Descrição | Implicação Técnica |\n"
    "|---|---|---|\n\n"

    "## Diferenciais\n"
    "| Abordagem Atual | Problema | Como Este Sistema Supera |\n"
    "|---|---|---|\n\n"

    "## Requisitos Funcionais (Consolidados)\n"
    "| ID | Requisito | Critério de Aceite | Prioridade | Complexidade | Status Pós-Review |\n"
    "|---|---|---|---|---|---|\n"
    "(incluir coluna de status baseada no Review)\n\n"

    "## Requisitos Não-Funcionais\n"
    "| ID | Categoria | Requisito | Métrica | Target |\n"
    "|---|---|---|---|---|\n\n"

    "## Arquitetura e Tech Stack (do System Design)\n"
    "- Estilo: [tipo]\n"
    "- Stack resumida em tabela\n"
    "| Camada | Tecnologia | Justificativa |\n"
    "|---|---|---|\n\n"

    "## ADRs (do System Design)\n"
    "| ID | Decisão | Alternativa Rejeitada | Consequências |\n"
    "|---|---|---|---|\n\n"

    "## Análise de Segurança (do Security Review)\n"
    "| ID | Ameaça STRIDE | Componente | Severidade | Mitigação |\n"
    "|---|---|---|---|---|\n\n"

    "## Escopo MVP\n"
    "**Inclui:** [lista com RF-XX — APENAS IDs que existem na tabela de RFs acima]\n"
    "**NÃO inclui:** [lista com justificativa]\n\n"

    "## Riscos Consolidados (PRD + Design + Security)\n"
    "| ID | Risco | Fonte | Probabilidade | Impacto | Mitigação |\n"
    "|---|---|---|---|---|---|\n\n"

    "## Métricas de Sucesso\n"
    "| Métrica | Target | Prazo | Como Medir |\n"
    "|---|---|---|---|\n\n"

    "## Plano de Implementação (resumo do Development Plan)\n"
    "| Fase | Duração | Entregas | Critério de Conclusão |\n"
    "|---|---|---|---|\n\n"

    "## Decisões do Debate (pontos de consenso)\n"
    "- [Decisão 1 com justificativa]\n"
    "- [Decisão 2 com justificativa]\n\n"

    "## Constraints Técnicos\n"
    "- Linguagem: [...]\n"
    "- Framework: [...]\n"
    "- Banco de dados: [...]\n"
    "- Infraestrutura: [...]\n\n"

    "## Matriz de Rastreabilidade\n"
    "| RF-ID | Componente/Módulo | Teste Associado | Status |\n"
    "|---|---|---|---|\n"
    "| RF-01 | [módulo responsável] | [tipo de teste: unit/integration/e2e] | Planejado |\n"
    "(OBRIGATÓRIO: cada RF da tabela de Requisitos Funcionais DEVE aparecer aqui exatamente uma vez)\n\n"

    "## Limitações Conhecidas\n"
    "| ID | Limitação | Impacto | Quando Será Resolvida |\n"
    "|---|---|---|---|\n"
    "| LIM-01 | [limitação técnica ou de escopo] | [impacto no usuário] | v2 / Nunca / A DEFINIR |\n\n"

    "## Guia de Replicação Resumido\n"
    "1. **Pré-requisitos:** [linguagem, versões, ferramentas obrigatórias]\n"
    "2. **Instalação:** [comandos exatos para setup]\n"
    "3. **Execução:** [comando para rodar o sistema]\n"
    "4. **Verificação:** [como confirmar que está funcionando]\n\n"

    "## Cláusula de Integridade\n"
    "| Item | Status |\n"
    "|---|---|\n"
    "| Todos os RF-IDs do Escopo existem na tabela de RFs | ✅/❌ |\n"
    "| Todos os riscos HIGH possuem mitigação definida | ✅/❌ |\n"
    "| Tech Stack é consistente entre seções | ✅/❌ |\n"
    "| Métricas de sucesso possuem target quantitativo | ✅/❌ |\n"
    "| Nenhuma seção contém placeholder 'A DEFINIR' | ✅/❌ |\n"
    "| Security Review endereça todas as ameaças HIGH | ✅/❌ |\n"
)
