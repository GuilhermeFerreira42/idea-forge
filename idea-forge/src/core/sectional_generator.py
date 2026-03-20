"""
sectional_generator.py — Gerador de artefatos por seções.

PROBLEMA RESOLVIDO:
Modelos locais (7-8B) com num_predict ≤ 1200 não conseguem produzir
artefatos densos com 7+ seções tabulares em uma única chamada.

SOLUÇÃO:
Quebrar a geração em N passes, cada um focado em 2-3 seções,
com template+example específico por pass. Depois concatenar.
"""
import sys
import re
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
        """
        if passes is None:
            passes = self._get_default_passes(artifact_type)
        
        if not passes:
            return ""
        
        accumulated_output = ""
        pass_results = []
        
        for i, section_pass in enumerate(passes):
            sys.stdout.write(
                f"\n{ANSIStyle.CYAN}  [PASS {i+1}/{len(passes)}] "
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
                role=self._get_role(artifact_type),
                max_tokens=section_pass.max_output_tokens
            )
            
            # Limpar resultado
            result = self._clean_pass_output(result)
            
            # Validar se o pass gerou o que devia. Se não, tenta um retry único.
            if not any(section in result for section in section_pass.sections):
                sys.stdout.write(
                    f"{ANSIStyle.YELLOW}    ⚠ Retry: pass {i+1} não gerou seções esperadas"
                    f"{ANSIStyle.RESET}\n"
                )
                sys.stdout.flush()
                
                retry_prompt = prompt + (
                    "\n\nATENÇÃO: Sua resposta anterior não continha as seções solicitadas. "
                    "Comece IMEDIATAMENTE com ## heading. Nenhum texto antes do heading."
                )
                result = self.provider.generate(
                    prompt=retry_prompt, 
                    role=self._get_role(artifact_type),
                    max_tokens=section_pass.max_output_tokens
                )
                result = self._clean_pass_output(result)

            # Validar pass individual (apenas log)
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
        
        system = (
            "Responda em Português. Formato: APENAS Markdown com tabelas e bullets.\n"
            "PROIBIDO: introduções, conclusões, meta-comentários, prosa.\n"
            "OBRIGATÓRIO: começar DIRETO com ## heading da primeira seção.\n"
        )
        
        if self.direct_mode:
            system += "Responda diretamente sem blocos <think>.\n"
        
        prompt = f"System: {system}\n\n"
        prompt += f"GERE EXATAMENTE ESTAS SEÇÕES:\n{section_pass.template}\n\n"
        
        if section_pass.example:
            prompt += f"REFERÊNCIA DE FORMATO:\n{section_pass.example}\n\n"
        
        prompt += f"PROJETO:\n{user_input[:800]}\n\n"
        
        if previous_output:
            summary = self._summarize_previous(previous_output, max_tokens=400)
            prompt += (
                f"SEÇÕES JÁ GERADAS (NÃO repita, use como referência):\n"
                f"{summary}\n\n"
            )
        
        if context:
            prompt += f"CONTEXTO ADICIONAL:\n{context[:600]}\n\n"
        
        prompt += (
            f"{section_pass.instruction}\n"
            f"[Pass {pass_number}/{total_passes}]"
        )
        
        return prompt
    
    def _summarize_previous(self, text: str, max_tokens: int = 400) -> str:
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
                summary_lines.append(stripped[:120])
                current_chars += min(len(stripped), 120)
                capture_next = False
            
            if current_chars >= chars_budget:
                break
        
        return '\n'.join(summary_lines)
    
    def _clean_pass_output(self, text: str) -> str:
        """Remove ruído do output de um pass individual."""
        lines = text.split('\n')
        start_idx = 0
        
        noise_prefixes = [
            'certamente', 'com certeza', 'aqui está', 'entendido',
            'com base', 'analisando', 'como solicitado', 'segue',
            'okay', "let's", 'i will', 'based on', 'here is', 'sure',
            'entendi', 'de acordo', '[pass'
        ]
        
        for i, line in enumerate(lines[:8]):
            stripped = line.strip().lower()
            if not stripped:
                start_idx = i + 1
                continue
            if any(stripped.startswith(p) for p in noise_prefixes):
                start_idx = i + 1
            else:
                break
        
        result = '\n'.join(lines[start_idx:]).strip()
        
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
        roles = {
            "prd": "product_manager",
            "system_design": "architect",
            "review": "critic",
            "security_review": "security_reviewer",
            "plan": "planner",
        }
        return roles.get(artifact_type, "user")
    
    def _get_default_passes(self, artifact_type: str) -> List[SectionPass]:
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
        ),
        instruction="Gere APENAS as seções Objetivo e Problema. Nada mais.",
        max_output_tokens=500,
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
            "| RNF-01 | Performance | ... | ... | ... |\n"
        ),
        example=(
            "| RF-01 | CRUD de tarefas | POST/GET/PUT/DELETE em /tasks retorna status correto | Must | Low |\n"
            "| RNF-01 | Performance | Resposta da API | Latência p95 | <200ms |\n"
        ),
        instruction="Gere Requisitos Funcionais (mín 5) e Não-Funcionais (mín 3).",
        max_output_tokens=900,
    ),
    SectionPass(
        pass_id="prd_p3",
        sections=["## Escopo MVP", "## Métricas de Sucesso"],
        template=(
            "## Escopo MVP\n"
            "**Inclui:** [lista com bullets]\n"
            "**NÃO inclui:** [lista com bullets]\n\n"
            "## Métricas de Sucesso (SMART)\n"
            "| Métrica | Specific | Measurable | Target | Prazo |\n"
            "|---|---|---|---|---|\n"
        ),
        example=(
            "**Inclui:**\n- RF-01, RF-02 — core CRUD\n\n**NÃO inclui:**\n- Notificações push (v2)\n"
        ),
        instruction="Gere Escopo MVP e Métricas. Referencie IDs RF-XX.",
        max_output_tokens=500,
    ),
    SectionPass(
        pass_id="prd_p4",
        sections=["## Dependências e Riscos", "## Constraints Técnicos"],
        template=(
            "## Dependências e Riscos\n"
            "| ID | Tipo | Descrição | Probabilidade | Impacto | Mitigação |\n"
            "|---|---|---|---|---|---|\n\n"
            "## Constraints Técnicos\n"
            "- Linguagem: [valor]\n"
            "- Banco: [valor]\n"
        ),
        example=(
            "| R-01 | Risco | Ollama offline | Alta | Crítico | Health check |\n"
        ),
        instruction="Gere Riscos e Constraints. Mínimo 3 riscos.",
        max_output_tokens=500,
    ),
]

DESIGN_PASSES = [
    SectionPass(
        pass_id="design_p1",
        sections=["## Arquitetura Geral", "## Tech Stack"],
        template=(
            "## Arquitetura Geral (C4 — Container Level)\n"
            "- Estilo: [ex: Monolito Modular]\n"
            "- containers: [lista]\n\n"
            "## Tech Stack\n"
            "| Camada | Tecnologia | Justificativa |\n"
            "|---|---|---|---|\n"
        ),
        example=(
            "| Backend | FastAPI | Async nativo |\n"
        ),
        instruction="Gere Arquitetura e Tech Stack.",
        max_output_tokens=600,
    ),
    SectionPass(
        pass_id="design_p2",
        sections=["## Módulos", "## Modelo de Dados"],
        template=(
            "## Módulos (C4 — Component Level)\n"
            "| Módulo | Responsabilidade | Interface |\n"
            "|---|---|---|---|\n\n"
            "## Modelo de Dados\n"
            "| Entidade | Atributos | Tipo | Relações |\n"
            "|---|---|---|---|---|\n"
        ),
        example=(
            "| AuthModule | Autenticação | REST /auth/* |\n"
        ),
        instruction="Gere Módulos e Modelo de Dados.",
        max_output_tokens=800,
    ),
    SectionPass(
        pass_id="design_p3",
        sections=["## Fluxo de Dados", "## ADRs", "## Riscos Técnicos"],
        template=(
            "## Fluxo de Dados\n"
            "1. [Ator] → [Ação] → [Resultado]\n\n"
            "## ADRs\n"
            "| ID | Decisão | Contexto |\n"
            "|---|---|---|---|\n\n"
            "## Riscos Técnicos\n"
            "| ID | Risco | Mitigação |\n"
            "|---|---|---|---|\n"
        ),
        example=(
            "1. Usuário → Login → JWT\n"
        ),
        instruction="Gere Fluxo de Dados, ADRs e Riscos Técnicos.",
        max_output_tokens=800,
    ),
]

PLAN_PASSES = [
    SectionPass(
        pass_id="plan_p1",
        sections=["## Arquitetura Sugerida", "## Módulos Core", "## Fases de Implementação"],
        template=(
            "## Arquitetura Sugerida\n- Estilo: [valor]\n\n"
            "## Módulos Core\n"
            "| Módulo | Prioridade | Estimativa |\n"
            "|---|---|---|---|\n\n"
            "## Fases de Implementação\n"
            "| Fase | Entregas | Riscos |\n"
            "|---|---|---|---|\n"
        ),
        example="",
        instruction="Gere Arquitetura, Módulos e Fases.",
        max_output_tokens=900,
    ),
    SectionPass(
        pass_id="plan_p2",
        sections=["## Dependências Técnicas", "## Riscos e Mitigações", "## Plano de Testes"],
        template=(
            "## Dependências Técnicas\n"
            "| Dependência | Propósito |\n"
            "|---|---|---|\n\n"
            "## Riscos e Mitigações\n"
            "| ID | Risco | Mitigação |\n"
            "|---|---|---|\n\n"
            "## Plano de Testes\n"
            "| Tipo | Escopo | Ferramenta |\n"
            "|---|---|---|---|\n"
        ),
        example="",
        instruction="Gere Dependências, Riscos e Plano de Testes.",
        max_output_tokens=700,
    ),
]
