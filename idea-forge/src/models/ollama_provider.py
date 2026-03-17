import requests
import json
import sys
from src.models.model_provider import ModelProvider
from src.config.settings import OLLAMA_ENDPOINT, MODEL_NAME

class OllamaProvider(ModelProvider):
    """
    Local LLM provider using Ollama HTTP API.
    """

    def __init__(self, model_name: str = MODEL_NAME, endpoint: str = OLLAMA_ENDPOINT, think: bool = False):
        self.model_name = model_name
        self.endpoint = endpoint
        self.think = think

    def generate(self, prompt: str, context: list = None, role: str = "user") -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "think": self.think
            }
        }

        full_response = ""
        try:
            response = requests.post(self.endpoint, json=payload, timeout=60, stream=True)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        chunk = data.get("response", "")
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                        full_response += chunk
                    except json.JSONDecodeError:
                        continue
            
            # Print a newline at the end of the streaming response
            print()
            return full_response
            
        except requests.exceptions.RequestException as e:
            return f"Error communicating with Ollama: {str(e)}"
