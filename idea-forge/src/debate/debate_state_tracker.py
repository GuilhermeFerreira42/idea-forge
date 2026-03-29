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
    """
    
    def __init__(self):
        self.issues: Dict[str, IssueRecord] = {}
        self.current_round: int = 0
        self._next_auto_id: int = 1
        self._seen_descriptions: Set[str] = set()  # Dedup por descrição normalizada
    
    def extract_issues_from_critique(self, critique_text: str, round_num: int) -> List[str]:
        """
        Parseia texto do Critic e registra novos issues.
        """
        if not critique_text:
            return []
        
        self.current_round = round_num
        new_ids = []
        
        # ═══ Estratégia 1: Tabela de issues ═══
        # Tentamos primeiro o padrão de 6 colunas
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
        """
        if not defense_text:
            return []
        
        resolved_ids = []
        accepted_block = self._extract_section_content(defense_text, "## Pontos Aceitos")
        if not accepted_block:
            return []
        
        for iss_id, record in self.issues.items():
            if record.status != "OPEN":
                continue
            
            matched = False
            match_reason = ""
            
            # Match 1: ID explícito (ex: "ISS-01" no texto)
            if iss_id.upper() in accepted_block.upper():
                matched = True
                match_reason = f"ID {iss_id} mencionado nos Pontos Aceitos"
            
            # Match 2: Descrição parcial (prefixo de 20 chars para robustez)
            if not matched:
                desc_normalized = self._normalize_text(record.description[:40])
                if desc_normalized and len(desc_normalized) > 10:
                    block_normalized = self._normalize_text(accepted_block)
                    if desc_normalized in block_normalized:
                        matched = True
                        match_reason = f"Descrição similar encontrada nos Pontos Aceitos"
                    elif desc_normalized[:20] in block_normalized:
                        matched = True
                        match_reason = f"Prefixo da descrição similar encontrado"
            
            # Match 3: Categoria mencionada com severidade HIGH
            if not matched:
                category_lower = record.category.lower()
                category_pt = {
                    "security": "segurança", "correctness": "correção",
                    "completeness": "completude", "consistency": "consistência",
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
        
        # Deferrals
        improvements_block = self._extract_section_content(defense_text, "## Melhorias Propostas")
        if improvements_block:
            for iss_id, record in self.issues.items():
                if record.status != "OPEN": continue
                defer_keywords = ["v2", "futuro", "postergar", "adiado", "backlog"]
                if any(kw in improvements_block.lower() for kw in defer_keywords):
                    if iss_id.upper() in improvements_block.upper():
                        record.status = "DEFERRED"
                        record.round_resolved = round_num
                        record.resolution = "Deferido para versão futura"
                        resolved_ids.append(iss_id)
        
        return resolved_ids
    
    def get_open_issues(self) -> List[IssueRecord]:
        severity_order = {"HIGH": 0, "MED": 1, "LOW": 2}
        open_issues = [r for r in self.issues.values() if r.status == "OPEN"]
        return sorted(open_issues, key=lambda x: severity_order.get(x.severity, 3))
    
    def get_resolved_issues(self) -> List[IssueRecord]:
        return [r for r in self.issues.values() if r.status != "OPEN"]
    
    def get_open_issues_prompt(self) -> str:
        open_issues = self.get_open_issues()
        if not open_issues: return "ESTADO DO DEBATE: Nenhum issue aberto de rodadas anteriores.\n"
        lines = ["═══ ISSUES JÁ REGISTRADOS (NÃO repita) ═══\n", "NÃO os repita. Foque EXCLUSIVAMENTE em NOVOS problemas.\n", "| ID | Severidade | Categoria | Descrição | Rodada |", "|---|---|---|---|---|"]
        for issue in open_issues:
            desc_short = issue.description[:80].replace('|', '/')
            lines.append(f"| {issue.issue_id} | {issue.severity} | {issue.category} | {desc_short} | R{issue.round_raised} |")
        lines.append(f"\nTotal de issues abertos: {len(open_issues)}\n═══ FIM DOS ISSUES REGISTRADOS ═══\n")
        return "\n".join(lines)
    
    def get_issues_for_proponent(self) -> str:
        open_issues = self.get_open_issues()
        if not open_issues: return "ESTADO DO DEBATE: Todos os issues anteriores foram resolvidos.\n"
        lines = ["═══ ISSUES QUE VOCÊ DEVE ENDEREÇAR ═══\n"]
        for issue in open_issues:
            desc_short = issue.description[:100].replace('|', '/')
            action_hint = " ← PRIORITÁRIO" if issue.severity == "HIGH" else ""
            lines.append(f"- **{issue.issue_id}** [{issue.severity}/{issue.category}]: {desc_short}{action_hint}")
        lines.append("\nResponda com '## Pontos Aceitos' listando-os.\n")
        return "\n".join(lines)
    
    def get_consolidation_summary(self) -> str:
        lines = ["\n## Estado Final do Debate\n"]
        resolved = self.get_resolved_issues()
        open_issues = self.get_open_issues()
        lines.append(f"- **Total de issues rastreados:** {len(self.issues)}")
        lines.append(f"- **Resolvidos/Aceitos:** {len(resolved)}")
        lines.append(f"- **Ainda abertos:** {len(open_issues)}")
        lines.append(f"- **Bloqueantes (HIGH+OPEN):** {'⚠️ SIM' if self.has_blocking_issues() else '✅ NÃO'}\n")
        if resolved:
            lines.append("### Issues Resolvidos\n| ID | Severidade | Categoria | Status | Round |\n|---|---|---|---|---|")
            for r in resolved:
                lines.append(f"| {r.issue_id} | {r.severity} | {r.category} | {r.status} | R{r.round_raised}→R{r.round_resolved or '?'} |")
        if open_issues:
            lines.append("\n### ⚠️ Issues NÃO Resolvidos\n| ID | Severidade | Categoria | Descrição | Rodada |\n|---|---|---|---|---|")
            for o in open_issues:
                lines.append(f"| {o.issue_id} | {o.severity} | {o.category} | {o.description[:80].replace('|', '/')} | R{o.round_raised} |")
        else:
            lines.append("### ✅ Todos os issues foram resolvidos durante o debate.")
        return "\n".join(lines)
    
    def has_blocking_issues(self) -> bool:
        return any(i.severity == "HIGH" and i.status == "OPEN" for i in self.issues.values())
    
    def get_stats(self) -> Dict:
        return {"total": len(self.issues), "open": len(self.get_open_issues()), "resolved": len(self.get_resolved_issues()), "has_blocking": self.has_blocking_issues(), "rounds_tracked": self.current_round}
    
    def _parse_issue_table(self, text: str, round_num: int) -> List[str]:
        new_ids = []
        # Tenta padrão 6 colunas
        p6 = r'\|\s*(ISS-\d+)\s*\|\s*(HIGH|MED|MEDIUM|LOW)\s*\|\s*(\w+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]*)\|'
        found_6col = False
        for m in re.finditer(p6, text, re.IGNORECASE):
            iss_id = m.group(1).upper()
            full_desc = f"{m.group(4).strip()}: {m.group(5).strip()}"
            if self._register_issue(iss_id, self._normalize_severity(m.group(2)), m.group(3).strip().upper(), full_desc, round_num):
                new_ids.append(iss_id)
            found_6col = True
        
        # Tenta padrão flex se não achou nada ou em complemento (mas o blueprint sugere 'if not table_ids')
        # Para evitar capturar a mesma linha duas vezes, o finditer em pattern_flex dispararia apenas
        # se as IDs não estivessem já registradas.
        p_flex = r'\|\s*(ISS-\d+)\s*\|\s*(HIGH|MED|MEDIUM|LOW)\s*\|\s*(\w+)\s*\|\s*([^|]+)\|'
        for m in re.finditer(p_flex, text, re.IGNORECASE):
            iss_id = m.group(1).upper()
            if self._register_issue(iss_id, self._normalize_severity(m.group(2)), m.group(3).strip().upper(), m.group(4).strip(), round_num):
                new_ids.append(iss_id)
        
        return new_ids

    def _parse_issue_bullets(self, text: str, round_num: int) -> List[str]:
        new_ids = []
        patterns = [r'-\s*\[(HIGH|MED|MEDIUM|LOW)\]\s*(.+?)(?:\r?\n|$)', r'-\s*(HIGH|MED|MEDIUM|LOW)\s*[:\—\-]\s*(.+?)(?:\r?\n|$)']
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                iss_id = self._generate_auto_id()
                if self._register_issue(iss_id, self._normalize_severity(m.group(1)), "GENERAL", m.group(2).strip(), round_num):
                    new_ids.append(iss_id)
        return new_ids
    
    def _register_issue(self, iss_id: str, severity: str, category: str, description: str, round_num: int) -> bool:
        if iss_id in self.issues: return False
        desc_key = self._normalize_text(description[:60])
        if desc_key in self._seen_descriptions and len(desc_key) > 20: return False
        self.issues[iss_id] = IssueRecord(iss_id, severity, category, description[:200], "OPEN", round_num)
        if desc_key: self._seen_descriptions.add(desc_key)
        return True
    
    def _generate_auto_id(self) -> str:
        while f"ISS-{self._next_auto_id:02d}" in self.issues: self._next_auto_id += 1
        iss_id = f"ISS-{self._next_auto_id:02d}"
        self._next_auto_id += 1 # Agora incrementa corretamente
        return iss_id
    
    def _normalize_severity(self, s: str) -> str:
        s = s.strip().upper()
        return "MED" if s == "MEDIUM" else s if s in ("HIGH", "MED", "LOW") else "MED"
    
    def _normalize_text(self, t: str) -> str:
        return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', t.lower().strip())) if t else ""
    
    def _extract_section_content(self, text: str, heading: str) -> str:
        m = re.search(re.escape(heading) + r'[ \t]*\r?\n(.*?)(?=\n## |\r\n## |\Z)', text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""
