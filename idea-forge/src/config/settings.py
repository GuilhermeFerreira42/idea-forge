import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
