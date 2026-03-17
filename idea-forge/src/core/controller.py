import sys
from src.conversation.conversation_manager import ConversationManager
from src.agents.critic_agent import CriticAgent
from src.agents.proponent_agent import ProponentAgent
from src.debate.debate_engine import DebateEngine
from src.planning.plan_generator import PlanGenerator
from src.models.model_provider import ModelProvider

class AgentController:
    """
    Orquestra o fluxo completo do sistema IdeaForge.
    """
    
    def __init__(self, provider: ModelProvider):
        self.provider = provider
        self.conversation = ConversationManager()
        self.critic = CriticAgent(provider)
        self.proponent = ProponentAgent(provider)
        self.debate_engine = DebateEngine(self.proponent, self.critic, rounds=3)
        self.plan_generator = PlanGenerator(provider)

    def run_pipeline(self, initial_idea: str, report_filename: str = None) -> str:
        """
        Executes the main pipeline:
        1. Critic Analysis
        2. Refinement Loop
        3. Debate
        4. Plan Generation
        """
        # Step 1: Initial conversation
        self.conversation.add_message("user", f"My initial idea is: {initial_idea}")
        
        from src.cli.main import display_response, ask_approval
        
        # Refinement Loop
        while True:
            print("\n⚙️ [Sistema] Enviando ideia para análise do Agente Crítico...")
            critique = self.critic.analyze(initial_idea, self.conversation)
            
            display_response("Critic Agent", critique)
            self.conversation.add_message("critic", critique)
            
            # Step 2: User Approval
            approved = ask_approval()
            if approved:
                print("\n✅ [Sistema] Ideia aprovada. Avançando para o debate...")
                break
            else:
                print("\n❌ [Sistema] Você decidiu refinar. Por favor, responda aos pontos levantados ou explique melhor a ideia:")
                user_refinement = input("> ")
                if not user_refinement:
                    print("[Sistema] Refinamento vazio. Encerrando o pipeline.")
                    sys.exit(0)
                self.conversation.add_message("user", user_refinement)
                # Keep looping

        # Step 3: Debate
        debate_result = self.debate_engine.run(initial_idea, report_filename)
        
        # Step 4: Plan Generation
        final_plan = self.plan_generator.generate_plan(debate_result, initial_idea)
        
        if report_filename:
            with open(report_filename, "a", encoding="utf-8") as f:
                f.write("\n# 📋 Plano de Desenvolvimento Técnico Final\n\n")
                f.write(final_plan + "\n")
        
        return final_plan
