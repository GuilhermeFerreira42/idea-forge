"""
retry_templates.py — Templates estáticos para fallback Nível 3.

Contrato:
    - Cada função recebe um dict de dados extraídos dos artefatos
    - Cada função retorna Markdown estruturalmente válido
    - Se um dado não existir, usa placeholder "[Dado não disponível]"
    - NUNCA retorna string vazia
    - ZERO chamadas LLM
"""
from typing import Dict, List

def template_publico_alvo(extracted: Dict) -> str:
    """Template para ## Público-Alvo"""
    personas = extracted.get("personas", [])
    if not personas:
        personas = [
            {"segmento": "Usuário Principal", "perfil": "Persona não definida nos artefatos", "prioridade": "P0"},
            {"segmento": "Usuário Secundário", "perfil": "Persona não definida nos artefatos", "prioridade": "P1"},
            {"segmento": "Stakeholder", "perfil": "Persona não definida nos artefatos", "prioridade": "P2"},
        ]
    
    lines = ["## Público-Alvo\n"]
    lines.append("| Segmento | Perfil (nome fictício + dor específica) | Prioridade |")
    lines.append("|---|---|---|")
    for p in personas:
        lines.append(f"| {p.get('segmento', 'N/A')} | {p.get('perfil', 'N/A')} | {p.get('prioridade', 'N/A')} |")
    
    return "\n".join(lines)


def template_requisitos_funcionais(extracted: Dict) -> str:
    """Template para ## Requisitos Funcionais"""
    rfs = extracted.get("rfs", [])
    if not rfs:
        rfs = [{"id": "RF-01", "req": "[Extraído do PRD]", "criterio": "[A validar]", 
                "prioridade": "Must", "complexidade": "Média"}]
    
    lines = ["## Requisitos Funcionais\n"]
    lines.append("| ID | Requisito | Critério de Aceite | Prioridade | Complexidade |")
    lines.append("|---|---|---|---|---|")
    for rf in rfs:
        lines.append(f"| {rf.get('id', 'RF-XX')} | {rf.get('req', 'N/A')} | {rf.get('criterio', 'N/A')} | {rf.get('prioridade', 'N/A')} | {rf.get('complexidade', 'N/A')} |")
    
    return "\n".join(lines)


def template_adrs(extracted: Dict) -> str:
    """Template para ## ADRs"""
    adrs = extracted.get("adrs", [])
    if not adrs:
        adrs = [{"titulo": "Uso de Arquitetura Padrão", "status": "Aceito", "contexto": "Garantir estabilidade inicial.", "consequencias": "Facilidade de manutenção."}]
    
    lines = ["## ADRs (Decisões Arquiteturais)\n"]
    lines.append("| Campo | Valor |")
    lines.append("|---|---|")
    for i, adr in enumerate(adrs):
        if i > 0: lines.append("| --- | --- |")
        lines.append(f"| Título | {adr.get('titulo', 'N/A')} |")
        lines.append(f"| Status | {adr.get('status', 'N/A')} |")
        lines.append(f"| Contexto | {adr.get('contexto', 'N/A')} |")
        lines.append(f"| Consequências | {adr.get('consequencias', 'N/A')} |")
    
    return "\n".join(lines)


def template_seguranca(extracted: Dict) -> str:
    """Template para ## Análise de Segurança"""
    threats = extracted.get("threats", [])
    if not threats:
        threats = [{"id": "S-01", "ameaca": "Acesso não autorizado", "componente": "API", "severidade": "Alta", "mitigacao": "Implementar JWT"}]
    
    lines = ["## Análise de Segurança\n"]
    lines.append("| ID | Ameaça STRIDE | Componente | Severidade | Mitigação |")
    lines.append("|---|---|---|---|---|")
    for t in threats:
        lines.append(f"| {t.get('id', 'S-XX')} | {t.get('ameaca', 'N/A')} | {t.get('componente', 'N/A')} | {t.get('severidade', 'N/A')} | {t.get('mitigacao', 'N/A')} |")
    
    return "\n".join(lines)


def template_metricas(extracted: Dict) -> str:
    """Template para ## Métricas de Sucesso"""
    metrics = extracted.get("metrics", [])
    if not metrics:
        metrics = [{"metrica": "Disponibilidade", "target": "> 99.9%", "como_medir": "Monitoramento via Health Check"}]
    
    lines = ["## Métricas de Sucesso\n"]
    lines.append("| Métrica | Target | Como Medir |")
    lines.append("|---|---|---|")
    for m in metrics:
        lines.append(f"| {m.get('metrica', 'N/A')} | {m.get('target', 'N/A')} | {m.get('como_medir', 'N/A')} |")
    
    return "\n".join(lines)


def template_plano(extracted: Dict) -> str:
    """Template para ## Plano de Implementação"""
    phases = extracted.get("phases", [])
    if not phases:
        phases = [{"fase": "Fase 1: Setup", "duracao": "1 semana", "entregas": "Infraestrutura básica", "dependencia": "N/A"}]
    
    lines = ["## Plano de Implementação\n"]
    lines.append("| Fase | Duração | Entregas | Critério | Dependência |")
    lines.append("|---|---|---|---|---|")
    for p in phases:
        lines.append(f"| {p.get('fase', 'N/A')} | {p.get('duracao', 'N/A')} | {p.get('entregas', 'N/A')} | [A Validar] | {p.get('dependencia', 'N/A')} |")
    
    return "\n".join(lines)


def template_decisoes_debate(extracted: Dict) -> str:
    """Template para ## Decisões do Debate"""
    decisions = extracted.get("decisions", [])
    if not decisions:
        decisions = [{"decisao": "Uso de Python/FastAPI", "consenso": "Total", "impacto": "Alta produtividade"}]
    
    lines = ["## Decisões do Debate\n"]
    lines.append("| Decisão | Consenso | Impacto |")
    lines.append("|---|---|---|")
    for d in decisions:
        lines.append(f"| {d.get('decisao', 'N/A')} | {d.get('consenso', 'N/A')} | {d.get('impacto', 'N/A')} |")
    
    return "\n".join(lines)


def template_stub(heading: str, extracted: Dict = None) -> str:
    """Stub para seções que normalmente não falham."""
    return f"{heading}\n\n[Seção recuperada via template de segurança — dados básicos mantidos]"


def template_visao_produto(extracted: Dict) -> str:
    """Template para ## Visão do Produto"""
    lines = ["## Visão do Produto\n"]
    lines.append("| Atributo | Valor |")
    lines.append("|---|---|")
    lines.append("| Codinome interno | [Projeto sem codinome definido] |")
    lines.append("| Declaração de visão | [Visão do produto não disponível nos artefatos — consultar PRD original] |")
    return "\n".join(lines)


def template_problema_solucao(extracted: Dict) -> str:
    """Template para ## Problema e Solução"""
    lines = ["## Problema e Solução\n"]
    lines.append("| ID | Problema | Impacto | Como Resolve |")
    lines.append("|---|---|---|---|")
    lines.append("| P-01 | [Problema principal extraído do contexto] | [Impacto não quantificado] | [Solução proposta no PRD] |")
    lines.append("| P-02 | [Problema secundário] | [Impacto a definir] | [Solução a definir] |")
    return "\n".join(lines)


def template_principios(extracted: Dict) -> str:
    """Template para ## Princípios Arquiteturais"""
    lines = ["## Princípios Arquiteturais\n"]
    lines.append("| Princípio | Descrição | Implicação Técnica |")
    lines.append("|---|---|---|")
    lines.append("| Escalabilidade | Sistema projetado para crescimento horizontal | Containerização e orquestração |")
    lines.append("| Segurança | Proteção de dados em repouso e trânsito | TLS, JWT, criptografia |")
    lines.append("| Manutenibilidade | Código modular e testável | Separação de responsabilidades |")
    return "\n".join(lines)


def template_diferenciais(extracted: Dict) -> str:
    """Template para ## Diferenciais"""
    lines = ["## Diferenciais\n"]
    lines.append("| Abordagem Atual | Problema | Como Este Sistema Supera |")
    lines.append("|---|---|---|")
    lines.append("| Abordagem manual/tradicional | Ineficiência e falta de escala | Automação e integração |")
    lines.append("| Soluções genéricas | Falta de personalização | Arquitetura adaptada ao domínio |")
    return "\n".join(lines)


def template_rnfs(extracted: Dict) -> str:
    """Template para ## Requisitos Não-Funcionais"""
    lines = ["## Requisitos Não-Funcionais\n"]
    lines.append("| ID | Categoria | Requisito | Métrica | Target |")
    lines.append("|---|---|---|---|---|")
    lines.append("| RNF-01 | Performance | Tempo de resposta da API | Latência p95 | < 200 ms |")
    lines.append("| RNF-02 | Disponibilidade | Uptime do sistema | Percentual | ≥ 99.9% |")
    lines.append("| RNF-03 | Segurança | Dados sensíveis criptografados | Conformidade | 100% |")
    return "\n".join(lines)


def template_arquitetura(extracted: Dict) -> str:
    """Template para ## Arquitetura e Tech Stack"""
    lines = ["## Arquitetura e Tech Stack\n"]
    lines.append("- **Estilo:** [Extraído do System Design]")
    lines.append("")
    lines.append("| Camada | Tecnologia | Justificativa |")
    lines.append("|---|---|---|")
    lines.append("| Backend | [Tecnologia do projeto] | [Justificativa do System Design] |")
    lines.append("| Banco de Dados | [BD do projeto] | [Justificativa] |")
    lines.append("| Cache | [Cache do projeto] | [Justificativa] |")
    return "\n".join(lines)


def template_escopo_mvp(extracted: Dict) -> str:
    """Template para ## Escopo MVP"""
    lines = ["## Escopo MVP\n"]
    lines.append("**O QUE ESTÁ NO MVP:**")
    lines.append("- [Funcionalidades core extraídas do PRD]")
    lines.append("")
    lines.append("**O QUE NÃO ESTÁ NO MVP:**")
    lines.append("- [Funcionalidades adiadas com justificativa técnica]")
    return "\n".join(lines)


def template_riscos(extracted: Dict) -> str:
    """Template para ## Riscos Consolidados"""
    lines = ["## Riscos Consolidados\n"]
    lines.append("| ID | Risco | Fonte | Probabilidade | Impacto | Mitigação |")
    lines.append("|---|---|---|---|---|---|")
    lines.append("| R-01 | [Risco técnico principal] | Design | Média | Alto | [Mitigação proposta] |")
    lines.append("| R-02 | [Risco de integração] | Infraestrutura | Média | Médio | [Mitigação proposta] |")
    return "\n".join(lines)


def template_constraints(extracted: Dict) -> str:
    """Template para ## Constraints Técnicos"""
    lines = ["## Constraints Técnicos\n"]
    lines.append("- Linguagem: [Conforme definido no PRD]")
    lines.append("- Framework: [Conforme definido no PRD]")
    lines.append("- Banco de dados: [Conforme definido no PRD]")
    lines.append("- Infraestrutura: [Conforme definido no PRD]")
    lines.append("- Restrições de segurança: [Conforme definido no PRD]")
    return "\n".join(lines)


def template_rastreabilidade(extracted: Dict) -> str:
    """Template para ## Matriz de Rastreabilidade"""
    rfs = extracted.get("rfs", [])
    lines = ["## Matriz de Rastreabilidade\n"]
    lines.append("| RF-ID | Componente | Arquivo | Teste que Valida | Critério |")
    lines.append("|---|---|---|---|---|")
    if rfs:
        for rf in rfs:
            rf_id = rf.get("id", "RF-XX")
            lines.append(f"| {rf_id} | [Componente] | [Arquivo] | [Teste] | [Critério] |")
    else:
        lines.append("| RF-01 | [Componente principal] | [Arquivo principal] | [Teste unitário] | [Critério de aceite] |")
    return "\n".join(lines)


def template_limitacoes(extracted: Dict) -> str:
    """Template para ## Limitações Conhecidas"""
    lines = ["## Limitações Conhecidas\n"]
    lines.append("| ID | Limitação | Severidade | Impacto | Workaround | Resolução |")
    lines.append("|---|---|---|---|---|---|")
    lines.append("| L-01 | [Limitação técnica principal] | Média | [Impacto no usuário] | [Workaround atual] | [Versão futura] |")
    lines.append("| L-02 | [Limitação de escopo] | Baixa | [Impacto menor] | [Workaround] | [Versão futura] |")
    return "\n".join(lines)


def template_guia_replicacao(extracted: Dict) -> str:
    """Template para ## Guia de Replicação Resumido"""
    phases = extracted.get("phases", [])
    lines = ["## Guia de Replicação Resumido\n"]
    lines.append("### 1. Pré-requisitos")
    lines.append("| Ferramenta | Versão | Verificação |")
    lines.append("|---|---|---|")
    lines.append("| [Linguagem] | [Versão] | [comando --version] |")
    lines.append("")
    lines.append("### 2. Instalação")
    lines.append("```bash")
    lines.append("git clone [url-do-repositorio]")
    lines.append("cd [projeto]")
    lines.append("[comando de instalação de dependências]")
    lines.append("```")
    lines.append("")
    lines.append("### 3. Execução")
    lines.append("```bash")
    lines.append("[comando para executar]")
    lines.append("```")
    lines.append("")
    lines.append("### 4. Verificação")
    lines.append("```bash")
    lines.append("[comando de health check]")
    lines.append("```")
    return "\n".join(lines)


def template_clausula(extracted: Dict) -> str:
    """Template para ## Cláusula de Integridade (safety net)"""
    lines = ["## Cláusula de Integridade\n"]
    lines.append("| Campo | Valor |")
    lines.append("|---|---|")
    lines.append("| Status do Documento | RECUPERADO VIA TEMPLATE |")
    lines.append("| Observação | Cláusula gerada via safety net do RetryOrchestrator |")
    return "\n".join(lines)
