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
