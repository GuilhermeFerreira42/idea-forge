from typing import Dict, Any
from src.agents.critic_agent import CriticAgent
from src.agents.proponent_agent import ProponentAgent

class DebateEngine:
    """
    Executa o debate estruturado entre o Agente Proponente e o Agente Crítico.
    """
    
    def __init__(self, proponent: ProponentAgent, critic: CriticAgent, rounds: int = 3):
        self.proponent = proponent
        self.critic = critic
        self.num_rounds = rounds
        self.debate_transcript = []

    def run(self, refined_idea: str, report_filename: str = None) -> str:
        """
        Executa os ciclos de debate alternados.
        """
        print("\n--- INICIANDO DEBATE ESTRUTURADO ---")
        
        context_accumulator = f"Initial Idea: {refined_idea}\n\n"
        
        for r in range(1, self.num_rounds + 1):
            print(f"\n[Round {r}/{self.num_rounds}]")
            
            # Proponent turn
            print("\n" + "="*40)
            print("=== PROPONENTE ===")
            print("="*40)
            prop_response = self.proponent.propose(refined_idea, context_accumulator)
            self.debate_transcript.append(f"Proponente:\n{prop_response}")
            context_accumulator += f"Proponent Proposal:\n{prop_response}\n\n"
            
            if report_filename:
                with open(report_filename, "a", encoding="utf-8") as f:
                    f.write("\n## 👤 Agente: PROPONENTE\n")
                    f.write(prop_response + "\n\n---\n")
            
            # Critic turn
            # Mocking history here to reuse critic analyze signature slightly adapted for debate context
            class MockHistory:
                def get_context_string(self):
                    return context_accumulator
                def get_history(self):
                    return []
                    
            print("\n" + "="*40)
            print("=== CRÍTICO ===")
            print("="*40)
            crit_response = self.critic.analyze(refined_idea, MockHistory())
            self.debate_transcript.append(f"Crítico:\n{crit_response}")
            context_accumulator += f"Critic Critique:\n{crit_response}\n\n"
            
            if report_filename:
                with open(report_filename, "a", encoding="utf-8") as f:
                    f.write("\n## 👤 Agente: CRÍTICO\n")
                    f.write(crit_response + "\n\n---\n")

        print("\n--- DEBATE CONCLUÍDO ---\n")
        return "\n\n".join(self.debate_transcript)
