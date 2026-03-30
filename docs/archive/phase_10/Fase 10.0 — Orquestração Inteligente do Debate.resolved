# Fase 10.0 — Orquestração Inteligente do Debate

## Implementação Completa

---

## 1. Novo Arquivo: `src/debate/debate_state_tracker.py`

```python
"""
debate_state_tracker.py — Rastreador de estado de issues entre rodadas de debate.

FASE 10.0:
Responsabilidade:
    - Manter registro de issues levantados pelo Critic entre rodadas
    - Rastrear status: OPEN → RESOLVED | ACCEPTED | DEFERRED
    - Fornecer contexto estruturado para Critic (focar em OPEN) e Proponent (responder OPEN)
    - Produzir sumário para o Consolidador (TASK_07)

Contrato:
    - 100% programático — zero chamadas LLM
    - Agnóstico ao modelo — parseia texto via regex, não depende de JSON
    - Se parser falhar, degrada graciosamente (lista vazia, debate continua)
    - Interno ao DebateEngine — nenhum outro módulo o acessa diretamente

NÃO contém lógica de negócio de geração. Apenas rastreia estado.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class IssueRecord:
    """Registro imutável de um issue levantado durante o debate."""
    issue_id: str                           # "ISS-01", "ISS-02", etc.
    severity: str                           # "HIGH" | "MED" | "LOW"
    category: str                           # "SECURITY" | "CORRECTNESS" | etc.
    description: str                        # Descrição curta do problema
    status: str = "OPEN"                    # "OPEN" | "ACCEPTED" | "DEFERRED"
    round_raised: int = 0                   # Rodada em que foi levantado
    round_resolved: Optional[int] = None    # Rodada em que foi resolvido
    resolution: str = ""                    # Como foi resolvido


class DebateStateTracker:
    """
    Mantém estado de issues entre rodadas do debate.
    
    Ciclo de vida de um issue:
        1. Critic levanta issue → status OPEN
        2. Proponent aceita → status ACCEPTED
        3. Proponent defere → status DEFERRED
        4. Issue permanece OPEN se Proponent não endereça
    
    Heurísticas de parsing:
        - Issues: Extraídos de tabelas Markdown (| ISS-XX | SEV | CAT | ... |)
        - Fallback: Extraídos de bullets com keywords de severidade
        - Resoluções: Extraídas de seção "## Pontos Aceitos" do Proponent
    """
    
    def __init__(self):
        self.issues: Dict[str, IssueRecord] = {}
        self.current_round: int = 0
        self._next_auto_id: int = 1
        self._seen_descriptions: Set[str] = set()  # Dedup por descrição normalizada
    
    def extract_issues_from_critique(self, critique_text: str, round_num: int) -> List[str]:
        """
        Parseia texto do Critic e registra novos issues.
        
        Estratégia de parsing (em ordem de prioridade):
            1. Tabela Markdown com padrão | ISS-XX | HIGH/MED/LOW | CATEGORY | ... |
            2. Bullets com keywords de severidade (fallback)
        
        Args:
            critique_text: Resposta completa do Critic
            round_num: Número da rodada atual
            
        Returns:
            Lista de IDs dos issues NOVOS adicionados (exclui duplicatas)
        """
        if not critique_text:
            return []
        
        self.current_round = round_num
        new_ids = []
        
        # ═══ Estratégia 1: Tabela de issues ═══
        table_ids = self._parse_issue_table(critique_text, round_num)
        new_ids.extend(table_ids)
        
        # ═══ Estratégia 2: Fallback — bullets com severidade ═══
        if not table_ids:
            bullet_ids = self._parse_issue_bullets(critique_text, round_num)
            new_ids.extend(bullet_ids)
        
        return new_ids
    
    def extract_resolutions_from_defense(self, defense_text: str, round_num: int) -> List[str]:
        """
        Parseia texto do Proponent e marca issues como resolvidos.
        
        Busca na seção "## Pontos Aceitos" por referências a issue IDs
        ou descrições similares aos issues OPEN.
        
        Args:
            defense_text: Resposta completa do Proponent
            round_num: Número da rodada atual
            
        Returns:
            Lista de IDs dos issues resolvidos nesta rodada
        """
        if not defense_text:
            return []
        
        resolved_ids = []
        
        # Extrair bloco de "Pontos Aceitos"
        accepted_block = self._extract_section_content(defense_text, "## Pontos Aceitos")
        
        if not accepted_block:
            return []
        
        # Para cada issue OPEN, verificar se é mencionado
        for iss_id, record in self.issues.items():
            if record.status != "OPEN":
                continue
            
            matched = False
            match_reason = ""
            
            # Match 1: ID explícito (ex: "ISS-01" no texto)
            if iss_id.upper() in accepted_block.upper():
                matched = True
                match_reason = f"ID {iss_id} mencionado nos Pontos Aceitos"
            
            # Match 2: Descrição parcial (primeiras 40 chars normalizadas)
            if not matched:
                desc_normalized = self._normalize_text(record.description[:40])
                if desc_normalized and len(desc_normalized) > 15:
                    block_normalized = self._normalize_text(accepted_block)
                    if desc_normalized in block_normalized:
                        matched = True
                        match_reason = f"Descrição similar encontrada nos Pontos Aceitos"
            
            # Match 3: Categoria mencionada (ex: "segurança" ou "SECURITY")
            if not matched:
                category_lower = record.category.lower()
                category_pt = {
                    "security": "segurança",
                    "correctness": "correção",
                    "completeness": "completude",
                    "consistency": "consistência",
                    "feasibility": "viabilidade"
                }.get(category_lower, category_lower)
                
                block_lower = accepted_block.lower()
                if (category_lower in block_lower or category_pt in block_lower) and record.severity == "HIGH":
                    matched = True
                    match_reason = f"Categoria {record.category} mencionada com severidade HIGH"
            
            if matched:
                record.status = "ACCEPTED"
                record.round_resolved = round_num
                record.resolution = match_reason
                resolved_ids.append(iss_id)
        
        # Verificar seção "Melhorias Propostas" para deferrals
        improvements_block = self._extract_section_content(defense_text, "## Melhorias Propostas")
        if improvements_block:
            for iss_id, record in self.issues.items():
                if record.status != "OPEN":
                    continue
                # Se a melhoria menciona postergar/v2/futuro
                defer_keywords = ["v2", "futuro", "postergar", "adiado", "backlog"]
                block_lower = improvements_block.lower()
                if any(kw in block_lower for kw in defer_keywords):
                    if iss_id.upper() in improvements_block.upper():
                        record.status = "DEFERRED"
                        record.round_resolved = round_num
                        record.resolution = "Deferido para versão futura"
                        resolved_ids.append(iss_id)
        
        return resolved_ids
    
    def get_open_issues(self) -> List[IssueRecord]:
        """Retorna issues ainda OPEN, ordenados por severidade (HIGH primeiro)."""
        severity_order = {"HIGH": 0, "MED": 1, "LOW": 2}
        open_issues = [r for r in self.issues.values() if r.status == "OPEN"]
        return sorted(open_issues, key=lambda x: severity_order.get(x.severity, 3))
    
    def get_resolved_issues(self) -> List[IssueRecord]:
        """Retorna todos os issues que não estão mais OPEN."""
        return [r for r in self.issues.values() if r.status != "OPEN"]
    
    def get_open_issues_prompt(self) -> str:
        """
        Gera contexto de issues OPEN para injetar no prompt do Critic.
        Instrui o Critic a NÃO re-levantar estes issues.
        
        Returns:
            String Markdown para injeção no contexto do Critic
        """
        open_issues = self.get_open_issues()
        
        if not open_issues:
            return (
                "ESTADO DO DEBATE: Nenhum issue aberto de rodadas anteriores.\n"
                "Você pode levantar novos problemas livremente.\n"
            )
        
        lines = [
            "═══ ISSUES JÁ REGISTRADOS (NÃO repita) ═══\n",
            "Os seguintes issues já foram levantados em rodadas anteriores.",
            "NÃO os repita. Foque EXCLUSIVAMENTE em NOVOS problemas.\n",
            "| ID | Severidade | Categoria | Descrição | Rodada |",
            "|---|---|---|---|---|"
        ]
        
        for issue in open_issues:
            desc_short = issue.description[:80].replace('|', '/')
            lines.append(
                f"| {issue.issue_id} | {issue.severity} | "
                f"{issue.category} | {desc_short} | R{issue.round_raised} |"
            )
        
        lines.append("")
        lines.append(f"Total de issues abertos: {len(open_issues)}")
        lines.append("═══ FIM DOS ISSUES REGISTRADOS ═══\n")
        
        return "\n".join(lines)
    
    def get_issues_for_proponent(self) -> str:
        """
        Gera contexto de issues OPEN para o Proponent defender.
        
        Returns:
            String Markdown para injeção no contexto do Proponent
        """
        open_issues = self.get_open_issues()
        
        if not open_issues:
            return (
                "ESTADO DO DEBATE: Todos os issues anteriores foram resolvidos.\n"
                "Foque em fortalecer a proposta.\n"
            )
        
        lines = [
            "═══ ISSUES QUE VOCÊ DEVE ENDEREÇAR ═══\n",
            "Para cada issue abaixo, na sua seção '## Pontos Aceitos', declare:"
        ]
        
        for issue in open_issues:
            desc_short = issue.description[:100].replace('|', '/')
            action_hint = ""
            if issue.severity == "HIGH":
                action_hint = " ← PRIORITÁRIO, endereçar obrigatoriamente"
            lines.append(
                f"- **{issue.issue_id}** [{issue.severity}/{issue.category}]: "
                f"{desc_short}{action_hint}"
            )
        
        lines.append("")
        lines.append(
            "Responda com '## Pontos Aceitos' listando quais issues você aceita, "
            "e '## Defesa Técnica' para os que você contesta.\n"
        )
        lines.append("═══ FIM DOS ISSUES ═══\n")
        
        return "\n".join(lines)
    
    def get_consolidation_summary(self) -> str:
        """
        Gera sumário estruturado para o Consolidador (TASK_07).
        Formato Markdown com tabelas de issues resolvidos e abertos.
        
        Returns:
            String Markdown pronta para anexar ao debate_transcript
        """
        lines = ["\n## Estado Final do Debate\n"]
        
        resolved = self.get_resolved_issues()
        open_issues = self.get_open_issues()
        total = len(self.issues)
        
        # ═══ Estatísticas ═══
        lines.append(f"- **Total de issues rastreados:** {total}")
        lines.append(f"- **Resolvidos/Aceitos:** {len(resolved)}")
        lines.append(f"- **Ainda abertos:** {len(open_issues)}")
        
        has_blocking = self.has_blocking_issues()
        lines.append(f"- **Issues bloqueantes (HIGH + OPEN):** {'⚠️ SIM' if has_blocking else '✅ NÃO'}")
        lines.append("")
        
        # ═══ Tabela de Issues Resolvidos ═══
        if resolved:
            lines.append("### Issues Resolvidos")
            lines.append("| ID | Severidade | Categoria | Descrição | Status | Resolução | Round |")
            lines.append("|---|---|---|---|---|---|---|")
            for r in resolved:
                desc = r.description[:60].replace('|', '/')
                res = r.resolution[:60].replace('|', '/')
                lines.append(
                    f"| {r.issue_id} | {r.severity} | {r.category} | "
                    f"{desc} | {r.status} | {res} | "
                    f"R{r.round_raised}→R{r.round_resolved or '?'} |"
                )
            lines.append("")
        
        # ═══ Tabela de Issues Abertos ═══
        if open_issues:
            lines.append("### ⚠️ Issues NÃO Resolvidos")
            lines.append("| ID | Severidade | Categoria | Descrição | Rodada |")
            lines.append("|---|---|---|---|---|")
            for o in open_issues:
                desc = o.description[:80].replace('|', '/')
                lines.append(
                    f"| {o.issue_id} | {o.severity} | {o.category} | "
                    f"{desc} | R{o.round_raised} |"
                )
            lines.append("")
            lines.append(
                "**ATENÇÃO para o Consolidador:** Os issues acima NÃO foram resolvidos "
                "durante o debate. O PRD Final deve documentá-los como riscos ou limitações."
            )
        else:
            lines.append("### ✅ Todos os issues foram resolvidos durante o debate.")
        
        lines.append("")
        return "\n".join(lines)
    
    def has_blocking_issues(self) -> bool:
        """True se existir qualquer issue HIGH ainda OPEN."""
        return any(
            i.severity == "HIGH" and i.status == "OPEN"
            for i in self.issues.values()
        )
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do tracker para logging."""
        return {
            "total": len(self.issues),
            "open": len(self.get_open_issues()),
            "resolved": len(self.get_resolved_issues()),
            "has_blocking": self.has_blocking_issues(),
            "rounds_tracked": self.current_round,
        }
    
    # ═══════════════════════════════════════════════════════
    # MÉTODOS DE PARSING (INTERNOS)
    # ═══════════════════════════════════════════════════════
    
    def _parse_issue_table(self, text: str, round_num: int) -> List[str]:
        """
        Extrai issues de tabelas Markdown.
        
        Padrões suportados:
            | ISS-01 | HIGH | SECURITY | Localização | Descrição | Sugestão |
            | ISS-01 | HIGH | SECURITY | Descrição | Sugestão |
        """
        new_ids = []
        
        # Padrão com 6 colunas: ID | SEV | CAT | LOC | DESC | SUGEST
        pattern_6col = (
            r'\|\s*(ISS-\d+)\s*\|\s*(HIGH|MED|MEDIUM|LOW)\s*\|'
            r'\s*(\w+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]*)\|'
        )
        
        for match in re.finditer(pattern_6col, text, re.IGNORECASE):
            iss_id = match.group(1).upper()
            severity = self._normalize_severity(match.group(2))
            category = match.group(3).strip().upper()
            location = match.group(4).strip()
            description = match.group(5).strip()
            
            full_desc = f"{location}: {description}" if location else description
            
            if self._register_issue(iss_id, severity, category, full_desc, round_num):
                new_ids.append(iss_id)
        
        # Padrão com 4-5 colunas (fallback mais flexível)
        if not new_ids:
            pattern_flex = (
                r'\|\s*(ISS-\d+)\s*\|\s*(HIGH|MED|MEDIUM|LOW)\s*\|'
                r'\s*(\w+)\s*\|\s*([^|]+)\|'
            )
            
            for match in re.finditer(pattern_flex, text, re.IGNORECASE):
                iss_id = match.group(1).upper()
                severity = self._normalize_severity(match.group(2))
                category = match.group(3).strip().upper()
                description = match.group(4).strip()
                
                if self._register_issue(iss_id, severity, category, description, round_num):
                    new_ids.append(iss_id)
        
        return new_ids
    
    def _parse_issue_bullets(self, text: str, round_num: int) -> List[str]:
        """
        Fallback: Extrai issues de bullets quando Critic não usa tabela.
        
        Procura padrões como:
            - [HIGH] Falta de autenticação no endpoint X
            - HIGH: Dados sensíveis sem criptografia
        """
        new_ids = []
        
        # Padrão 1: - [SEV] descrição
        bracket_pattern = r'-\s*\[(HIGH|MED|MEDIUM|LOW)\]\s*(.+?)(?:\n|$)'
        for match in re.finditer(bracket_pattern, text, re.IGNORECASE):
            severity = self._normalize_severity(match.group(1))
            description = match.group(2).strip()
            
            iss_id = self._generate_auto_id()
            if self._register_issue(iss_id, severity, "GENERAL", description, round_num):
                new_ids.append(iss_id)
        
        # Padrão 2: - SEV: descrição (ou SEV — descrição)
        if not new_ids:
            colon_pattern = r'-\s*(HIGH|MED|MEDIUM|LOW)\s*[:\—\-]\s*(.+?)(?:\n|$)'
            for match in re.finditer(colon_pattern, text, re.IGNORECASE):
                severity = self._normalize_severity(match.group(1))
                description = match.group(2).strip()
                
                iss_id = self._generate_auto_id()
                if self._register_issue(iss_id, severity, "GENERAL", description, round_num):
                    new_ids.append(iss_id)
        
        return new_ids
    
    def _register_issue(self, iss_id: str, severity: str, category: str,
                        description: str, round_num: int) -> bool:
        """
        Registra um issue se não for duplicata.
        
        Deduplicação por:
            1. ID exato (ISS-01 == ISS-01)
            2. Descrição normalizada similar (evita re-registro com ID diferente)
        
        Returns:
            True se o issue foi registrado (novo), False se duplicata
        """
        # Dedup por ID
        if iss_id in self.issues:
            return False
        
        # Dedup por descrição normalizada
        desc_key = self._normalize_text(description[:60])
        if desc_key in self._seen_descriptions and len(desc_key) > 15:
            return False
        
        # Registrar
        self.issues[iss_id] = IssueRecord(
            issue_id=iss_id,
            severity=severity,
            category=category,
            description=description[:200],
            round_raised=round_num
        )
        
        if desc_key:
            self._seen_descriptions.add(desc_key)
        
        return True
    
    def _generate_auto_id(self) -> str:
        """Gera ID auto-incremental para issues sem ID explícito."""
        while f"ISS-{self._next_auto_id:02d}" in self.issues:
            self._next_auto_id += 1
        iss_id = f"ISS-{self._next_auto_id:02d}"
        self._next_auto_id += 1
        return iss_id
    
    def _normalize_severity(self, severity: str) -> str:
        """Normaliza variações de severidade."""
        s = severity.strip().upper()
        if s == "MEDIUM":
            return "MED"
        if s in ("HIGH", "MED", "LOW"):
            return s
        return "MED"  # Default seguro
    
    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para comparação (lowercase, sem pontuação extra)."""
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _extract_section_content(self, text: str, heading: str) -> str:
        """
        Extrai conteúdo de uma seção ## até a próxima seção ## ou fim do texto.
        Retorna string vazia se seção não encontrada.
        """
        # Escapar caracteres especiais no heading para regex
        escaped = re.escape(heading)
        pattern = escaped + r'\s*\n(.*?)(?=\n## |\Z)'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""
```

---

## 2. Modificar `src/debate/debate_engine.py`

Substituir o arquivo completo:

```python
from typing import Dict, Any
from src.agents.critic_agent import CriticAgent
from src.agents.proponent_agent import ProponentAgent
from src.core.stream_handler import ANSIStyle
from src.debate.debate_state_tracker import DebateStateTracker


class DebateEngine:
    """
    Executa o debate estruturado entre o Agente Proponente e o Agente Crítico.
    
    FASE 10.0: Integrado com DebateStateTracker para rastreamento
    de issues entre rodadas, eliminando repetição e desperdício de tokens.
    """
    
    def __init__(self, proponent: ProponentAgent, critic: CriticAgent, rounds: int = 3):
        self.proponent = proponent
        self.critic = critic
        self.num_rounds = rounds
        self.debate_transcript = []
        self.state_tracker = DebateStateTracker()  # FASE 10.0

    def run(self, first_input: str, context: str = "", report_filename: str = None) -> str:
        """
        Executa os ciclos de debate alternados usando contexto do Blackboard.
        
        FASE 10.0: Cada rodada agora injeta estado de issues no contexto
        dos agentes para evitar repetição e focar em problemas não resolvidos.
        
        first_input: Geralmente o PRD ou a Ideia Refinada.
        context: Contexto acumulado de outros artefatos (ex: System Design).
        """
        print(
            f"\n{ANSIStyle.BOLD}{ANSIStyle.YELLOW}"
            f"{'═' * 50}\n"
            f" ⚖ INICIANDO DEBATE ESTRUTURADO "
            f"({self.num_rounds} rounds)\n"
            f"{'═' * 50}"
            f"{ANSIStyle.RESET}"
        )
        
        # FASE 3.1: O contexto inicial é enxuto.
        initial_context = f"Main Subject:\n{first_input[:1000]}\n\nRelated Context:\n{context[:500]}\n\n"
        current_context = initial_context
        
        for r in range(1, self.num_rounds + 1):
            # ── Round Header ──
            print(
                f"\n{ANSIStyle.BOLD}{ANSIStyle.BLUE}"
                f"┌{'─' * 48}┐\n"
                f"│ Round {r}/{self.num_rounds} │\n"
                f"└{'─' * 48}┘"
                f"{ANSIStyle.RESET}"
            )
            
            # ═══ FASE 10.0: Estado do tracker para este round ═══
            tracker_stats = self.state_tracker.get_stats()
            if tracker_stats["total"] > 0:
                print(
                    f"{ANSIStyle.CYAN}"
                    f" Estado: {tracker_stats['open']} issues abertos, "
                    f"{tracker_stats['resolved']} resolvidos"
                    f"{ANSIStyle.RESET}"
                )
            
            # ══════════════════════════════════════════
            # TURNO DO PROPONENTE
            # ══════════════════════════════════════════
            print(
                f"\n{ANSIStyle.BOLD}{ANSIStyle.GREEN}"
                f" 🛡 PROPONENTE — formulando defesa arquitetural..."
                f"{ANSIStyle.RESET}"
            )
            
            # FASE 10.0: Injetar issues abertos para o Proponent endereçar
            issues_for_proponent = self.state_tracker.get_issues_for_proponent()
            
            # FASE 3.1: O Proponente foca na crítica anterior
            last_critique = self.debate_transcript[-1] if self.debate_transcript else "Inicie a defesa técnica."
            
            # Montar contexto enriquecido para o Proponent
            proponent_context = initial_context
            if issues_for_proponent and self.state_tracker.get_stats()["open"] > 0:
                proponent_context = f"{initial_context}\n{issues_for_proponent}"
            
            prop_response = self.proponent.defend_artifact(
                artifact_content=first_input,
                critique=last_critique,
                context=proponent_context
            )
            
            self.debate_transcript.append(f"Proponente:\n{prop_response}")
            
            # FASE 10.0: Extrair resoluções da resposta do Proponent
            resolved_ids = self.state_tracker.extract_resolutions_from_defense(prop_response, r)
            if resolved_ids:
                print(
                    f"{ANSIStyle.GREEN}"
                    f" ✅ Issues resolvidos neste round: {resolved_ids}"
                    f"{ANSIStyle.RESET}"
                )
            
            if report_filename:
                try:
                    with open(report_filename, "a", encoding="utf-8") as f:
                        f.write(f"\n## Agente: PROPONENTE (Round {r})\n")
                        f.write(prop_response + "\n\n---\n")
                except OSError:
                    pass
            
            # ══════════════════════════════════════════
            # TURNO DO CRÍTICO
            # ══════════════════════════════════════════
            print(
                f"\n{ANSIStyle.BOLD}{ANSIStyle.YELLOW}"
                f" ⚡ CRÍTICO — analisando vulnerabilidades e lacunas..."
                f"{ANSIStyle.RESET}"
            )
            
            # FASE 10.0: Injetar lista de issues OPEN para o Critic NÃO repetir
            open_issues_context = self.state_tracker.get_open_issues_prompt()
            
            # Montar contexto enriquecido para o Critic
            critic_context = (
                f"{initial_context}\n\n"
                f"Última Resposta (🛡 Proponente):\n{prop_response[:800]}\n\n"
                f"{open_issues_context}"
            )
            
            crit_response = self.critic.review_artifact(
                artifact_content=first_input,
                artifact_type="document",
                context=critic_context
            )
            
            self.debate_transcript.append(f"Crítico:\n{crit_response}")
            
            # FASE 10.0: Extrair novos issues da crítica
            new_issue_ids = self.state_tracker.extract_issues_from_critique(crit_response, r)
            if new_issue_ids:
                print(
                    f"{ANSIStyle.YELLOW}"
                    f" 📋 Novos issues registrados: {new_issue_ids}"
                    f"{ANSIStyle.RESET}"
                )
            
            if report_filename:
                try:
                    with open(report_filename, "a", encoding="utf-8") as f:
                        f.write(f"\n## Agente: CRÍTICO (Round {r})\n")
                        f.write(crit_response + "\n\n---\n")
                except OSError:
                    pass

        # ═══ FASE 9.0: Decisões Aplicáveis (mantido) ═══
        decisions_section = self._extract_decisions_from_transcript()
        self.debate_transcript.append(decisions_section)

        # ═══ FASE 10.0: Sumário de estado do tracker ═══
        consolidation_summary = self.state_tracker.get_consolidation_summary()
        self.debate_transcript.append(consolidation_summary)

        # ═══ Fechamento ═══
        final_stats = self.state_tracker.get_stats()
        blocking_warning = ""
        if final_stats["has_blocking"]:
            blocking_warning = (
                f"\n{ANSIStyle.YELLOW}{ANSIStyle.BOLD}"
                f" ⚠️ ATENÇÃO: {final_stats['open']} issue(s) HIGH ainda aberto(s)!"
                f"{ANSIStyle.RESET}"
            )

        print(
            f"\n{ANSIStyle.BOLD}{ANSIStyle.GREEN}"
            f"{'═' * 50}\n"
            f" ✅ DEBATE CONCLUÍDO — {self.num_rounds} rounds completos\n"
            f"    Issues: {final_stats['total']} total, "
            f"{final_stats['resolved']} resolvidos, "
            f"{final_stats['open']} abertos\n"
            f"{'═' * 50}"
            f"{ANSIStyle.RESET}"
            f"{blocking_warning}\n"
        )
        
        return "\n\n".join(self.debate_transcript)

    def _extract_decisions_from_transcript(self) -> str:
        """
        FASE 9.0: Extrai decisões estruturadas dos "Pontos Aceitos"
        de cada round do Proponente.
        """
        decisions_section = (
            "\n## Decisões Aplicáveis (Síntese)\n\n"
            "| Round | Tipo | Decisão | Justificativa |\n"
            "|---|---|---|---|\n"
        )

        decisions_found = 0

        for entry_idx, entry in enumerate(self.debate_transcript):
            if not entry.startswith("Proponente:"):
                continue

            round_num = (entry_idx // 2) + 1

            # Extrair "Pontos Aceitos"
            if "## Pontos Aceitos" in entry:
                accepted_block = entry.split("## Pontos Aceitos")[1]
                if "##" in accepted_block[1:]:
                    next_section = accepted_block.index("##", 1)
                    accepted_block = accepted_block[:next_section]

                for line in accepted_block.strip().split('\n'):
                    line = line.strip().lstrip('- ')
                    if line and len(line) > 10 and not line.startswith('#'):
                        decision_text = line[:120]
                        decisions_section += (
                            f"| R{round_num} | ACEITO | "
                            f"{decision_text} | Proponente concordou |\n"
                        )
                        decisions_found += 1

            # Extrair "Melhorias Propostas" (tabela)
            if "## Melhorias Propostas" in entry:
                improvements_block = entry.split("## Melhorias Propostas")[1]
                if "##" in improvements_block[1:]:
                    next_section = improvements_block.index("##", 1)
                    improvements_block = improvements_block[:next_section]

                table_lines = [
                    l for l in improvements_block.strip().split('\n')
                    if l.strip().startswith('|')
                    and '---|' not in l
                    and 'Área' not in l
                ]
                for tl in table_lines:
                    cells = [c.strip() for c in tl.split('|') if c.strip()]
                    if len(cells) >= 3:
                        area = cells[0][:30]
                        change = cells[1][:60]
                        justification = cells[2][:60]
                        decisions_section += (
                            f"| R{round_num} | MELHORIA | "
                            f"{area}: {change} | {justification} |\n"
                        )
                        decisions_found += 1

        if decisions_found == 0:
            decisions_section += (
                "| - | - | Nenhuma decisão estruturada extraída | "
                "Debate em formato livre |\n"
            )

        decisions_section += f"\n*Total de decisões extraídas: {decisions_found}*\n"

        return decisions_section
```

---

## 3. Modificar `src/agents/critic_agent.py`

Localizar a string `self._base_system_prompt` no `__init__`. Encontrar a linha que diz `"8. Responda em Português.\n\n"` e **adicionar imediatamente após**:

```python
                "9. Se houver lista de ISSUES ABERTOS no contexto, NÃO os repita. "
                "Levante APENAS problemas NOVOS não listados.\n"
                "10. Cada novo issue DEVE ter ID incremental (ISS-XX) continuando a numeração existente.\n\n"
```

**Localização exata — antes:**

```python
                "8. Responda em Português.\n\n"
                "## CATEGORIAS DE ISSUE\n"
```

**Depois:**

```python
                "8. Responda em Português.\n"
                "9. Se houver lista de ISSUES ABERTOS no contexto, NÃO os repita. "
                "Levante APENAS problemas NOVOS não listados.\n"
                "10. Cada novo issue DEVE ter ID incremental (ISS-XX) continuando a numeração existente.\n\n"
                "## CATEGORIAS DE ISSUE\n"
```

---

## 4. Modificar `src/agents/proponent_agent.py`

Localizar o método `defend_artifact`. Alterar os limites de truncamento:

**Antes:**

```python
        defense_prompt = (
            f"System: {self.system_prompt}\n\n"
            f"ARTEFATO:\n{artifact_content[:1000]}\n\n"
            f"CRÍTICA RECEBIDA:\n{critique[:500]}\n\n"
        )
```

**Depois:**

```python
        defense_prompt = (
            f"System: {self.system_prompt}\n\n"
            f"ARTEFATO:\n{artifact_content[:2000]}\n\n"   # FASE 10.0: era [:1000]
            f"CRÍTICA RECEBIDA:\n{critique[:800]}\n\n"    # FASE 10.0: era [:500]
        )
```

---

## 5. Novo Arquivo: `tests/test_debate_tracker.py`

```python
"""
test_debate_tracker.py — Testes para o DebateStateTracker (Fase 10.0).
"""
import pytest
from src.debate.debate_state_tracker import DebateStateTracker, IssueRecord


# ═══════════════════════════════════════════════════════════
# TESTES DE PARSING DE ISSUES DO CRITIC
# ═══════════════════════════════════════════════════════════

class TestExtractIssuesFromTable:
    """Testes de extração de issues de tabelas Markdown."""

    def test_extract_6_column_table(self):
        tracker = DebateStateTracker()
        critique = (
            "## Issues Identificadas\n"
            "| ID | Severidade | Categoria | Localização | Descrição | Sugestão |\n"
            "|---|---|---|---|---|---|\n"
            "| ISS-01 | HIGH | SECURITY | Seção Auth | Senha sem hash | Usar bcrypt |\n"
            "| ISS-02 | MED | COMPLETENESS | Seção Riscos | Falta risco infra | Adicionar riscos |\n"
            "| ISS-03 | LOW | CONSISTENCY | Tech Stack | Redis sem módulo | Remover ou adicionar |\n"
        )
        new_ids = tracker.extract_issues_from_critique(critique, round_num=1)
        
        assert len(new_ids) == 3
        assert "ISS-01" in new_ids
        assert "ISS-02" in new_ids
        assert "ISS-03" in new_ids
        assert tracker.issues["ISS-01"].severity == "HIGH"
        assert tracker.issues["ISS-01"].category == "SECURITY"
        assert tracker.issues["ISS-02"].severity == "MED"
        assert tracker.issues["ISS-03"].round_raised == 1

    def test_extract_4_column_table(self):
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | Falha de autenticação |\n"
        )
        new_ids = tracker.extract_issues_from_critique(critique, round_num=2)
        
        assert len(new_ids) == 1
        assert tracker.issues["ISS-01"].severity == "HIGH"
        assert tracker.issues["ISS-01"].round_raised == 2

    def test_extract_with_medium_spelled_out(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | MEDIUM | CORRECTNESS | Lógica errada |\n"
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        
        assert len(new_ids) == 1
        assert tracker.issues["ISS-01"].severity == "MED"

    def test_no_duplicate_registration(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | HIGH | SECURITY | Falha auth |\n"
        
        ids_r1 = tracker.extract_issues_from_critique(critique, 1)
        ids_r2 = tracker.extract_issues_from_critique(critique, 2)
        
        assert len(ids_r1) == 1
        assert len(ids_r2) == 0
        assert len(tracker.issues) == 1

    def test_similar_description_dedup(self):
        tracker = DebateStateTracker()
        critique1 = "| ISS-01 | HIGH | SECURITY | Senha de usuário armazenada sem hashing |\n"
        critique2 = "| ISS-05 | HIGH | SECURITY | Senha de usuário armazenada sem hashing |\n"
        
        ids1 = tracker.extract_issues_from_critique(critique1, 1)
        ids2 = tracker.extract_issues_from_critique(critique2, 2)
        
        assert len(ids1) == 1
        assert len(ids2) == 0  # Mesma descrição, ID diferente → dedup


class TestExtractIssuesFromBullets:
    """Testes de extração fallback via bullets."""

    def test_bracket_severity_pattern(self):
        tracker = DebateStateTracker()
        critique = (
            "## Issues\n"
            "- [HIGH] Falta de autenticação no endpoint de admin\n"
            "- [LOW] Documentação de API incompleta\n"
        )
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        
        assert len(new_ids) == 2
        high_issues = [i for i in tracker.issues.values() if i.severity == "HIGH"]
        low_issues = [i for i in tracker.issues.values() if i.severity == "LOW"]
        assert len(high_issues) == 1
        assert len(low_issues) == 1

    def test_colon_severity_pattern(self):
        tracker = DebateStateTracker()
        critique = "- HIGH: Dados sensíveis sem criptografia\n"
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        
        assert len(new_ids) == 1
        assert tracker.issues[new_ids[0]].severity == "HIGH"

    def test_no_issues_in_plain_text(self):
        tracker = DebateStateTracker()
        critique = "A arquitetura parece boa. Continuar assim."
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        
        assert len(new_ids) == 0

    def test_empty_critique(self):
        tracker = DebateStateTracker()
        assert tracker.extract_issues_from_critique("", 1) == []
        assert tracker.extract_issues_from_critique(None, 1) == []


# ═══════════════════════════════════════════════════════════
# TESTES DE RESOLUÇÃO DE ISSUES
# ═══════════════════════════════════════════════════════════

class TestExtractResolutions:
    """Testes de detecção de resoluções na resposta do Proponent."""

    def test_resolve_by_explicit_id(self):
        tracker = DebateStateTracker()
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | Sem hash de senha |\n", 1
        )
        
        defense = (
            "## Pontos Aceitos\n"
            "- ISS-01: Concordamos em usar bcrypt para hash de senhas\n"
            "## Defesa Técnica\n"
            "- Restante da arquitetura está sólida\n"
        )
        resolved = tracker.extract_resolutions_from_defense(defense, 1)
        
        assert "ISS-01" in resolved
        assert tracker.issues["ISS-01"].status == "ACCEPTED"
        assert tracker.issues["ISS-01"].round_resolved == 1

    def test_resolve_by_description_match(self):
        tracker = DebateStateTracker()
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | Senha de usuário sem hashing no banco |\n", 1
        )
        
        defense = (
            "## Pontos Aceitos\n"
            "- A questão da senha de usuário sem hashing é válida, vamos corrigir\n"
        )
        resolved = tracker.extract_resolutions_from_defense(defense, 1)
        
        assert "ISS-01" in resolved
        assert tracker.issues["ISS-01"].status == "ACCEPTED"

    def test_no_resolve_without_pontos_aceitos(self):
        tracker = DebateStateTracker()
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | Problema grave |\n", 1
        )
        
        defense = (
            "## Defesa Técnica\n"
            "- ISS-01 não é um problema real, o sistema já cobre isso\n"
        )
        resolved = tracker.extract_resolutions_from_defense(defense, 1)
        
        # Sem seção "Pontos Aceitos", o issue permanece OPEN
        assert len(resolved) == 0
        assert tracker.issues["ISS-01"].status == "OPEN"

    def test_empty_defense(self):
        tracker = DebateStateTracker()
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | X |\n", 1
        )
        assert tracker.extract_resolutions_from_defense("", 1) == []
        assert tracker.extract_resolutions_from_defense(None, 1) == []

    def test_partial_resolution(self):
        """Apenas alguns issues são resolvidos, outros permanecem OPEN."""
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | Sem autenticação |\n"
            "| ISS-02 | MED | COMPLETENESS | Falta documentação |\n"
            "| ISS-03 | LOW | CONSISTENCY | Naming inconsistente |\n"
        )
        tracker.extract_issues_from_critique(critique, 1)
        
        defense = (
            "## Pontos Aceitos\n"
            "- ISS-01: Vamos adicionar JWT\n"
            "- ISS-03: Vamos padronizar nomenclatura\n"
            "## Defesa Técnica\n"
            "- ISS-02: A documentação será feita na v2\n"
        )
        resolved = tracker.extract_resolutions_from_defense(defense, 1)
        
        assert "ISS-01" in resolved
        assert "ISS-03" in resolved
        assert "ISS-02" not in resolved
        assert tracker.issues["ISS-01"].status == "ACCEPTED"
        assert tracker.issues["ISS-02"].status == "OPEN"
        assert tracker.issues["ISS-03"].status == "ACCEPTED"


# ═══════════════════════════════════════════════════════════
# TESTES DE QUERIES
# ═══════════════════════════════════════════════════════════

class TestTrackerQueries:
    """Testes para métodos de consulta do tracker."""

    def _setup_tracker_with_mixed_issues(self):
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | Sem auth |\n"
            "| ISS-02 | MED | COMPLETENESS | Falta doc |\n"
            "| ISS-03 | LOW | CONSISTENCY | Naming |\n"
        )
        tracker.extract_issues_from_critique(critique, 1)
        
        defense = "## Pontos Aceitos\n- ISS-03: OK\n"
        tracker.extract_resolutions_from_defense(defense, 1)
        
        return tracker

    def test_get_open_issues(self):
        tracker = self._setup_tracker_with_mixed_issues()
        open_issues = tracker.get_open_issues()
        
        assert len(open_issues) == 2
        # HIGH deve vir primeiro (ordenação por severidade)
        assert open_issues[0].severity == "HIGH"
        assert open_issues[1].severity == "MED"

    def test_get_resolved_issues(self):
        tracker = self._setup_tracker_with_mixed_issues()
        resolved = tracker.get_resolved_issues()
        
        assert len(resolved) == 1
        assert resolved[0].issue_id == "ISS-03"

    def test_has_blocking_issues_true(self):
        tracker = self._setup_tracker_with_mixed_issues()
        assert tracker.has_blocking_issues() is True

    def test_has_blocking_issues_false(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | LOW | CONSISTENCY | Minor |\n"
        tracker.extract_issues_from_critique(critique, 1)
        
        assert tracker.has_blocking_issues() is False

    def test_has_blocking_false_when_resolved(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | HIGH | SECURITY | Crítico |\n"
        tracker.extract_issues_from_critique(critique, 1)
        assert tracker.has_blocking_issues() is True
        
        defense = "## Pontos Aceitos\n- ISS-01: Corrigido\n"
        tracker.extract_resolutions_from_defense(defense, 1)
        assert tracker.has_blocking_issues() is False

    def test_empty_tracker(self):
        tracker = DebateStateTracker()
        assert tracker.get_open_issues() == []
        assert tracker.get_resolved_issues() == []
        assert tracker.has_blocking_issues() is False


# ═══════════════════════════════════════════════════════════
# TESTES DE PROMPT GENERATION
# ═══════════════════════════════════════════════════════════

class TestPromptGeneration:
    """Testes para geração de prompts contextuais."""

    def test_open_issues_prompt_with_issues(self):
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | Sem autenticação no endpoint |\n"
            "| ISS-02 | MED | COMPLETENESS | Documentação ausente |\n"
        )
        tracker.extract_issues_from_critique(critique, 1)
        
        prompt = tracker.get_open_issues_prompt()
        
        assert "NÃO repita" in prompt
        assert "ISS-01" in prompt
        assert "ISS-02" in prompt
        assert "HIGH" in prompt
        assert "SECURITY" in prompt
        assert "Total de issues abertos: 2" in prompt

    def test_open_issues_prompt_empty(self):
        tracker = DebateStateTracker()
        prompt = tracker.get_open_issues_prompt()
        
        assert "Nenhum issue aberto" in prompt

    def test_issues_for_proponent_with_issues(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | HIGH | SECURITY | Sem auth |\n"
        tracker.extract_issues_from_critique(critique, 1)
        
        prompt = tracker.get_issues_for_proponent()
        
        assert "ISS-01" in prompt
        assert "DEVE ENDEREÇAR" in prompt
        assert "PRIORITÁRIO" in prompt  # HIGH issues marcados como prioritários

    def test_issues_for_proponent_empty(self):
        tracker = DebateStateTracker()
        prompt = tracker.get_issues_for_proponent()
        
        assert "Todos os issues" in prompt or "resolvidos" in prompt


# ═══════════════════════════════════════════════════════════
# TESTES DE CONSOLIDATION SUMMARY
# ═══════════════════════════════════════════════════════════

class TestConsolidationSummary:
    """Testes para o sumário de consolidação."""

    def test_summary_with_mixed_states(self):
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | Sem auth |\n"
            "| ISS-02 | MED | COMPLETENESS | Falta doc |\n"
        )
        tracker.extract_issues_from_critique(critique, 1)
        
        defense = "## Pontos Aceitos\n- ISS-02: Vamos documentar\n"
        tracker.extract_resolutions_from_defense(defense, 1)
        
        summary = tracker.get_consolidation_summary()
        
        assert "Estado Final do Debate" in summary
        assert "Issues Resolvidos" in summary
        assert "Issues NÃO Resolvidos" in summary
        assert "ISS-01" in summary
        assert "ISS-02" in summary
        assert "⚠️ SIM" in summary  # has_blocking = True (ISS-01 HIGH OPEN)

    def test_summary_all_resolved(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | LOW | CONSISTENCY | Minor |\n"
        tracker.extract_issues_from_critique(critique, 1)
        
        defense = "## Pontos Aceitos\n- ISS-01: OK\n"
        tracker.extract_resolutions_from_defense(defense, 1)
        
        summary = tracker.get_consolidation_summary()
        
        assert "Todos os issues foram resolvidos" in summary
        assert "✅ NÃO" in summary  # has_blocking = False

    def test_summary_empty_tracker(self):
        tracker = DebateStateTracker()
        summary = tracker.get_consolidation_summary()
        
        assert "Total de issues rastreados:** 0" in summary

    def test_summary_contains_stats(self):
        tracker = DebateStateTracker()
        critique = (
            "| ISS-01 | HIGH | SECURITY | A |\n"
            "| ISS-02 | MED | CORRECTNESS | B |\n"
            "| ISS-03 | LOW | CONSISTENCY | C |\n"
        )
        tracker.extract_issues_from_critique(critique, 1)
        
        summary = tracker.get_consolidation_summary()
        
        assert "Total de issues rastreados:** 3" in summary
        assert "Resolvidos/Aceitos:** 0" in summary
        assert "Ainda abertos:** 3" in summary


# ═══════════════════════════════════════════════════════════
# TESTES DE MULTI-ROUND
# ═══════════════════════════════════════════════════════════

class TestMultiRoundTracking:
    """Testes simulando múltiplas rodadas de debate."""

    def test_two_round_flow(self):
        tracker = DebateStateTracker()
        
        # Round 1: Critic levanta 2 issues
        critique_r1 = (
            "| ISS-01 | HIGH | SECURITY | Sem autenticação |\n"
            "| ISS-02 | MED | COMPLETENESS | Sem testes |\n"
        )
        new_r1 = tracker.extract_issues_from_critique(critique_r1, 1)
        assert len(new_r1) == 2
        assert len(tracker.get_open_issues()) == 2
        
        # Round 1: Proponent resolve ISS-01
        defense_r1 = "## Pontos Aceitos\n- ISS-01: Vamos adicionar JWT\n"
        resolved_r1 = tracker.extract_resolutions_from_defense(defense_r1, 1)
        assert "ISS-01" in resolved_r1
        assert len(tracker.get_open_issues()) == 1
        
        # Round 2: Critic levanta 1 novo issue (NÃO repete ISS-01 ou ISS-02)
        critique_r2 = (
            "| ISS-03 | HIGH | CORRECTNESS | Lógica de cálculo errada |\n"
        )
        new_r2 = tracker.extract_issues_from_critique(critique_r2, 2)
        assert len(new_r2) == 1
        assert "ISS-03" in new_r2
        
        # Estado final: ISS-01 resolvido, ISS-02 e ISS-03 abertos
        assert len(tracker.get_open_issues()) == 2
        assert len(tracker.get_resolved_issues()) == 1
        assert tracker.has_blocking_issues() is True  # ISS-03 é HIGH

    def test_three_round_progressive_resolution(self):
        tracker = DebateStateTracker()
        
        # Round 1
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | Auth |\n"
            "| ISS-02 | HIGH | CORRECTNESS | Logic |\n", 1
        )
        assert tracker.has_blocking_issues() is True
        
        # Round 1 defense
        tracker.extract_resolutions_from_defense(
            "## Pontos Aceitos\n- ISS-01: Corrigido\n", 1
        )
        assert tracker.has_blocking_issues() is True  # ISS-02 still HIGH OPEN
        
        # Round 2
        tracker.extract_issues_from_critique(
            "| ISS-03 | LOW | CONSISTENCY | Minor |\n", 2
        )
        
        # Round 2 defense
        tracker.extract_resolutions_from_defense(
            "## Pontos Aceitos\n- ISS-02: Lógica corrigida\n- ISS-03: OK\n", 2
        )
        
        # Todos resolvidos
        assert tracker.has_blocking_issues() is False
        assert len(tracker.get_open_issues()) == 0
        assert len(tracker.get_resolved_issues()) == 3


# ═══════════════════════════════════════════════════════════
# TESTES DE GET_STATS
# ═══════════════════════════════════════════════════════════

class TestGetStats:
    """Testes para o método get_stats."""

    def test_stats_empty(self):
        tracker = DebateStateTracker()
        stats = tracker.get_stats()
        
        assert stats["total"] == 0
        assert stats["open"] == 0
        assert stats["resolved"] == 0
        assert stats["has_blocking"] is False
        assert stats["rounds_tracked"] == 0

    def test_stats_after_activity(self):
        tracker = DebateStateTracker()
        tracker.extract_issues_from_critique(
            "| ISS-01 | HIGH | SECURITY | X |\n"
            "| ISS-02 | LOW | CONSISTENCY | Y |\n", 1
        )
        tracker.extract_resolutions_from_defense(
            "## Pontos Aceitos\n- ISS-02: OK\n", 1
        )
        
        stats = tracker.get_stats()
        assert stats["total"] == 2
        assert stats["open"] == 1
        assert stats["resolved"] == 1
        assert stats["has_blocking"] is True
        assert stats["rounds_tracked"] == 1


# ═══════════════════════════════════════════════════════════
# TESTES DE EDGE CASES E RESILIÊNCIA
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    """Testes de degradação graciosa."""

    def test_malformed_table_no_crash(self):
        tracker = DebateStateTracker()
        critique = (
            "| sem | formato | correto |\n"
            "| ISS-INVALID | XYZ | | broken |\n"
            "Texto livre sem estrutura\n"
        )
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        # Deve retornar lista vazia (graceful degradation), não crashar
        assert isinstance(new_ids, list)

    def test_special_chars_in_description(self):
        tracker = DebateStateTracker()
        critique = "| ISS-01 | HIGH | SECURITY | Falha com chars: <script>alert('xss')</script> |\n"
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        
        assert len(new_ids) == 1

    def test_very_long_description_truncated(self):
        tracker = DebateStateTracker()
        long_desc = "A" * 500
        critique = f"| ISS-01 | HIGH | SECURITY | {long_desc} |\n"
        tracker.extract_issues_from_critique(critique, 1)
        
        assert len(tracker.issues["ISS-01"].description) <= 200

    def test_auto_id_generation_skips_existing(self):
        tracker = DebateStateTracker()
        # Registrar ISS-01 via tabela
        tracker.extract_issues_from_critique("| ISS-01 | HIGH | SECURITY | X |\n", 1)
        
        # Registrar via bullet (auto-ID) — deve gerar ISS-02, não ISS-01
        tracker.extract_issues_from_critique("- [MED] Outro problema diferente do primeiro\n", 2)
        
        assert "ISS-01" in tracker.issues
        assert "ISS-02" in tracker.issues
        assert len(tracker.issues) == 2

    def test_pipe_in_description_handled(self):
        """Pipe characters na descrição não quebram o parser."""
        tracker = DebateStateTracker()
        critique = "| ISS-01 | HIGH | SECURITY | Input com | chars estranhos |\n"
        # O regex pode capturar parcialmente, mas não deve crashar
        new_ids = tracker.extract_issues_from_critique(critique, 1)
        assert isinstance(new_ids, list)
```

---

## 6. Comandos para Rodar os Testes

```bash
# 1. Rodar APENAS os testes do tracker (Fase 10.0)
pytest tests/test_debate_tracker.py -v --tb=short

# 2. Rodar testes do debate (deve continuar passando)
pytest tests/test_debate.py -v --tb=short

# 3. Rodar testes de agentes (critic/proponent com prompts atualizados)
pytest tests/test_agents.py tests/test_new_agents.py -v --tb=short

# 4. Rodar suite completa (deve passar 65+ testes)
pytest tests/ -v --tb=short

# 5. Teste de integração real (com modelo)
python idea-forge/src/cli/main.py --no-gate
```

---

## 7. Checklist de Validação da Fase 10.0

- [ ] `debate_state_tracker.py` existe em `src/debate/`
- [ ] `DebateStateTracker` não faz nenhuma chamada LLM
- [ ] `extract_issues_from_critique` parseia tabelas de 4-6 colunas
- [ ] `extract_issues_from_critique` faz fallback para bullets com severidade
- [ ] `extract_resolutions_from_defense` detecta IDs explícitos nos "Pontos Aceitos"
- [ ] `extract_resolutions_from_defense` detecta descrições similares
- [ ] Issues duplicados não são registrados duas vezes (dedup por ID e descrição)
- [ ] `get_open_issues_prompt` contém instrução "NÃO repita"
- [ ] `get_issues_for_proponent` marca issues HIGH como PRIORITÁRIO
- [ ] `get_consolidation_summary` gera tabelas separadas de resolvidos e abertos
- [ ] `has_blocking_issues` retorna True para HIGH + OPEN
- [ ] `debate_engine.py` instancia `DebateStateTracker` no `__init__`
- [ ] Loop de debate injeta `get_issues_for_proponent()` no contexto do Proponent
- [ ] Loop de debate injeta `get_open_issues_prompt()` no contexto do Critic
- [ ] Após resposta do Proponent, chama `extract_resolutions_from_defense()`
- [ ] Após resposta do Critic, chama `extract_issues_from_critique()`
- [ ] Transcript termina com "Estado Final do Debate"
- [ ] `critic_agent.py` contém regras 9-10 sobre não repetir issues
- [ ] `proponent_agent.py` usa `artifact_content[:2000]` e `critique[:800]`
- [ ] `DebateEngine.run()` mantém mesma assinatura (C-001)
- [ ] `pytest tests/test_debate_tracker.py` — todos passam
- [ ] `pytest tests/test_debate.py` — todos passam
- [ ] `pytest tests/` — todos os 65+ testes passam

---

## 8. DECISION_LOG — Entradas da Fase 10.0

```
### Fase 10.0 — Orquestração Inteligente do Debate
F10 | ADD | `DebateStateTracker` | Rastreamento de issues entre rodadas sem LLM | `debate_state_tracker.py`
F10 | ADD | `IssueRecord` | Dataclass para registro de issues (status, resolução, round) | `debate_state_tracker.py`
F10 | MOD | `DebateEngine` | Integração do tracker com injeção de contexto em Critic e Proponent | `debate_engine.py`
F10 | MOD | `CriticAgent` | Regras 9-10: não repetir issues abertos, IDs incrementais | `critic_agent.py`
F10 | MOD | `ProponentAgent` | Truncamento ampliado: artifact[:2000], critique[:800] | `proponent_agent.py`
F10 | RULE | Graceful Degradation | Se parser falhar, tracker retorna lista vazia sem quebrar debate | `debate_state_tracker.py`
F10 | RULE | Tracker Encapsulation | Tracker é interno ao DebateEngine, nenhum módulo externo o acessa | `debate_engine.py`
```