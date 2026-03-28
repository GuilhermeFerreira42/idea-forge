from typing import Dict, Any
from src.agents.critic_agent import CriticAgent
from src.agents.proponent_agent import ProponentAgent
from src.core.stream_handler import ANSIStyle


class DebateEngine:
    """
    Executa o debate estruturado entre o Agente Proponente e o Agente Crítico.
    """
    
    def __init__(self, proponent: ProponentAgent, critic: CriticAgent, rounds: int = 3):
        self.proponent = proponent
        self.critic = critic
        self.num_rounds = rounds
        self.debate_transcript = []

    def run(self, first_input: str, context: str = "", report_filename: str = None) -> str:
        """
        Executa os ciclos de debate alternados usando contexto do Blackboard.
        first_input: Geralmente o PRD ou a Ideia Refinada.
        context: Contexto acumulado de outros artefatos (ex: System Design).
        """
        print(
            f"\n{ANSIStyle.BOLD}{ANSIStyle.YELLOW}"
            f"{'═' * 50}\n"
            f"  ⚔️  INICIANDO DEBATE ESTRUTURADO "
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
                f"│  Round {r}/{self.num_rounds}                                      │\n"
                f"└{'─' * 48}┘"
                f"{ANSIStyle.RESET}"
            )
            
            # ── Proponent turn ──
            print(
                f"\n{ANSIStyle.BOLD}{ANSIStyle.GREEN}"
                f"🛡️  PROPONENTE — formulando defesa arquitetural..."
                f"{ANSIStyle.RESET}"
            )
            # FASE 3.1: O Proponente foca na crítica anterior
            last_critique = self.debate_transcript[-1] if self.debate_transcript else "Inicie a defesa técnica."
            
            prop_response = self.proponent.defend_artifact(
                artifact_content=first_input, 
                critique=last_critique,
                context=initial_context # Proponente sempre vê o PRD base
            )
            self.debate_transcript.append(f"Proponente:\n{prop_response}")
            
            # Janela deslizante: O contexto para o próximo agente foca no que acabou de ser dito
            current_context = f"{initial_context}\n\nÚltima Resposta (🛡️ Proponente):\n{prop_response}\n"
            
            if report_filename:
                with open(report_filename, "a", encoding="utf-8") as f:
                    f.write(f"\n## 🛡️ Agente: PROPONENTE (Round {r})\n")
                    f.write(prop_response + "\n\n---\n")
            
            # ── Critic turn ──
            print(
                f"\n{ANSIStyle.BOLD}{ANSIStyle.YELLOW}"
                f"⚡ CRÍTICO — analisando vulnerabilidades e lacunas..."
                f"{ANSIStyle.RESET}"
            )
            
            crit_response = self.critic.review_artifact(
                artifact_content=first_input,
                artifact_type="document",
                context=current_context
            )
            self.debate_transcript.append(f"Crítico:\n{crit_response}")
            
            # Atualiza contexto para o próximo round (janela deslizante)
            current_context = f"{initial_context}\n\nÚltima Crítica (⚡ Crítico):\n{crit_response}\n"
            
            if report_filename:
                with open(report_filename, "a", encoding="utf-8") as f:
                    f.write(f"\n## ⚡ Agente: CRÍTICO (Round {r})\n")
                    f.write(crit_response + "\n\n---\n")

        # ═══ FASE 9.0: Injetar seção estruturada de Decisões Aplicáveis ═══
        decisions_section = self._extract_decisions_from_transcript()
        self.debate_transcript.append(decisions_section)
        # ═══ FIM FASE 9.0 ═══

        print(
            f"\n{ANSIStyle.BOLD}{ANSIStyle.GREEN}"
            f"{'═' * 50}\n"
            f" ✅ DEBATE CONCLUÍDO — {self.num_rounds} rounds completos\n"
            f"{'═' * 50}"
            f"{ANSIStyle.RESET}\n"
        )

        return "\n\n".join(self.debate_transcript)

    def _extract_decisions_from_transcript(self) -> str:
        """
        FASE 9.0: Extrai decisões estruturadas dos "Pontos Aceitos"
        de cada round do Proponente.

        Retorna seção Markdown com tabela de decisões para facilitar
        a consolidação pelo TASK_07.
        """
        decisions_section = (
            "\n## Decisões Aplicáveis (Síntese)\n\n"
            "| Round | Tipo | Decisão | Justificativa |\n"
            "|---|---|---|---|\n"
        )

        decisions_found = 0

        for entry_idx, entry in enumerate(self.debate_transcript):
            # Apenas entradas do Proponente contêm "Pontos Aceitos"
            if not entry.startswith("Proponente:"):
                continue

            # Calcular número do round (cada round = 1 Proponente + 1 Crítico)
            round_num = (entry_idx // 2) + 1

            # Extrair seção "Pontos Aceitos"
            if "## Pontos Aceitos" in entry:
                parts = entry.split("## Pontos Aceitos")
                if len(parts) > 1:
                    accepted_block = parts[1]
                    # Cortar na próxima seção ## se existir
                    if "##" in accepted_block[1:]:
                        next_section = accepted_block.index("##", 1)
                        accepted_block = accepted_block[:next_section]

                    for line in accepted_block.strip().split('\n'):
                        line = line.strip().lstrip('- ')
                        if line and len(line) > 10 and not line.startswith('#'):
                            # Limpar e truncar
                            decision_text = line[:120]
                            decisions_section += (
                                f"| R{round_num} | ACEITO | "
                                f"{decision_text} | Proponente concordou |\n"
                            )
                            decisions_found += 1

            # Extrair seção "Melhorias Propostas" (tabela)
            if "## Melhorias Propostas" in entry:
                parts = entry.split("## Melhorias Propostas")
                if len(parts) > 1:
                    improvements_block = parts[1]
                    if "##" in improvements_block[1:]:
                        next_section = improvements_block.index("##", 1)
                        improvements_block = improvements_block[:next_section]

                    # Extrair linhas de tabela (excluindo header e separador)
                    table_lines = [
                        l for l in improvements_block.strip().split('\n')
                        if l.strip().startswith('|')
                        and '---|' not in l
                        and 'Área' not in l  # Excluir header
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
