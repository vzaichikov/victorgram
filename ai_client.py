import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(".env")

class AIClient:
    def __init__(self, api_type=None):
        if api_type is None:
            use_ollama = os.getenv("USE_OLLAMA", "false").lower() in ["1", "true", "yes"]
        else:
            use_ollama = api_type.lower() == "ollama"
        if use_ollama:
            api_key = os.getenv("OLLAMA_API_KEY")
            base_url = os.getenv("OLLAMA_API_BASE_URL")
            self.model = os.getenv("OLLAMA_API_MODEL", "gemma3:27b")
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_API_BASE_URL")
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def complete(self, messages, max_tokens=int(os.getenv("AI_MAX_TOKENS")), temperature=float(os.getenv("AI_TEMPERATURE"))):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
