import sys
import os
from unittest.mock import MagicMock

# Ajustar path para incluir a raiz do projeto (onde está a pasta 'src')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.sectional_generator import SectionalGenerator, SectionPass
from src.models.model_provider import ModelProvider, GenerationResult

def test_sectional_generator_init():
    provider = MagicMock(spec=ModelProvider)
    generator = SectionalGenerator(provider=provider, direct_mode=True)
    assert generator.provider == provider
    assert generator.direct_mode is True
    print("✅ SectionalGenerator instanciado com sucesso.")

def test_build_prompt():
    provider = MagicMock(spec=ModelProvider)
    generator = SectionalGenerator(provider=provider, direct_mode=True)
    
    section_pass = SectionPass(
        pass_id="test_p1",
        sections=["## Seção 1"],
        template="## Seção 1\nConteúdo",
        example="## Seção 1\nExemplo",
        instruction="Gere a seção 1",
        max_output_tokens=500
    )
    
    prompt = generator._build_pass_prompt(
        section_pass=section_pass,
        user_input="Ideia de teste",
        context="Contexto de teste",
        previous_output="Output anterior",
        pass_number=1,
        total_passes=1
    )
    
    assert "System:" in prompt
    assert "## Seção 1" in prompt
    assert "Ideia de teste" in prompt
    assert "Contexto de teste" in prompt
    assert "Gere a seção 1" in prompt
    assert "[Pass 1/1]" in prompt
    print("✅ Prompt construído corretamente.")

def test_clean_output():
    provider = MagicMock(spec=ModelProvider)
    generator = SectionalGenerator(provider=provider)
    
    raw_output = "Certamente! Aqui está a seção solicitada.\n\n## Seção 1\nConteúdo <think>pensamento</think>"
    cleaned = generator._clean_pass_output(raw_output)
    
    assert "Certamente" not in cleaned
    assert "## Seção 1" in cleaned
    assert "<think>" not in cleaned
    assert "pensamento" not in cleaned
    print("✅ Limpeza de output funcionando.")

if __name__ == "__main__":
    try:
        test_sectional_generator_init()
        test_build_prompt()
        test_clean_output()
        print("\n🚀 Verificação estática concluída com sucesso!")
    except Exception as e:
        print(f"\n❌ Erro na verificação: {str(e)}")
        sys.exit(1)
