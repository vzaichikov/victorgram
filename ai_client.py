import os
import time
import logging
import requests
from openai import OpenAI

try:
    import whisper  # type: ignore
except Exception:
    whisper = None


class AIClient:
    def __init__(self, api_type=None):
        if api_type is None:
            self.use_ollama = os.getenv("USE_OLLAMA", "false").lower() in ["1", "true", "yes"]
        else:
            self.use_ollama = api_type.lower() == "ollama"

        if self.use_ollama:
            api_key = os.getenv("OLLAMA_API_KEY")
            base_url = os.getenv("OLLAMA_API_BASE_URL")
            self.model = os.getenv("OLLAMA_API_MODEL", "gemma3:27b")
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_API_BASE_URL")
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

        self.client = OpenAI(api_key=api_key, base_url=base_url)

        self.unload_timeout = int(os.getenv("MODEL_UNLOAD_TIMEOUT", "1800"))
        self.last_used_time = time.time()
        self._whisper_model = None

        self.load_models()

    def load_whisper(self):
        if whisper is None:
            raise RuntimeError("whisper package not installed")

        model_name = os.getenv("WHISPER_MODEL", "turbo")
        print(f"ℹ️ Loading Whisper model {model_name}")
        logging.info("Loading Whisper model '%s'", model_name)
        self._whisper_model = whisper.load_model(model_name, device=os.getenv("WHISPER_DEVICE"))
        print(f"✅ Loaded Whisper model {model_name}")
        logging.info("Whisper model '%s' loaded", model_name)

    def load_models(self):
        self.load_whisper()

        if self.use_ollama:
            try:
                url = str(self.client.base_url).rstrip("/v1/") + "/api/tags"
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                names = [m.get("name") for m in data.get("models", [])]
                short = self.model.split(":")[0]
                if self.model not in names and short not in names:
                    raise RuntimeError(f"Ollama model '{self.model}' not found")
                print(f"✅ Ollama model {self.model} available")
                logging.info("Ollama model '%s' available", self.model)
            except Exception as e:
                raise RuntimeError(f"Failed to verify Ollama model '{self.model}': {e}")

    def _maybe_unload_models(self):
        if self.last_used_time and self.unload_timeout > 0:
            if time.time() - self.last_used_time > self.unload_timeout:
                if self._whisper_model is not None:
                    self._whisper_model = None
                    logging.info("Whisper model unloaded due to inactivity")

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.ogg") -> str:
        import tempfile

        self._maybe_unload_models()

        if whisper is None:
            raise RuntimeError("whisper package not installed")

        if self._whisper_model is None:
            self.load_whisper()

        suffix = os.path.splitext(filename)[1] or ".ogg"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp.close()
            result = self._whisper_model.transcribe(audio=tmp.name)
        finally:
            os.remove(tmp.name)

        self.last_used_time = time.time()

        return result.get("text", "").strip()

    def complete(self, messages, max_tokens=None, temperature=None, top_p=None):
        self._maybe_unload_models()

        if max_tokens is None:
            env_val = os.getenv("AI_MAX_TOKENS", 512)
            if env_val is not None:
                max_tokens = int(env_val)
        if temperature is None:
            env_val = os.getenv("AI_TEMPERATURE", 0.8)
            if env_val is not None:
                temperature = float(env_val)
        if top_p is None:
            env_val = os.getenv("AI_TOP_P", 0.9)
            if env_val is not None:
                top_p = float(env_val)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p
        )
        self.last_used_time = time.time()
        return response.choices[0].message.content.strip()
