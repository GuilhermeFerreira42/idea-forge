# BLUEPRINT — FASE 4: UPGRADE DE MATURIDADE TÉCNICA (Padrão NEXUS)

---

## 1. DIAGNÓSTICO: DELTA IdeaForge vs. NEXUS

### 1.1 — Mapa de Lacunas

| Dimensão | IdeaForge (Estado Atual) | NEXUS (Golden Standard) | Gap |
|---|---|---|---|
| **Persona dos Agentes** | "Arquiteto Sênior analítico" / "Engenheiro Líder visionário" — generalistas com adjetivos | Staff/Principal Engineers com SOP numerado, regras invioláveis, budget de tokens, formato de saída JSON-enforced | Profundidade de expertise, determinismo de output |
| **Estrutura de Artefatos** | Templates em `prompt_templates.py` com seções Markdown (tabelas/bullets) | JSON Schemas formais com `$schema`, `required`, `properties`, `enum`, `pattern` — validáveis programaticamente | Schema enforcement programático, rastreabilidade máquina-legível |
| **Cobertura de Domínio** | PRD → Review → Approval → System Design → Debate → Plan | PRD + DAG de subtarefas + Execução + Revisão com scoring + Self-healing L1-L6 + Escalation + Rollback + Resource Monitoring | Segurança, Infraestrutura, Recovery, Observabilidade |
| **Contratos Inter-Agente** | Strings passadas entre agentes via `generate()` → `str` | 8 JSON Schemas tipados com IDs rastreáveis, validação pré-dispatch, audit trail completo | Tipagem de mensagens, validação, auditoria |
| **Gestão de Contexto** | `usage_hint` + truncação por chars/4 + janela deslizante no debate | AST-based chunking + FAISS retrieval + Resumo progressivo + Budget % por agente + Compressão de histórico | Retrieval semântico, budget proporcional, chunking inteligente |
| **Resiliência** | Fallback de pipeline (Blackboard → Legacy) + post-processor de ruído | Classificação L1-L6 + Self-healing patterns + Rollback Git por subtarefa + Graceful degradation de modelo + Resume após crash | Profundidade de recovery, granularidade de rollback |

### 1.2 — Causa Raiz da Divergência

```
NEXUS é DENSO porque:
1. Cada agente tem CONTRATO DE SAÍDA (JSON Schema) — não "sugestão de formato"
2. Cada decisão tem RASTREABILIDADE (IDs, hashes, timestamps)
3. Cada falha tem TAXONOMIA (L1-L6) e PROCEDIMENTO DE RECOVERY
4. Cada recurso tem BUDGET QUANTIFICADO (tokens, RAM, VRAM, tempo)
5. Cada interação tem VALIDAÇÃO PROGRAMÁTICA (não "espero que o LLM siga o formato")

IdeaForge é RASO porque:
1. Templates são SUGESTÕES textuais — o LLM pode ignorar
2. Artefatos são STRINGS OPACAS — sem validação de estrutura
3. Erros são GENÉRICOS — try/except com retry, sem classificação
4. Recursos são FIXOS — num_predict hardcoded, sem adaptação
5. Revisão é NARRATIVA — o Critic opina, não PONTUA
```

---

## 2. PLANO DE AÇÃO — 4 VETORES DE UPGRADE

### VETOR 1: Refinamento de Persona (Expertise)

#### 2.1.1 — Reescrita de System Prompts: De "Assistente" para "Staff Engineer"

**Princípio:** O system prompt do NEXUS não diz "você é experiente". Ele diz "estas são suas REGRAS INVIOLÁVEIS" + "este é seu FORMATO DE SAÍDA" + "NENHUM texto fora do formato".

**Mudanças em `src/agents/product_manager_agent.py`:**

```python
# ANTES (Fase 3.1):
self._base_system_prompt = (
    "Você é um Product Manager técnico. "
    "Saída APENAS em Markdown estruturado, sem prosa.\n\n"
    f"{PRD_TEMPLATE}\n"
    f"{ANTI_PROLIXITY_DIRECTIVE}\n"
    f"{STYLE_CONTRACT}"
)

# DEPOIS (Fase 4 — Padrão NEXUS):
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
```

**Mudanças em `src/agents/architect_agent.py`:**

```python
# DEPOIS (Fase 4):
self._base_system_prompt = (
    "Você é o Agente ARQUITETO do sistema IdeaForge.\n\n"
    "## REGRAS INVIOLÁVEIS\n"
    "1. NÃO repita informações do PRD — referencie por ID (RF-XX).\n"
    "2. Cada decisão de design DEVE ter alternativa rejeitada + justificativa.\n"
    "3. Cada risco técnico DEVE ter probabilidade (Alta/Média/Baixa) + mitigação.\n"
    "4. O modelo de dados DEVE ser normalizável e incluir relações explícitas.\n"
    "5. O fluxo de dados DEVE ser numerado sequencialmente.\n"
    "6. Sua saída DEVE ser Markdown válido seguindo o schema abaixo.\n"
    "7. Responda em Português.\n\n"
    "## FRAMEWORKS DE ANÁLISE\n"
    "- Use C4 Model (Context/Container/Component) para descrever arquitetura\n"
    "- Documente decisões como ADRs: Contexto → Decisão → Consequências\n"
    "- Aplique STRIDE simplificado para ameaças: Spoofing, Tampering,\n"
    "  Repudiation, Information Disclosure, DoS, Elevation of Privilege\n\n"
    "## FORMATO DE SAÍDA OBRIGATÓRIO\n"
    f"{SYSTEM_DESIGN_TEMPLATE}\n\n"
    f"{ANTI_PROLIXITY_DIRECTIVE}\n"
    f"{STYLE_CONTRACT}"
)
```

**Mudanças em `src/agents/critic_agent.py`:**

```python
# DEPOIS (Fase 4):
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
```

**Novo agente recomendado: `src/agents/security_reviewer_agent.py` (CRIAR):**

```python
"""
security_reviewer_agent.py — Agente de Revisão de Segurança (Hardening).

Responsabilidade:
Analisar System Design para ameaças de segurança usando STRIDE simplificado.
Produzir relatório de ameaças com mitigações concretas.

Contrato:
    Input: System Design (string) + PRD (string para contexto)
    Output: Security Review em Markdown com tabela de ameaças
"""
from src.models.model_provider import ModelProvider
from src.core.prompt_templates import (
    ANTI_PROLIXITY_DIRECTIVE, SECURITY_REVIEW_TEMPLATE, STYLE_CONTRACT
)

DIRECT_MODE_SUFFIX = (
    "\n\nIMPORTANT: Respond directly without internal reasoning blocks. "
    "Do NOT use <think> tags. Go straight to your security analysis."
)

class SecurityReviewerAgent:
    """
    Analisa artefatos de design para ameaças de segurança.
    Opera sob STRIDE simplificado.
    """
    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self._base_system_prompt = (
            "Você é o Agente de SEGURANÇA do sistema IdeaForge.\n\n"
            "## REGRAS INVIOLÁVEIS\n"
            "1. Analise CADA componente do System Design contra STRIDE.\n"
            "2. Cada ameaça DEVE ter: categoria, componente afetado, "
            "severidade, mitigação concreta.\n"
            "3. NUNCA ignore autenticação, autorização ou validação de input.\n"
            "4. Se o design não menciona criptografia de dados sensíveis, "
            "isso é automaticamente uma ameaça HIGH.\n"
            "5. Responda em Português.\n\n"
            "## CATEGORIAS STRIDE\n"
            "- S: Spoofing (falsificação de identidade)\n"
            "- T: Tampering (adulteração de dados)\n"
            "- R: Repudiation (negação de ações)\n"
            "- I: Information Disclosure (vazamento de dados)\n"
            "- D: Denial of Service (indisponibilidade)\n"
            "- E: Elevation of Privilege (escalonamento)\n\n"
            "## FORMATO DE SAÍDA OBRIGATÓRIO\n"
            f"{SECURITY_REVIEW_TEMPLATE}\n\n"
            f"{ANTI_PROLIXITY_DIRECTIVE}\n"
            f"{STYLE_CONTRACT}"
        )

    @property
    def system_prompt(self) -> str:
        if self.direct_mode:
            return self._base_system_prompt + DIRECT_MODE_SUFFIX
        return self._base_system_prompt

    def review_security(self, system_design: str, prd_context: str = "") -> str:
        """
        Analisa System Design para ameaças de segurança.
        """
        prompt = f"System: {self.system_prompt}\n\n"
        if prd_context:
            prompt += (
                "PRD (REFERÊNCIA — NÃO repita):\n"
                f"{prd_context[:500]}\n\n"
            )
        prompt += (
            f"SYSTEM DESIGN PARA ANÁLISE:\n{system_design}\n\n"
            "Preencha EXATAMENTE as seções do template de segurança."
        )
        return self.provider.generate(prompt=prompt, role="security_reviewer")
```

---

### VETOR 2: Estrutura de Artefatos (Templates Densificados)

#### 2.2.1 — Novos Templates em `src/core/prompt_templates.py`

**Templates a ADICIONAR:**

```python
# ─── Template: Security Review ─────────────────────────────────────
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

# ─── Template: Infrastructure/Deployment ────────────────────────────
INFRASTRUCTURE_TEMPLATE = (
    "FORMATO OBRIGATÓRIO DE INFRAESTRUTURA:\n\n"
    "## Ambiente de Deploy\n"
    "- Tipo: [ex: VPS, Container, Serverless, Local]\n"
    "- Provider: [ex: Self-hosted, AWS, GCP, Vercel]\n\n"
    "## Dependências de Infraestrutura\n"
    "| Serviço | Versão Mínima | Propósito | Fallback |\n"
    "|---|---|---|---|\n\n"
    "## Configuração de Ambiente\n"
    "| Variável | Obrigatória | Default | Descrição |\n"
    "|---|---|---|---|\n\n"
    "## Plano de Monitoramento\n"
    "| Métrica | Threshold Warning | Threshold Critical | Ação |\n"
    "|---|---|---|---|\n\n"
    "## Plano de Recuperação de Desastres\n"
    "| Cenário | RTO | RPO | Procedimento |\n"
    "|---|---|---|---|\n"
    "- RTO: Recovery Time Objective (tempo máximo para restaurar)\n"
    "- RPO: Recovery Point Objective (perda máxima de dados aceitável)\n"
)

# ─── Template: PRD Densificado (Fase 4) ────────────────────────────
PRD_TEMPLATE_V2 = (
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
SYSTEM_DESIGN_TEMPLATE_V2 = (
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
REVIEW_TEMPLATE_V2 = (
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
```

---

### VETOR 3: Injeção de Contexto (Golden Examples como Few-Shot)

#### 2.3.1 — Módulo de Golden Examples

**Arquivo a CRIAR: `src/core/golden_examples.py`**

```python
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
```

#### 2.3.2 — Integração nos Agentes

**Mudança em `product_manager_agent.py` → `generate_prd()`:**

```python
from src.core.golden_examples import PRD_EXAMPLE_FRAGMENT

def generate_prd(self, idea: str, context: str = "") -> str:
    prompt = f"System: {self.system_prompt}\n\n"
    if context:
        prompt += f"CONTEXTO (NÃO repita):\n{context}\n\n"
    # FASE 4: Injeção de golden example como few-shot
    prompt += PRD_EXAMPLE_FRAGMENT
    prompt += (
        f"IDEIA DO USUÁRIO:\n{idea}\n\n"
        "Preencha EXATAMENTE as seções do template acima com base na ideia. "
        "Não adicione seções extras. Não escreva introduções."
    )
    return self.provider.generate(prompt=prompt, role="product_manager")
```

**Padrão idêntico aplicado a:**
- `architect_agent.py` → `design_system()` — injeta `DESIGN_EXAMPLE_FRAGMENT`
- `critic_agent.py` → `review_artifact()` — injeta `REVIEW_EXAMPLE_FRAGMENT`
- `security_reviewer_agent.py` → `review_security()` — injeta `SECURITY_EXAMPLE_FRAGMENT`

#### 2.3.3 — Controle de Budget com Few-Shot

**Mudança em `src/models/ollama_provider.py`:**

```python
# FASE 4: Aumentar num_predict para acomodar examples + resposta densa
if self.think:
    options["num_predict"] = 3000   # Reasoning mode
    options["temperature"] = 0.7
else:
    options["num_predict"] = 1200   # Direct mode: aumentado de 800 para 1200
    options["temperature"] = 0.1    # Mantém determinístico
```

**Justificativa:** Os golden examples consomem ~300-400 tokens do input. Para manter a qualidade de resposta, o budget de output precisa subir de 800 para 1200.

---

### VETOR 4: Expansão do SOP (Novos Agentes e Sub-fases)

#### 2.4.1 — Nova DAG de Tasks (7 tasks em vez de 6)

**Mudança em `src/core/planner.py` → `load_default_dag()`:**

```python
def load_default_dag(self) -> None:
    """
    FASE 4: DAG expandida com 7 tasks.
    Adicionada TASK_04b (Security Review) entre System Design e Debate.
    """
    self.dag = [
        TaskDefinition(
            task_id="TASK_01",
            agent_name="product_manager",
            method_name="generate_prd",
            input_artifacts=["user_idea"],
            output_artifact="prd",
            requires=[]
        ),
        TaskDefinition(
            task_id="TASK_02",
            agent_name="critic",
            method_name="review_artifact",
            input_artifacts=["prd"],
            output_artifact="prd_review",
            requires=["TASK_01"]
        ),
        TaskDefinition(
            task_id="TASK_03",
            agent_name="system",
            method_name="human_gate",
            input_artifacts=["prd", "prd_review"],
            output_artifact="approval_decision",
            requires=["TASK_02"],
            task_type="HUMAN_GATE"
        ),
        TaskDefinition(
            task_id="TASK_04",
            agent_name="architect",
            method_name="design_system",
            input_artifacts=["prd", "approval_decision"],
            output_artifact="system_design",
            requires=["TASK_03"]
        ),
        # FASE 4: Nova task de Security Review
        TaskDefinition(
            task_id="TASK_04b",
            agent_name="security_reviewer",
            method_name="review_security",
            input_artifacts=["system_design", "prd"],
            output_artifact="security_review",
            requires=["TASK_04"]
        ),
        TaskDefinition(
            task_id="TASK_05",
            agent_name="debate_engine",
            method_name="run",
            input_artifacts=["prd", "system_design", "security_review"],
            output_artifact="debate_transcript",
            requires=["TASK_04b"],  # Agora depende de security review
            task_type="ENGINE"
        ),
        TaskDefinition(
            task_id="TASK_06",
            agent_name="plan_generator",
            method_name="generate_plan",
            input_artifacts=["prd", "system_design", "security_review", "debate_transcript"],
            output_artifact="development_plan",
            requires=["TASK_05"],
            task_type="ENGINE"
        )
    ]
    for task in self.dag:
        self.blackboard.set_task_status(task.task_id, TaskStatus.PENDING)
```

#### 2.4.2 — Registro do Novo Agente no Controller

**Mudança em `src/core/controller.py` → `__init__()`:**

```python
from src.agents.security_reviewer_agent import SecurityReviewerAgent

# Dentro de __init__:
self.agents = {
    "product_manager": ProductManagerAgent(provider, direct_mode=direct_mode),
    "architect": ArchitectAgent(provider, direct_mode=direct_mode),
    "critic": CriticAgent(provider, direct_mode=direct_mode),
    "proponent": ProponentAgent(provider, direct_mode=direct_mode),
    # FASE 4: Novo agente de segurança
    "security_reviewer": SecurityReviewerAgent(provider, direct_mode=direct_mode),
    "debate_engine": DebateEngine(
        proponent=ProponentAgent(provider, direct_mode=direct_mode),
        critic=CriticAgent(provider, direct_mode=direct_mode),
        rounds=3
    ),
    "plan_generator": PlanGenerator(provider)
}
```

#### 2.4.3 — Routing do Novo Agente no Planner

**Mudança em `src/core/planner.py` → `_execute_task()`:**

```python
# Adicionar na seção de dispatch por method_name:
elif task.method_name == "review_security":
    # Security Reviewer recebe system_design como primeiro input, PRD como contexto
    system_design_art = self.artifact_store.read("system_design")
    prd_art = self.artifact_store.read("prd")
    result = method(
        system_design=system_design_art.content if system_design_art else "",
        prd_context=prd_art.content[:500] if prd_art else ""
    )
```

#### 2.4.4 — Template do Plan Generator Densificado

**Mudança em `src/core/prompt_templates.py`:**

```python
# ─── Template: Development Plan Densificado (Fase 4) ───────────────
PLAN_TEMPLATE_V2 = (
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
```

---

## 3. VALIDAÇÃO DE OUTPUT — Pós-Processador de Conformidade

**Arquivo a CRIAR: `src/core/output_validator.py`**

```python
"""
output_validator.py — Validador de conformidade de artefatos gerados.

Responsabilidade:
Verificar se o output do LLM contém as seções obrigatórias do template.
Calcular density_score. Rejeitar outputs que não atendem threshold mínimo.

NÃO usa LLM. Apenas regex e heurísticas.
"""
import re
from typing import Dict, List, Tuple


class OutputValidator:
    """Valida conformidade de artefatos contra templates esperados."""

    # Seções obrigatórias por tipo de artefato
    REQUIRED_SECTIONS = {
        "prd": [
            "## Objetivo",
            "## Problema",
            "## Requisitos Funcionais",
            "## Requisitos Não-Funcionais",
            "## Escopo MVP",
            "## Métricas de Sucesso",
            "## Dependências e Riscos",
        ],
        "system_design": [
            "## Arquitetura Geral",
            "## Tech Stack",
            "## Módulos",
            "## Modelo de Dados",
            "## Fluxo de Dados",
            "## Riscos Técnicos",
        ],
        "review": [
            "## Score de Qualidade",
            "## Issues Identificadas",
            "## Verificação de Requisitos",
            "## Sumário",
            "## Recomendação",
        ],
        "security_review": [
            "## Superfície de Ataque",
            "## Ameaças Identificadas",
            "## Requisitos de Segurança Derivados",
            "## Dados Sensíveis",
        ],
        "plan": [
            "## Arquitetura Sugerida",
            "## Módulos Core",
            "## Fases de Implementação",
            "## Riscos e Mitigações",
        ],
    }

    def validate(self, content: str, artifact_type: str) -> Dict:
        """
        Valida artefato contra seções obrigatórias.

        Returns:
            {
                "valid": bool,
                "missing_sections": list[str],
                "present_sections": list[str],
                "completeness_score": float,  # 0.0 - 1.0
                "density_score": float,        # 0.0 - 1.0
                "has_tables": bool,
                "table_count": int
            }
        """
        required = self.REQUIRED_SECTIONS.get(artifact_type, [])
        present = []
        missing = []

        for section in required:
            if section in content:
                present.append(section)
            else:
                missing.append(section)

        completeness = len(present) / len(required) if required else 1.0
        density = self._calculate_density(content)
        table_count = content.count("|---|")

        return {
            "valid": completeness >= 0.8 and density >= 0.6,
            "missing_sections": missing,
            "present_sections": present,
            "completeness_score": completeness,
            "density_score": density,
            "has_tables": table_count > 0,
            "table_count": table_count,
        }

    def _calculate_density(self, content: str) -> float:
        """Calcula razão linhas técnicas / total linhas."""
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        if not lines:
            return 0.0
        technical = 0
        for line in lines:
            if (line.startswith('|') or
                line.startswith('-') or
                line.startswith('##') or
                line.startswith('```') or
                (len(line) > 1 and line[0].isdigit() and line[1] in '.)')):
                technical += 1
        return technical / len(lines)
```

**Integração no Planner (pós-processamento):**

```python
# Em _execute_task(), após capturar resultado do agente:
from src.core.output_validator import OutputValidator

validator = OutputValidator()
validation = validator.validate(clean_result, self._get_artifact_type_from_task(task))

if not validation["valid"]:
    # Log warning mas NÃO rejeita — SLMs podem falhar parcialmente
    import sys
    from src.core.stream_handler import ANSIStyle
    sys.stdout.write(
        f"{ANSIStyle.YELLOW}[VALIDATOR] Artefato {task.output_artifact} "
        f"incompleto: {validation['missing_sections']} "
        f"(density: {validation['density_score']:.2f}){ANSIStyle.RESET}\n"
    )
```

---

## 4. ORDEM DE IMPLEMENTAÇÃO

```
FASE 4 — UPGRADE DE MATURIDADE TÉCNICA
══════════════════════════════════════

STEP 01: src/core/prompt_templates.py     ← MODIFICAR
    Adicionar: PRD_TEMPLATE_V2, SYSTEM_DESIGN_TEMPLATE_V2,
    REVIEW_TEMPLATE_V2, SECURITY_REVIEW_TEMPLATE,
    INFRASTRUCTURE_TEMPLATE, PLAN_TEMPLATE_V2
    Dependências: ZERO
    Validação: importação sem erro

STEP 02: src/core/golden_examples.py      ← CRIAR
    Dependências: ZERO
    Validação: importação sem erro

STEP 03: src/core/output_validator.py     ← CRIAR
    Dependências: ZERO
    Validação: pytest tests/test_output_validator.py

STEP 04: src/agents/security_reviewer_agent.py ← CRIAR
    Dependências: prompt_templates, golden_examples
    Validação: pytest tests/test_security_reviewer.py

STEP 05: src/agents/product_manager_agent.py ← MODIFICAR
    Mudança: system prompt v2 + golden example injection
    Validação: pytest tests/test_new_agents.py

STEP 06: src/agents/architect_agent.py    ← MODIFICAR
    Mudança: system prompt v2 + golden example + ADR/C4/STRIDE
    Validação: pytest tests/test_new_agents.py

STEP 07: src/agents/critic_agent.py       ← MODIFICAR
    Mudança: system prompt v2 + scoring matrix + golden example
    Validação: pytest tests/test_agents.py + tests/test_new_agents.py

STEP 08: src/agents/proponent_agent.py    ← MODIFICAR
    Mudança: golden example injection no defend_artifact
    Validação: pytest tests/test_agents.py

STEP 09: src/planning/plan_generator.py   ← MODIFICAR
    Mudança: PLAN_TEMPLATE_V2 + consolidação de riscos
    Validação: pytest tests/test_pipeline.py

STEP 10: src/core/planner.py             ← MODIFICAR
    Mudança: DAG 7 tasks, routing security_reviewer,
    output_validator integration
    Validação: pytest tests/test_planner.py

STEP 11: src/core/controller.py           ← MODIFICAR
    Mudança: registro de SecurityReviewerAgent
    Validação: pytest tests/test_pipeline.py

STEP 12: src/models/ollama_provider.py    ← MODIFICAR
    Mudança: num_predict 800→1200 (direct mode)
    Validação: pytest tests/test_stream_handler.py

STEP 13: tests/test_output_validator.py   ← CRIAR
    Validação: pytest tests/test_output_validator.py

STEP 14: tests/test_security_reviewer.py  ← CRIAR
    Validação: pytest tests/test_security_reviewer.py

STEP 15: VALIDAÇÃO FINAL
    Comando: python -m pytest tests/ -v
    Critério: 100% passed
```

---

## 5. ARQUIVOS NÃO ALTERADOS

| Arquivo | Motivo |
|---|---|
| `src/models/model_provider.py` | Interface base preservada |
| `src/models/cloud_provider.py` | Mock preservado |
| `src/core/stream_handler.py` | Streaming intocado |
| `src/core/blackboard.py` | Estado intocado |
| `src/core/artifact_store.py` | Artefatos intocados |
| `src/config/settings.py` | Config intocada |
| `src/conversation/conversation_manager.py` | Deprecado, preservado |
| `src/cli/main.py` | Interface de terminal intocada |
| `src/debate/debate_engine.py` | Engine intocada (consome security_review via artifacts) |

---

## 6. INVARIANTES GARANTIDAS

1. **Contrato `generate(prompt, context, role) -> str` preservado** — Nenhum provider alterado
2. **Contrato de agentes existentes preservado** — `analyze()`, `propose()`, `generate_prd()`, `design_system()` mantêm assinaturas
3. **Blackboard/ArtifactStore intocados** — Schema de persistência preservado
4. **Backward compatibility total** — `direct_mode` e `think` mantêm defaults
5. **Zero dependências externas novas** — Apenas constantes string e regex
6. **Novo agente é ADITIVO** — `SecurityReviewerAgent` pode ser removido deletando o arquivo e revertendo TASK_04b da DAG
7. **Templates V2 são OPCIONAIS** — Se um agente não conseguir preencher todas as seções, o `OutputValidator` loga warning mas não bloqueia o pipeline

---

## 7. MATRIZ DE RASTREABILIDADE — FASE 4

| Requisito | Componente | Arquivo | Método | Teste | Critério |
|---|---|---|---|---|---|
| System prompts com "Regras Invioláveis" | Todos os agentes | `*_agent.py` | `system_prompt` (property) | `test_new_agents::test_agents_direct_mode` | "REGRAS INVIOLÁVEIS" presente |
| PRD com MoSCoW + SMART + Riscos | ProductManagerAgent | `product_manager_agent.py` | `generate_prd()` | `test_new_agents::test_product_manager_agent` | Output contém "Prioridade (MoSCoW)" |
| Design com ADR + C4 + STRIDE ref | ArchitectAgent | `architect_agent.py` | `design_system()` | `test_new_agents::test_architect_agent` | Output contém "ADRs" |
| Review com scoring numérico | CriticAgent | `critic_agent.py` | `review_artifact()` | `test_new_agents::test_critic_review_artifact` | Output contém "quality_score" |
| Security Review STRIDE | SecurityReviewerAgent | `security_reviewer_agent.py` | `review_security()` | `test_security_reviewer::test_review_security` | Output contém "STRIDE" |
| Golden examples injetados | Todos os agentes de geração | `golden_examples.py` | N/A | `test_output_validator::test_example_fragments_valid` | Cada fragment contém "|---|" |
| Output validation pós-geração | Planner | `output_validator.py` | `validate()` | `test_output_validator::test_validate_complete_prd` | completeness_score >= 0.8 |
| DAG 7 tasks com security | Planner | `planner.py` | `load_default_dag()` | `test_planner::test_planner_dag_initialization` | len(dag) == 7 |
| num_predict 1200 | OllamaProvider | `ollama_provider.py` | `generate_with_thinking()` | `test_stream_handler::test_*` | provider.think==False → options contém 1200 |
| Templates V2 densificados | prompt_templates | `prompt_templates.py` | N/A | `test_prompt_quality::test_*_template_has_required_sections` | Seções presentes |

---

**Este blueprint foi estruturado para que a implementação seja determinística, incremental e reversível. Cada STEP pode ser implementado, testado e commitado independentemente. O rollback da Fase 4 consiste em reverter os agentes para system prompts da Fase 3.1 e remover TASK_04b da DAG — nenhum componente estrutural (Blackboard, ArtifactStore, StreamHandler) é tocado.**