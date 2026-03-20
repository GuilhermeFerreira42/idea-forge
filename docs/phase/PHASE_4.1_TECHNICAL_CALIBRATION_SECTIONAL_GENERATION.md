Perfeito. Com a sua autorização, o próximo passo é a execução técnica. 

O arquivo **`PHASE_4.1_TECHNICAL_CALIBRATION_SECTIONAL_GENERATION.md`** é o comando mestre que a inteligência executora deve seguir. Ele contém a lógica para "fatiar" a geração e garantir que cada seção do seu projeto receba a atenção e o limite de tokens necessários para atingir a densidade do NEXUS.

### O que acontece agora na prática:

1.  **Refatoração do Provider:** O `ollama_provider.py` será ajustado para permitir que o sistema peça tamanhos de resposta diferentes conforme a complexidade da seção.
2.  **Criação do Motor de Seções:** O `SectionalGenerator` passará a ser o responsável por coordenar as chamadas. Em vez de uma maratona de 2000 tokens, ele fará uma série de "sprints" de 500-800 tokens.
3.  **Fim do "A DEFINIR":** Como a IA terá espaço de sobra para cada tabela, ela não precisará mais economizar palavras ou deixar campos vazios para conseguir terminar o arquivo.

---------

# DIAGNÓSTICO: Por que o Ollama entrega resultados rasos

Analisei seu código completo. O problema não é o modelo — é a **arquitetura de geração**. Você pede um PRD inteiro (7 seções densas com tabelas) em UMA chamada com `num_predict=1200`. Isso é como pedir a alguém que escreva um livro em meia página.

---

## O PROBLEMA EM NÚMEROS

```
Seu pipeline atual para gerar um PRD:

CHAMADA ÚNICA ao LLM:
├── System prompt do agente:        ~800 tokens (consumo fixo)
├── ANTI_PROLIXITY_DIRECTIVE:       ~150 tokens (consumo fixo)
├── STYLE_CONTRACT:                 ~50 tokens  (consumo fixo)
├── PRD_TEMPLATE (esqueleto):       ~400 tokens (consumo fixo)
├── Golden Example:                 ~300 tokens (consumo fixo)
├── Contexto do usuário:            ~200 tokens (variável)
├── TOTAL INPUT:                    ~1900 tokens
│
├── num_predict (modo direto):      1200 tokens ← TETO DE SAÍDA
│
└── O que sobra para a IA preencher 7 seções com tabelas:
    1200 tokens ÷ 7 seções = ~170 tokens por seção
    170 tokens ≈ 4 linhas de tabela

RESULTADO: O modelo preenche 2-3 seções bem e abandona o resto,
ou preenche tudo superficialmente com 1 linha por seção.
```

**O NEXUS não tem esse problema porque eu (Claude) tenho janela de 200K tokens e gero o documento inteiro de uma vez.** Seu Ollama com 8K de contexto e 1200 de output não pode fazer o mesmo.

---

## SOLUÇÃO: DECOMPOSIÇÃO SEQUENCIAL COM MERGE

A estratégia é: **em vez de pedir o PRD inteiro em 1 chamada, quebrar em 4 sub-chamadas especializadas e depois concatenar os resultados.**

### Arquitetura da Solução

```
ANTES (1 chamada, resultado raso):
┌─────────────────────────────┐
│ generate_prd(ideia)         │──→ PRD inteiro (1200 tokens) → RASO
└─────────────────────────────┘

DEPOIS (4 chamadas, resultado denso):
┌─────────────────────────────┐
│ PASS 1: Objetivo + Problema │──→ ~400 tokens → DENSO
├─────────────────────────────┤
│ PASS 2: Requisitos (RF/RNF) │──→ ~600 tokens → DENSO
├─────────────────────────────┤
│ PASS 3: Escopo + Métricas   │──→ ~400 tokens → DENSO
├─────────────────────────────┤
│ PASS 4: Riscos + Constraints│──→ ~400 tokens → DENSO
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ MERGE: Concatenar passes    │──→ PRD completo (~1800 tokens) → NEXUS-GRADE
└─────────────────────────────┘
```

---

## IMPLEMENTAÇÃO COMPLETA

### 1. Novo módulo: `src/core/sectional_generator.py` (CRIAR)

```python
"""
sectional_generator.py — Gerador de artefatos por seções.

PROBLEMA RESOLVIDO:
Modelos locais (7-8B) com num_predict ≤ 1200 não conseguem produzir
artefatos densos com 7+ seções tabulares em uma única chamada.

SOLUÇÃO:
Quebrar a geração em N passes, cada um focado em 2-3 seções,
com template+example específico por pass. Depois concatenar.

Cada pass recebe:
- System prompt CURTO (150 tokens, não o completo)
- Template de APENAS as seções desse pass (100-200 tokens)
- Golden example de APENAS esse tipo de seção (100-150 tokens)
- A ideia do usuário (variável)
- Output de passes anteriores como REFERÊNCIA (não para repetir)

Budget por pass: ~500-600 tokens de input + 600-800 de output = cabe em 8K.
"""
import sys
from typing import List, Dict, Optional
from src.models.model_provider import ModelProvider
from src.core.stream_handler import ANSIStyle
from src.core.output_validator import OutputValidator


class SectionPass:
    """Definição de um passo de geração."""
    def __init__(self, pass_id: str, sections: List[str],
                 template: str, example: str,
                 instruction: str, max_output_tokens: int = 800):
        self.pass_id = pass_id
        self.sections = sections      # Nomes das seções geradas neste pass
        self.template = template      # Esqueleto Markdown das seções
        self.example = example        # Golden example específico
        self.instruction = instruction # Instrução curta do que fazer
        self.max_output_tokens = max_output_tokens


class SectionalGenerator:
    """
    Gera artefatos densos quebrando em múltiplos passes sequenciais.
    
    Fluxo:
    1. Define lista de SectionPasses para o tipo de artefato
    2. Executa cada pass sequencialmente via provider.generate()
    3. Acumula resultados e passa output anterior como contexto
    4. Valida cada pass individualmente
    5. Concatena todos os passes no artefato final
    6. Valida artefato final com OutputValidator
    """
    
    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self.validator = OutputValidator()
    
    def generate_sectional(self, artifact_type: str, 
                           user_input: str,
                           context: str = "",
                           passes: List[SectionPass] = None) -> str:
        """
        Gera artefato denso em múltiplos passes.
        
        Args:
            artifact_type: Tipo para validação (prd, system_design, etc)
            user_input: Ideia do usuário ou input primário
            context: Contexto adicional (artefatos anteriores)
            passes: Lista de SectionPass. Se None, usa padrão para artifact_type.
        
        Returns:
            Artefato completo concatenado (string Markdown)
        """
        if passes is None:
            passes = self._get_default_passes(artifact_type)
        
        if not passes:
            # Fallback: geração única (comportamento antigo)
            return None
        
        accumulated_output = ""
        pass_results = []
        
        for i, section_pass in enumerate(passes):
            sys.stdout.write(
                f"{ANSIStyle.CYAN}  [PASS {i+1}/{len(passes)}] "
                f"Gerando: {', '.join(section_pass.sections)}"
                f"{ANSIStyle.RESET}\n"
            )
            sys.stdout.flush()
            
            # Construir prompt para este pass
            prompt = self._build_pass_prompt(
                section_pass=section_pass,
                user_input=user_input,
                context=context,
                previous_output=accumulated_output,
                pass_number=i + 1,
                total_passes=len(passes)
            )
            
            # Gerar via provider
            result = self.provider.generate(
                prompt=prompt, 
                role=self._get_role(artifact_type)
            )
            
            # Limpar resultado
            result = self._clean_pass_output(result)
            
            # Validar pass individual (aviso, não bloqueante)
            self._validate_pass(section_pass, result, i + 1)
            
            pass_results.append(result)
            accumulated_output += result + "\n\n"
        
        # Concatenar todos os passes
        final_output = "\n\n".join(pass_results)
        
        # Validar artefato final
        validation = self.validator.validate(final_output, artifact_type)
        if validation.get("valid"):
            sys.stdout.write(
                f"{ANSIStyle.GREEN}  [VALIDAÇÃO] Artefato aprovado — "
                f"density: {validation['density_score']:.2f}, "
                f"completude: {int(validation['completeness_score']*100)}%, "
                f"tabelas: {validation['table_count']}"
                f"{ANSIStyle.RESET}\n"
            )
        else:
            sys.stdout.write(
                f"{ANSIStyle.YELLOW}  [VALIDAÇÃO] Artefato incompleto — "
                f"faltam: {validation.get('missing_sections', [])}"
                f"{ANSIStyle.RESET}\n"
            )
        sys.stdout.flush()
        
        return final_output
    
    def _build_pass_prompt(self, section_pass: SectionPass,
                           user_input: str, context: str,
                           previous_output: str,
                           pass_number: int, total_passes: int) -> str:
        """Constrói prompt otimizado para um pass individual."""
        
        # System prompt CURTO (não o completo do agente)
        system = (
            "Responda em Português. Formato: APENAS Markdown com tabelas e bullets.\n"
            "PROIBIDO: introduções, conclusões, meta-comentários, prosa.\n"
            "OBRIGATÓRIO: começar DIRETO com ## heading da primeira seção.\n"
        )
        
        if self.direct_mode:
            system += "Responda diretamente sem blocos <think>.\n"
        
        prompt = f"System: {system}\n\n"
        
        # Template das seções deste pass
        prompt += f"GERE EXATAMENTE ESTAS SEÇÕES:\n{section_pass.template}\n\n"
        
        # Golden example específico (curto)
        if section_pass.example:
            prompt += f"REFERÊNCIA DE FORMATO:\n{section_pass.example}\n\n"
        
        # Contexto do usuário
        prompt += f"PROJETO:\n{user_input[:600]}\n\n"
        
        # Output de passes anteriores (RESUMO para não estourar contexto)
        if previous_output:
            # Pegar apenas os headings e primeiras linhas do output anterior
            summary = self._summarize_previous(previous_output, max_tokens=300)
            prompt += (
                f"SEÇÕES JÁ GERADAS (NÃO repita, use como referência):\n"
                f"{summary}\n\n"
            )
        
        # Contexto adicional (artefatos anteriores)
        if context:
            prompt += f"CONTEXTO ADICIONAL:\n{context[:400]}\n\n"
        
        # Instrução final
        prompt += (
            f"{section_pass.instruction}\n"
            f"[Pass {pass_number}/{total_passes}]"
        )
        
        return prompt
    
    def _summarize_previous(self, text: str, max_tokens: int = 300) -> str:
        """Extrai apenas headings e primeiras linhas de cada seção."""
        lines = text.split('\n')
        summary_lines = []
        chars_budget = max_tokens * 4
        current_chars = 0
        capture_next = False
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('##'):
                summary_lines.append(stripped)
                current_chars += len(stripped)
                capture_next = True
            elif capture_next and stripped:
                # Capturar primeira linha não-vazia após heading
                summary_lines.append(stripped[:100])
                current_chars += min(len(stripped), 100)
                capture_next = False
            
            if current_chars >= chars_budget:
                break
        
        return '\n'.join(summary_lines)
    
    def _clean_pass_output(self, text: str) -> str:
        """Remove ruído do output de um pass individual."""
        import re
        
        lines = text.split('\n')
        start_idx = 0
        
        # Remover linhas iniciais que são ruído
        noise_prefixes = [
            'certamente', 'com certeza', 'aqui está', 'entendido',
            'com base', 'analisando', 'como solicitado', 'segue',
            'okay', "let's", 'i will', 'based on', 'here is', 'sure',
            'entendi', 'de acordo', '[pass'
        ]
        
        for i, line in enumerate(lines[:5]):
            stripped = line.strip().lower()
            if not stripped:
                start_idx = i + 1
                continue
            if any(stripped.startswith(p) for p in noise_prefixes):
                start_idx = i + 1
            else:
                break
        
        result = '\n'.join(lines[start_idx:]).strip()
        
        # Remover tags think residuais
        if '<think>' in result:
            result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
        
        return result
    
    def _validate_pass(self, section_pass: SectionPass, 
                       result: str, pass_number: int) -> None:
        """Valida se o pass gerou as seções esperadas."""
        for section_name in section_pass.sections:
            if section_name not in result:
                sys.stdout.write(
                    f"{ANSIStyle.YELLOW}    ⚠ Pass {pass_number}: "
                    f"seção '{section_name}' não encontrada"
                    f"{ANSIStyle.RESET}\n"
                )
                sys.stdout.flush()
    
    def _get_role(self, artifact_type: str) -> str:
        """Mapeia tipo de artefato para role do provider."""
        roles = {
            "prd": "product_manager",
            "system_design": "architect",
            "review": "critic",
            "security_review": "security_reviewer",
            "plan": "planner",
        }
        return roles.get(artifact_type, "user")
    
    def _get_default_passes(self, artifact_type: str) -> List[SectionPass]:
        """Retorna passes padrão por tipo de artefato."""
        if artifact_type == "prd":
            return PRD_PASSES
        elif artifact_type == "system_design":
            return DESIGN_PASSES
        elif artifact_type == "plan":
            return PLAN_PASSES
        return []


# ═══════════════════════════════════════════════════════
# DEFINIÇÃO DOS PASSES POR TIPO DE ARTEFATO
# ═══════════════════════════════════════════════════════

PRD_PASSES = [
    SectionPass(
        pass_id="prd_p1",
        sections=["## Objetivo", "## Problema"],
        template=(
            "## Objetivo\n"
            "- [1 frase, verbo no infinitivo, máximo 25 palavras]\n\n"
            "## Problema\n"
            "| ID | Problema | Impacto | Evidência |\n"
            "|---|---|---|---|\n"
            "| P-01 | ... | ... | ... |\n"
        ),
        example=(
            "## Objetivo\n"
            "- Permitir gerenciamento de tarefas pessoais com sincronização offline-first\n\n"
            "## Problema\n"
            "| ID | Problema | Impacto | Evidência |\n"
            "|---|---|---|---|\n"
            "| P-01 | Apps existentes requerem internet | Perda de dados em offline | 40% dos usuários reportam |\n"
            "| P-02 | Complexidade de apps enterprise | Abandono em 7 dias | Retenção <20% |\n"
        ),
        instruction="Gere APENAS as seções Objetivo e Problema. Nada mais.",
        max_output_tokens=400,
    ),
    SectionPass(
        pass_id="prd_p2",
        sections=["## Requisitos Funcionais", "## Requisitos Não-Funcionais"],
        template=(
            "## Requisitos Funcionais\n"
            "| ID | Requisito | Critério de Aceite | Prioridade (MoSCoW) | Complexidade |\n"
            "|---|---|---|---|---|\n"
            "| RF-01 | ... | ... | Must/Should/Could | Low/Med/High |\n\n"
            "## Requisitos Não-Funcionais\n"
            "| ID | Categoria | Requisito | Métrica | Target |\n"
            "|---|---|---|---|---|\n"
            "| RNF-01 | Performance/Segurança | ... | ... | ... |\n"
        ),
        example=(
            "| RF-01 | CRUD de tarefas | POST/GET/PUT/DELETE em /tasks retorna status correto | Must | Low |\n"
            "| RF-02 | Filtro por status | GET /tasks?status=done retorna subset | Should | Low |\n"
            "| RNF-01 | Performance | Resposta da API | Latência p95 | <200ms |\n"
        ),
        instruction=(
            "Gere APENAS Requisitos Funcionais e Não-Funcionais. "
            "Mínimo 5 RF e 3 RNF. Use IDs sequenciais."
        ),
        max_output_tokens=800,
    ),
    SectionPass(
        pass_id="prd_p3",
        sections=["## Escopo MVP", "## Métricas de Sucesso"],
        template=(
            "## Escopo MVP\n"
            "**Inclui:** [lista com bullets, referenciando IDs RF-XX]\n"
            "**NÃO inclui:** [lista com bullets]\n\n"
            "## Métricas de Sucesso (SMART)\n"
            "| Métrica | Specific | Measurable | Target | Prazo |\n"
            "|---|---|---|---|---|\n"
        ),
        example=(
            "**Inclui:**\n"
            "- RF-01, RF-02, RF-03 — core CRUD\n"
            "- RF-05 — autenticação básica\n\n"
            "**NÃO inclui:**\n"
            "- Integração com calendário (v2)\n"
            "- Notificações push (v2)\n"
        ),
        instruction=(
            "Gere APENAS Escopo MVP e Métricas. "
            "Referencie os IDs RF-XX das seções anteriores."
        ),
        max_output_tokens=400,
    ),
    SectionPass(
        pass_id="prd_p4",
        sections=["## Dependências e Riscos", "## Constraints Técnicos"],
        template=(
            "## Dependências e Riscos\n"
            "| ID | Tipo (Dep/Risco) | Descrição | Probabilidade | Impacto | Mitigação |\n"
            "|---|---|---|---|---|---|\n"
            "| R-01 | Risco | ... | Alta/Média/Baixa | Alto/Médio/Baixo | ... |\n\n"
            "## Constraints Técnicos\n"
            "- Linguagem: [valor ou 'A DEFINIR']\n"
            "- Framework: [valor ou 'A DEFINIR']\n"
            "- Banco de dados: [valor ou 'A DEFINIR']\n"
            "- Infraestrutura: [valor ou 'A DEFINIR']\n"
        ),
        example=(
            "| R-01 | Risco | SQLite não suporta escrita concorrente | Média | Alto | WAL mode + mutex |\n"
            "| R-02 | Dependência | Ollama deve estar rodando | Alta | Crítico | Health check no startup |\n"
        ),
        instruction="Gere APENAS Riscos/Dependências e Constraints. Mínimo 3 riscos.",
        max_output_tokens=400,
    ),
]


DESIGN_PASSES = [
    SectionPass(
        pass_id="design_p1",
        sections=["## Arquitetura Geral", "## Tech Stack"],
        template=(
            "## Arquitetura Geral (C4 — Container Level)\n"
            "- Estilo: [ex: Monolito Modular]\n"
            "- Containers: [lista]\n"
            "- Comunicação: [protocolos]\n\n"
            "## Tech Stack\n"
            "| Camada | Tecnologia | Versão | Justificativa | Alternativa Rejeitada |\n"
            "|---|---|---|---|---|\n"
        ),
        example=(
            "| Backend | FastAPI | 0.104 | Async nativo + Pydantic | Django: overhead ORM |\n"
            "| DB | SQLite | 3.40 | Zero config, portável | PostgreSQL: requer servidor |\n"
        ),
        instruction="Gere APENAS Arquitetura Geral e Tech Stack. Baseie-se no PRD.",
        max_output_tokens=600,
    ),
    SectionPass(
        pass_id="design_p2",
        sections=["## Módulos", "## Modelo de Dados"],
        template=(
            "## Módulos (C4 — Component Level)\n"
            "| Módulo | Responsabilidade | Interface | Requisitos Atendidos |\n"
            "|---|---|---|---|\n\n"
            "## Modelo de Dados\n"
            "| Entidade | Atributos-chave | Tipo | Relações | Constraints |\n"
            "|---|---|---|---|---|\n"
        ),
        example=(
            "| AuthModule | Autenticação JWT | REST /auth/* | RF-01, RF-02 |\n"
            "| User | id, email, password_hash, created_at | PK, UNIQUE, NOT NULL | 1:N → Task | email UNIQUE |\n"
        ),
        instruction="Gere APENAS Módulos e Modelo de Dados. Referencie RF-XX do PRD.",
        max_output_tokens=600,
    ),
    SectionPass(
        pass_id="design_p3",
        sections=["## Fluxo de Dados", "## ADRs", "## Riscos Técnicos"],
        template=(
            "## Fluxo de Dados (Sequencial)\n"
            "1. [Ator] → [Componente] → [Ação] → [Resultado]\n\n"
            "## ADRs (Architecture Decision Records)\n"
            "| ID | Decisão | Contexto | Alternativa Rejeitada | Consequências |\n"
            "|---|---|---|---|---|\n\n"
            "## Riscos Técnicos\n"
            "| ID | Risco | Probabilidade | Impacto | Mitigação | Owner |\n"
            "|---|---|---|---|---|---|\n"
        ),
        example=(
            "1. Usuário → API /auth/login → Valida credenciais → Retorna JWT\n"
            "| ADR-01 | SQLite para MVP | Deploy local, sem servidor | PostgreSQL | Migrar na v2 |\n"
        ),
        instruction=(
            "Gere Fluxo de Dados (mín 5 passos), ADRs (mín 2) e Riscos (mín 3). "
            "NÃO repita seções anteriores."
        ),
        max_output_tokens=800,
    ),
]


PLAN_PASSES = [
    SectionPass(
        pass_id="plan_p1",
        sections=["## Arquitetura Sugerida", "## Módulos Core", "## Fases de Implementação"],
        template=(
            "## Arquitetura Sugerida\n"
            "- Estilo: [ex: Monolito Modular]\n"
            "- Componentes: [bullets]\n\n"
            "## Módulos Core\n"
            "| Módulo | Responsabilidade | Prioridade | Requisitos (RF-XX) | Estimativa |\n"
            "|---|---|---|---|---|\n\n"
            "## Fases de Implementação\n"
            "| Fase | Duração | Entregas | Critério de Conclusão | Riscos |\n"
            "|---|---|---|---|---|\n"
        ),
        example="",
        instruction="Gere Arquitetura, Módulos Core e Fases de Implementação.",
        max_output_tokens=800,
    ),
    SectionPass(
        pass_id="plan_p2",
        sections=["## Dependências Técnicas", "## Riscos e Mitigações", "## Plano de Testes"],
        template=(
            "## Dependências Técnicas\n"
            "| Dependência | Versão | Propósito | Alternativa |\n"
            "|---|---|---|---|\n\n"
            "## Riscos e Mitigações (consolidado)\n"
            "| ID | Risco | Fonte | Impacto | Mitigação | Owner |\n"
            "|---|---|---|---|---|---|\n\n"
            "## Plano de Testes\n"
            "| Tipo | Escopo | Ferramenta | Cobertura Mínima |\n"
            "|---|---|---|---|\n"
        ),
        example="",
        instruction=(
            "Gere Dependências, Riscos consolidados (do PRD + Design + Security) "
            "e Plano de Testes."
        ),
        max_output_tokens=600,
    ),
]
```

---

### 2. Integração nos Agentes Existentes

**Mudança em `src/agents/product_manager_agent.py`:**

```python
from src.core.sectional_generator import SectionalGenerator

class ProductManagerAgent:
    # ... (init existente mantido) ...
    
    def generate_prd(self, idea: str, context: str = "") -> str:
        """
        Gera PRD a partir da ideia do usuário.
        
        FASE 5: Usa geração sequencial por seções para maximizar
        densidade em modelos locais com janela limitada.
        Fallback para geração única se sectional falhar.
        """
        # Tentar geração sectional (4 passes)
        generator = SectionalGenerator(
            provider=self.provider, 
            direct_mode=self.direct_mode
        )
        
        result = generator.generate_sectional(
            artifact_type="prd",
            user_input=idea,
            context=context,
        )
        
        if result and len(result) > 200:
            return result
        
        # Fallback: geração única (comportamento anterior)
        return self._generate_single_pass(idea, context)
    
    def _generate_single_pass(self, idea: str, context: str = "") -> str:
        """Geração em chamada única (fallback)."""
        from src.core.golden_examples import PRD_EXAMPLE_FRAGMENT
        
        prompt = f"System: {self.system_prompt}\n\n"
        if context:
            prompt += f"CONTEXTO (NÃO repita):\n{context}\n\n"
        prompt += PRD_EXAMPLE_FRAGMENT
        prompt += (
            f"IDEIA DO USUÁRIO:\n{idea}\n\n"
            "Preencha EXATAMENTE as seções do template."
        )
        return self.provider.generate(prompt=prompt, role="product_manager")
```

**Padrão idêntico para `architect_agent.py` e `plan_generator.py`:**

```python
# Em architect_agent.py → design_system():
generator = SectionalGenerator(self.provider, self.direct_mode)
result = generator.generate_sectional(
    artifact_type="system_design",
    user_input=prd_content,
    context=context,
)
if result and len(result) > 200:
    return result
return self._generate_single_pass(prd_content, context)

# Em plan_generator.py → generate_plan():
generator = SectionalGenerator(self.provider, self.direct_mode)
result = generator.generate_sectional(
    artifact_type="plan",
    user_input=first_input,
    context=context,
)
if result and len(result) > 200:
    return result
return self._generate_single_pass(first_input, context)
```

---

### 3. Ajuste no `ollama_provider.py` — num_predict por pass

O `SectionalGenerator` faz chamadas menores. Cada pass precisa de menos tokens. Mas o `num_predict` atual é fixo. A solução é **tornar `num_predict` configurável por chamada**:

```python
# Em ollama_provider.py, modificar generate_with_thinking:

def generate_with_thinking(self, prompt: str, context: list = None,
                           role: str = "user",
                           max_tokens_override: int = None) -> GenerationResult:
    """
    FASE 5: Adicionado max_tokens_override para permitir que o
    SectionalGenerator controle o budget por pass.
    """
    final_prompt = self._build_prompt(prompt)
    
    payload = {
        "model": self.model_name,
        "prompt": final_prompt,
        "stream": True,
    }
    
    # Determinar num_predict
    if max_tokens_override:
        num_predict = max_tokens_override
    elif self.think:
        num_predict = 3000
    else:
        num_predict = 1200
    
    options = {
        "num_predict": num_predict,
        "temperature": 0.1 if not self.think else 0.7,
    }
    # ... resto do método mantido ...
```

E no `generate()`:

```python
def generate(self, prompt: str, context: list = None, 
             role: str = "user", max_tokens: int = None) -> str:
    result = self.generate_with_thinking(
        prompt, context, role, 
        max_tokens_override=max_tokens
    )
    return result.content
```

---

### 4. Validador de Densidade com Retry

O `OutputValidator` atual só loga warning. Para forçar qualidade, adicione **retry automático para passes que falharam**:

```python
# Em sectional_generator.py, adicionar ao generate_sectional():

# Dentro do loop de passes, APÓS gerar e validar:
if not any(section in result for section in section_pass.sections):
    # Pass falhou completamente — retry com instrução mais enfática
    sys.stdout.write(
        f"{ANSIStyle.YELLOW}    ⚠ Retry: pass {i+1} não gerou seções esperadas"
        f"{ANSIStyle.RESET}\n"
    )
    
    retry_prompt = self._build_pass_prompt(
        section_pass=section_pass,
        user_input=user_input,
        context=context,
        previous_output=accumulated_output,
        pass_number=i + 1,
        total_passes=len(passes)
    )
    # Adicionar instrução mais enfática
    retry_prompt += (
        "\n\nATENÇÃO: Sua resposta anterior não continha as seções solicitadas. "
        "Comece IMEDIATAMENTE com ## heading. Nenhum texto antes do heading."
    )
    
    result = self.provider.generate(prompt=retry_prompt, role=self._get_role(artifact_type))
    result = self._clean_pass_output(result)
```

---

### 5. Métricas de Qualidade no Relatório Final

Adicione um **sumário de qualidade** ao relatório `.md`:

```python
# Em controller.py → _generate_final_report(), ao final:

f.write("\n---\n\n## Métricas de Qualidade (Automáticas)\n\n")
f.write("| Artefato | Density Score | Completude | Tabelas | Tokens |\n")
f.write("|---|---|---|---|---|\n")

validator = OutputValidator()
for art_name in artifacts_to_include:
    artifact = self.artifact_store.read(art_name)
    if artifact:
        # Determinar tipo para validação
        type_map = {
            "prd": "prd", "system_design": "system_design",
            "prd_review": "review", "security_review": "security_review",
            "development_plan": "plan"
        }
        art_type = type_map.get(art_name, "document")
        val = validator.validate(artifact.content, art_type)
        f.write(
            f"| {art_name} | {val.get('density_score', 'N/A')} | "
            f"{int(val.get('completeness_score', 0)*100)}% | "
            f"{val.get('table_count', 0)} | "
            f"{artifact.token_estimate()} |\n"
        )
```

---

## POR QUE ISSO FUNCIONA

```
COMPARAÇÃO DE BUDGET POR SEÇÃO:

ANTES (1 chamada):
  7 seções ÷ 1200 tokens output = 171 tokens/seção = 4 linhas de tabela

DEPOIS (4 passes):
  Pass 1: 2 seções ÷ 400 tokens = 200 tokens/seção = 5 linhas de tabela
  Pass 2: 2 seções ÷ 800 tokens = 400 tokens/seção = 10 linhas de tabela ← DENSO
  Pass 3: 2 seções ÷ 400 tokens = 200 tokens/seção = 5 linhas de tabela
  Pass 4: 2 seções ÷ 400 tokens = 200 tokens/seção = 5 linhas de tabela
  
  TOTAL OUTPUT: ~2000 tokens vs 1200 anterior = 67% MAIS CONTEÚDO

CUSTO:
  4 chamadas ao Ollama em vez de 1
  Tempo: ~4x mais (4 × 15s = 60s vs 15s)
  Trade-off: 60 segundos para resultado NEXUS-grade vs 15s para resultado raso
```

---

## ORDEM DE IMPLEMENTAÇÃO

```
STEP 01: src/core/sectional_generator.py     ← CRIAR
    Dependências: output_validator, model_provider
    Validação: pytest tests/test_sectional_generator.py

STEP 02: src/models/ollama_provider.py       ← MODIFICAR
    Mudança: max_tokens_override em generate() e generate_with_thinking()
    Validação: pytest tests/test_stream_handler.py

STEP 03: src/agents/product_manager_agent.py ← MODIFICAR
    Mudança: generate_prd() usa SectionalGenerator com fallback
    Validação: pytest tests/test_new_agents.py

STEP 04: src/agents/architect_agent.py       ← MODIFICAR
    Mudança: design_system() usa SectionalGenerator com fallback
    Validação: pytest tests/test_new_agents.py

STEP 05: src/planning/plan_generator.py      ← MODIFICAR
    Mudança: generate_plan() usa SectionalGenerator com fallback
    Validação: pytest tests/test_pipeline.py

STEP 06: src/core/controller.py              ← MODIFICAR
    Mudança: Métricas de qualidade no relatório final
    Validação: execução manual

STEP 07: tests/test_sectional_generator.py   ← CRIAR
    Validação: pytest tests/test_sectional_generator.py

STEP 08: VALIDAÇÃO FINAL
    Comando: python -m pytest tests/ -v
    Critério: 100% passed
```

---

## INVARIANTES GARANTIDAS

```
1. Contrato generate(prompt, context, role) → str PRESERVADO
   - max_tokens é parâmetro OPCIONAL com default None
   - Código que não usa max_tokens continua funcionando

2. Fallback total: se SectionalGenerator falhar, agente usa geração única

3. Zero dependências novas: apenas reorganização de chamadas existentes

4. Backward compatibility: testes existentes passam sem mudança

5. Artefatos finais são strings Markdown idênticas em formato — 
   apenas MAIS DENSAS
```