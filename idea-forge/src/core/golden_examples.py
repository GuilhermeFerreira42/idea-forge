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
    "## Requisitos Funcionais\n"
    "| ID | Requisito | Critério de Aceite | Prioridade | Complexidade |\n"
    "|---|---|---|---|---|\n"
    "| RF-01 | Usuário cadastra conta com email e senha | "
    "POST /auth/register retorna 201 + JWT válido | Must | Low |\n"
    "| RF-02 | Usuário faz login com credenciais | "
    "POST /auth/login retorna 200 + JWT com exp 24h | Must | Low |\n"
    "| RF-03 | CRUD completo de tarefas | "
    "Endpoints GET/POST/PUT/DELETE em /tasks retornam status corretos | Must | Medium |\n"
    "| RF-04 | Filtrar tarefas por status | "
    "GET /tasks?status=done retorna apenas tarefas concluídas | Should | Low |\n"
    "| RF-05 | Paginação de resultados | "
    "GET /tasks?page=2&limit=10 retorna segundo lote de 10 itens | Should | Low |\n\n"
    "---\n"
    "FIM DO EXEMPLO. Agora gere o artefato real com base na ideia do usuário.\n\n"
)

# ─── Example: ADR + Riscos (extraído do NEXUS) ─────────────────────
DESIGN_EXAMPLE_FRAGMENT = (
    "EXEMPLO DE QUALIDADE ESPERADA (use como referência):\n\n"
    "## ADRs (Architecture Decision Records)\n"
    "| ID | Decisão | Contexto | Alternativa Rejeitada | Consequências |\n"
    "|---|---|---|---|---|\n"
    "| ADR-01 | SQLite como banco de dados | MVP com baixo volume, "
    "deploy local sem servidor de BD | PostgreSQL: requer setup separado | "
    "Limitação de concorrência, migrar para PG na v2 |\n"
    "| ADR-02 | FastAPI como framework web | Async nativo, tipagem Pydantic, "
    "OpenAPI auto | Django: overhead de ORM desnecessário para API-only | "
    "Dependência de ecossistema Starlette |\n\n"
    "## Riscos Técnicos\n"
    "| ID | Risco | Probabilidade | Impacto | Mitigação | Owner |\n"
    "|---|---|---|---|---|---|\n"
    "| R-01 | SQLite não suporta escritas concorrentes | Média | Alto | "
    "Write-ahead log + connection pooling com mutex | Backend Lead |\n"
    "| R-02 | JWT sem refresh token | Baixa | Médio | "
    "Implementar refresh endpoint na v1.1 | Security |\n\n"
    "---\n"
    "FIM DO EXEMPLO. Agora gere o artefato real.\n\n"
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
    "| ISS-01 | HIGH | SECURITY | Seção 'Modelo de Dados' | "
    "Senha de usuário sem menção a hashing | Adicionar campo password_hash "
    "com bcrypt, remover campo password plaintext |\n"
    "| ISS-02 | MEDIUM | COMPLETENESS | Seção 'Riscos' | "
    "Nenhum risco de infraestrutura identificado | Adicionar riscos de "
    "deploy, backup, e monitoramento |\n"
    "| ISS-03 | LOW | CONSISTENCY | Seção 'Tech Stack' vs 'Módulos' | "
    "Tech Stack menciona Redis mas nenhum módulo o utiliza | "
    "Remover Redis ou adicionar módulo de cache |\n\n"
    "---\n"
    "FIM DO EXEMPLO. Agora analise o artefato real.\n\n"
)

# ─── Example: Security Review (inspirado no NEXUS STRIDE) ──────────
SECURITY_EXAMPLE_FRAGMENT = (
    "EXEMPLO DE QUALIDADE ESPERADA (use como referência):\n\n"
    "## Ameaças Identificadas (STRIDE)\n"
    "| ID | Categoria STRIDE | Componente | Ameaça | Severidade | Mitigação |\n"
    "|---|---|---|---|---|---|\n"
    "| T-01 | S (Spoofing) | API /auth/login | Brute force de credenciais | "
    "Alta | Rate limiting (5 tentativas/min) + CAPTCHA após 3 falhas |\n"
    "| T-02 | I (Info Disclosure) | Endpoint /users/{id} | "
    "IDOR — acesso a dados de outros usuários | Alta | "
    "Verificar ownership do recurso via middleware de autorização |\n"
    "| T-03 | T (Tampering) | JWT Token | "
    "Token sem assinatura verificada no backend | Alta | "
    "Validar assinatura RS256 em cada request autenticado |\n\n"
    "---\n"
    "FIM DO EXEMPLO. Agora analise o artefato real.\n\n"
)
