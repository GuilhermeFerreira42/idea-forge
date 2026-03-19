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
        
        # O contexto inicial inclui o que foi passado e o input principal
        current_context = f"Main Subject:\n{first_input}\n\nRelated Context:\n{context}\n\n"
        
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
            # Na Fase 3, usamos o método defend_artifact se disponível
            prop_response = self.proponent.defend_artifact(
                artifact_content=first_input, 
                critique="Analyze the current state and defend the technical direction.",
                context=current_context
            )
            self.debate_transcript.append(f"Proponente:\n{prop_response}")
            current_context += f"Proponent Defense (R{r}):\n{prop_response}\n\n"
            
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
            current_context += f"Critic Critique (R{r}):\n{crit_response}\n\n"
            
            if report_filename:
                with open(report_filename, "a", encoding="utf-8") as f:
                    f.write(f"\n## ⚡ Agente: CRÍTICO (Round {r})\n")
                    f.write(crit_response + "\n\n---\n")

        print(
            f"\n{ANSIStyle.BOLD}{ANSIStyle.GREEN}"
            f"{'═' * 50}\n"
            f"  ✅ DEBATE CONCLUÍDO — {self.num_rounds} rounds completos\n"
            f"{'═' * 50}"
            f"{ANSIStyle.RESET}\n"
        )
        return "\n\n".join(self.debate_transcript)
