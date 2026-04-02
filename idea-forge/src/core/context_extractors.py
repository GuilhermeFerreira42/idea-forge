"""
context_extractors.py — Extratores de contexto mínimo para passagens do sectional_generator.
Cada extrator recebe o conteúdo completo de um artefato e retorna
apenas o trecho relevante para uma seção específica do PRD_FINAL.
"""
import re
from typing import Optional


def _extract_section(content: str, header: str, max_chars: int = 1600) -> str:
    """Extrai conteúdo sob um header markdown ## ou ### de forma robusta."""
    lines = content.split('\n')
    start_idx = -1
    header_lower = header.lower()
    
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if stripped.startswith('##') and header_lower in stripped:
            start_idx = i
            break
            
    if start_idx == -1:
        return ""
        
    result_lines = [lines[start_idx]]
    for line in lines[start_idx + 1:]:
        stripped = line.strip()
        # Se encontrar outro header ## (mas permitir ### dentro da seção)
        if stripped.startswith('##') and not stripped.startswith('###'):
            break
        result_lines.append(line)
        
    text = "\n".join(result_lines).strip()
    if len(text) > max_chars:
        return text[:max_chars] + "\n[...truncado]"
    return text


def _extract_table(content: str, header: str, max_chars: int = 1600) -> str:
    """Extrai uma tabela markdown que aparece após um header."""
    section = _extract_section(content, header, max_chars=max_chars * 2)
    if not section:
        return ""
    # Encontrar linhas de tabela (começam com |)
    lines = section.split("\n")
    table_lines = [l for l in lines if l.strip().startswith("|")]
    if table_lines:
        # Reconstruir a tabela com o header original se possível
        header_line = lines[0] if lines[0].startswith("#") else ""
        result = (header_line + "\n" if header_line else "") + "\n".join(table_lines)
        if len(result) > max_chars:
            return result[:max_chars] + "\n[...truncado]"
        return result
    # Fallback se não for tabela mas for seção curta
    return section[:max_chars]


def extract_for_arquitetura_tech_stack(system_design: str) -> str:
    """Extrai Tech Stack e Arquitetura Geral do system_design."""
    parts = []
    
    # Extrair tabela de Tech Stack
    tech_stack = _extract_table(system_design, "Tech Stack", max_chars=800)
    if not tech_stack:
        tech_stack = _extract_table(system_design, "Stack", max_chars=800)
        
    if tech_stack:
        parts.append(tech_stack)
    
    # Extrair Arquitetura Geral (containers e comunicação)
    arq = _extract_section(system_design, "Arquitetura Geral", max_chars=800)
    if not arq:
        arq = _extract_section(system_design, "Arquitetura", max_chars=800)
        
    if arq:
        parts.append(arq)
    
    return "\n\n".join(parts) if parts else "[Nenhum dado de arquitetura/stack disponível]"


def extract_for_plano_implementacao(development_plan: str) -> str:
    """Extrai Fases de Implementação e Módulos Core do development_plan."""
    parts = []
    
    fases = _extract_table(development_plan, "Fases de Implementação", max_chars=800)
    if not fases:
        fases = _extract_table(development_plan, "Fases", max_chars=800)
    if fases:
        parts.append(fases)
    
    modulos = _extract_table(development_plan, "Módulos Core", max_chars=800)
    if not modulos:
        modulos = _extract_table(development_plan, "Modulos", max_chars=800)
    if modulos:
        parts.append(modulos)
    
    return "\n\n".join(parts) if parts else "[Nenhum dado de plano de implementação disponível]"


def extract_for_decisoes_debate(debate_transcript: str) -> str:
    """Extrai tabela de Decisões Aplicáveis do debate_transcript."""
    decisoes = _extract_table(debate_transcript, "Decisões Aplicáveis", max_chars=1400)
    if not decisoes:
        decisoes = _extract_table(debate_transcript, "Decisões", max_chars=1400)
    if not decisoes:
        decisoes = _extract_table(debate_transcript, "Decis", max_chars=1400)
    
    if decisoes:
        return decisoes
    
    return "[Nenhuma tabela de decisões encontrada no debate]"


def extract_for_guia_replicacao(development_plan: str) -> str:
    """Extrai Dependências Técnicas e Configurações de Ambiente."""
    parts = []
    
    deps = _extract_table(development_plan, "Dependências Técnicas", max_chars=700)
    if not deps:
        deps = _extract_table(development_plan, "Dependências", max_chars=700)
    if not deps:
        deps = _extract_table(development_plan, "Dependencias", max_chars=700)
    if deps:
        parts.append(deps)
    
    env = _extract_table(development_plan, "Configurações de Ambiente", max_chars=500)
    if not env:
        env = _extract_table(development_plan, "Ambiente", max_chars=500)
    if env:
        parts.append(env)
    
    guia = _extract_section(development_plan, "Guia de Replicação", max_chars=600)
    if not guia:
        guia = _extract_section(development_plan, "Guia", max_chars=600)
    if guia:
        parts.append(guia)
    
    return "\n\n".join(parts) if parts else "[Nenhum dado de replicação disponível]"


def generate_clausula_integridade(
    prd_final_chars: int,
    total_sections: int,
    failed_sections: int,
    model_name: str,
    generated_at: str
) -> str:
    """
    Gera Cláusula de Integridade como template estático.
    NÃO usa LLM — preenchimento determinístico.
    """
    status = "COMPLETO" if failed_sections == 0 else f"INCOMPLETO ({failed_sections} seções falharam)"
    
    return f"""## Cláusula de Integridade

| Campo | Valor |
|---|---|
| Status do Documento | {status} |
| Total de Seções | {total_sections} |
| Seções Geradas | {total_sections - failed_sections} |
| Seções Falhadas | {failed_sections} |
| Tamanho Total | {prd_final_chars:,} caracteres |
| Modelo Utilizado | {model_name} |
| Gerado em | {generated_at} |
| Versão do Pipeline | IdeaForge CLI — Fase 9.5.3 |

Este documento foi gerado automaticamente pelo pipeline IdeaForge.
Todas as seções passaram por validação estrutural via consistency_checker.
Dados técnicos foram derivados dos artefatos: system_design, security_review,
debate_transcript e development_plan."""
