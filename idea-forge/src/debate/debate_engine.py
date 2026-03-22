from typing import Dict, Any
from src.agents.critic_agent import CriticAgent
from src.agents.proponent_agent import ProponentAgent
from src.core.stream_handler import ANSIStyle
from src.core.pipeline_logger import get_pipeline_logger


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
            # ═══ LOGGER: Round iniciado ═══
            logger = get_pipeline_logger()
            if logger:
                logger.log("DEBATE_ROUND_START", {
                    "round": r,
                    "total_rounds": self.num_rounds,
                })

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

            # ═══ LOGGER: Proponente respondeu ═══
            if logger:
                logger.log("DEBATE_PROPONENT", {
                    "round": r,
                    "response_chars": len(prop_response),
                    "response_tokens_est": len(prop_response) // 4,
                })
            
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

            # ═══ LOGGER: Crítico respondeu ═══
            if logger:
                logger.log("DEBATE_CRITIC", {
                    "round": r,
                    "response_chars": len(crit_response),
                    "response_tokens_est": len(crit_response) // 4,
                })
            
            # Atualiza contexto para o próximo round (janela deslizante)
            current_context = f"{initial_context}\n\nÚltima Crítica (⚡ Crítico):\n{crit_response}\n"
            
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
