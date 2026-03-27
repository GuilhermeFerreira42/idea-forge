"""
golden_examples.py — Trechos do NEXUS usados como few-shot examples.

Responsabilidade:
Fornecer exemplos concretos de output de alta qualidade para cada tipo
de artefato, permitindo que SLMs "aprendam" o nível de detalhe esperado.

Estratégia:
- Cada exemplo é um TRECHO (não o artefato completo) — máx 400 tokens
- Exemplos são injetados APÓS o template e ANTES do input do usuário
- O prompt diz: "EXEMPLO DE QUALIDADE ESPERADA (não copie, use como referência)"

NÃO contém lógica. Apenas constantes string.
"""

# ─── Example: Tabela de Requisitos Funcionais (extraído do NEXUS) ──
PRD_EXAMPLE_FRAGMENT = (
    "EXEMPLO DE QUALIDADE ESPERADA (use como referência de formato e densidade):\n\n"
    "## Problema\n"
    "| ID | Problema | Impacto | Como o Sistema Resolve |\n"
    "|---|---|---|---|\n"
    "| P-01 | Dependência de APIs em nuvem para coding assistants | Latência, custo recorrente, vendor lock-in | Inferência 100% local via Ollama |\n"
    "| P-02 | Dados proprietários enviados a terceiros | Risco de compliance (LGPD, GDPR) | Soberania total — zero egress de dados |\n"
    "| P-03 | Coding assistants são reativos, não proativos | Dev precisa micro-gerenciar cada passo | Agentes autônomos com ciclo plan→execute→review |\n"
    "| P-04 | Falta de revisão automatizada de código gerado | Código de baixa qualidade entra em produção | Agente Revisor dedicado com critérios mensuráveis |\n\n"
    "## Público-Alvo\n"
    "| Segmento | Perfil | Prioridade |\n"
    "|---|---|---|\n"
    "| Desenvolvedores Individuais | Lucas, dev fullstack, valoriza privacidade, tem RTX 3060 | P0 |\n"
    "| Equipes Pequenas (2-10) | Startup que não pode enviar código para APIs externas | P1 |\n"
    "| Empresas Regulamentadas | Org sob LGPD/GDPR que proíbe envio de dados a terceiros | P2 |\n\n"
    "## Requisitos Funcionais\n"
    "| ID | Requisito | Critério de Aceite | Prioridade | Complexidade |\n"
    "|---|---|---|---|---|\n"
    "| RF-01 | Usuário submete ideia em linguagem natural | Input via CLI aceita texto livre ≥10 chars | Must | Low |\n"
    "| RF-02 | Sistema decompõe ideia em subtarefas atômicas | Planner retorna DAG JSON com ≥2 tasks | Must | High |\n"
    "| RF-03 | Código gerado passa em linting automático | ruff check retorna exit 0 | Must | Medium |\n"
    "| RF-04 | Revisor emite score numérico 0-100 | ReviewVerdict.quality_score é int entre 0 e 100 | Must | Medium |\n"
    "| RF-05 | Self-healing corrige erros de import | ModuleNotFoundError → pip install automático → re-execução | Should | Medium |\n\n"
    "---\n"
    "FIM DO EXEMPLO. Gere o artefato real com base na ideia do usuário.\n\n"
)

# ─── Example: ADR + Riscos (extraído do NEXUS) ─────────────────────
DESIGN_EXAMPLE_FRAGMENT = (
    "EXEMPLO DE QUALIDADE ESPERADA (use como referência):\n\n"
    "## ADRs (Architecture Decision Records)\n"
    "| ID | Decisão | Contexto | Alternativa Rejeitada | Consequências | Mitigação |\n"
    "|---|---|---|---|---|---|\n"
    "| ADR-01 | SQLite como banco de dados | MVP com baixo volume, deploy local | PostgreSQL: requer setup separado | Limitação de concorrência | WAL mode + migrar para PG na v2 |\n"
    "| ADR-02 | FastAPI como framework | Async nativo, tipagem Pydantic, OpenAPI auto | Django: overhead de ORM para API-only | Dependência de Starlette | Documentação forte, comunidade ativa |\n"
    "| ADR-03 | JSON para persistência | Zero dependências, legível por humanos | SQLite: mais robusto | Não escala para milhares de registros | Volume esperado é dezenas, não milhares |\n\n"
    "## Riscos Técnicos\n"
    "| ID | Risco | Probabilidade | Impacto | Mitigação | Owner |\n"
    "|---|---|---|---|---|---|\n"
    "| R-01 | SQLite não suporta escritas concorrentes | Média | Alto | WAL mode + connection pooling com mutex | Backend Lead |\n"
    "| R-02 | Modelos 7B geram código de baixa qualidade | Alta | Alto | Self-healing + retry + fallback para modelo maior | ML Eng |\n"
    "| R-03 | JWT sem refresh token permite sessões eternas | Baixa | Médio | Implementar refresh endpoint na v1.1 | Security |\n\n"
    "---\nFIM DO EXEMPLO. Gere o artefato real.\n\n"
)

# ─── Example: Review com Scoring (inspirado no NEXUS ReviewVerdict) ─
REVIEW_EXAMPLE_FRAGMENT = (
    "EXEMPLO DE QUALIDADE ESPERADA (use como referência):\n\n"
    "## Score de Qualidade\n"
    "- **quality_score:** 72\n"
    "- **verdict:** NEEDS_CORRECTION\n\n"
    "## Issues Identificadas\n"
    "| ID | Severidade | Categoria | Localização | Descrição | Sugestão de Correção |\n"
    "|---|---|---|---|---|---|\n"
    "| ISS-01 | HIGH | SECURITY | Seção 'Modelo de Dados' | Senha de usuário armazenada sem menção a hashing | Adicionar campo password_hash com bcrypt, remover campo password plaintext |\n"
    "| ISS-02 | MEDIUM | COMPLETENESS | Seção 'Riscos' | Nenhum risco de infraestrutura identificado | Adicionar riscos de deploy, backup, monitoramento |\n"
    "| ISS-03 | LOW | CONSISTENCY | Tech Stack vs Módulos | Tech Stack menciona Redis mas nenhum módulo o utiliza | Remover Redis ou adicionar módulo de cache |\n\n"
    "## Verificação de Requisitos\n"
    "| Requisito ID | Status | Notas |\n"
    "|---|---|---|\n"
    "| RF-01 | ✅ Atendido | Input aceita texto livre |\n"
    "| RF-02 | ⚠️ Parcial | DAG gerado mas sem validação de ciclos |\n"
    "| RF-03 | ❌ Não atendido | Nenhum linting configurado |\n\n"
    "---\nFIM DO EXEMPLO. Analise o artefato real.\n\n"
)

# ─── Example: Security Review (inspirado no NEXUS STRIDE) ──────────
SECURITY_EXAMPLE_FRAGMENT = (
    "EXEMPLO DE QUALIDADE ESPERADA (use como referência):\n\n"
    "## Ameaças Identificadas (STRIDE)\n"
    "| ID | Categoria STRIDE | Componente | Ameaça | Severidade | Mitigação Concreta |\n"
    "|---|---|---|---|---|---|\n"
    "| T-01 | S (Spoofing) | API /auth/login | Brute force de credenciais | Alta | Rate limiting 5 tentativas/min + CAPTCHA após 3 falhas |\n"
    "| T-02 | I (Info Disclosure) | /users/{id} | IDOR — acesso a dados de outros usuários | Alta | Verificar ownership via middleware de autorização |\n"
    "| T-03 | T (Tampering) | JWT Token | Token sem assinatura verificada no backend | Alta | Validar assinatura RS256 em cada request autenticado |\n"
    "| T-04 | D (DoS) | API pública | Flood de requests sem rate limit | Média | Nginx rate limiting + circuit breaker |\n\n"
    "## Dados Sensíveis\n"
    "| Dado | Classificação | Criptografia | Retenção |\n"
    "|---|---|---|---|\n"
    "| Senha do usuário | PII Crítico | bcrypt (cost 12) | Indefinida |\n"
    "| Token JWT | Sessão | RS256 | 24h (exp claim) |\n"
    "| Email | PII | AES-256 em repouso | Até exclusão da conta |\n\n"
    "---\nFIM DO EXEMPLO. Analise o artefato real.\n\n"
)

# ─── Example: Development Plan (Fase 7) ─────────────────────────────
PLAN_EXAMPLE_FRAGMENT = (
    "EXEMPLO DE QUALIDADE ESPERADA (use como referência):\n\n"
    "## Fases de Implementação\n"
    "| Fase | Duração | Entregas | Critério de Conclusão | Dependência |\n"
    "|---|---|---|---|---|\n"
    "| Fase 0 — Setup | 1 semana | Repo, CI, configs, health check | make health → ✅ | Nenhuma |\n"
    "| Fase 1 — Core | 2 semanas | Agentes base, provider LLM, filesystem | Testes unitários 80%+ | Fase 0 |\n"
    "| Fase 2 — Pipeline | 2 semanas | Orquestrador, DAG, retry | Pipeline E2E com mock | Fase 1 |\n\n"
    "---\nFIM DO EXEMPLO. Gere o artefato real.\n\n"
)
