from __future__ import annotations

import os
import numpy as np
import requests

# Allow optional loading of a .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # dotenv is optional; environment variables can be set directly
    pass

DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
DEFAULT_TIMEOUT_S = int(os.getenv("TIMEOUT_S", "120"))


class OllamaEmbedder:
    def __init__(self, model: str | None = None, host: str | None = None, timeout_s: int | None = None):
        self.model = model or DEFAULT_EMBED_MODEL
        self.host = (host or DEFAULT_OLLAMA_HOST).rstrip("/")
        self.timeout_s = int(timeout_s or DEFAULT_TIMEOUT_S)

    def embed_texts(self, texts):
        vectors = []
        for t in texts:
            vectors.append(self._embed_one(t))
        return np.vstack(vectors).astype("float32")

    def _embed_one(self, text: str) -> np.ndarray:
        url = f"{self.host}/api/embeddings"
        payload = {"model": self.model, "prompt": text}
        r = requests.post(url, json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        emb = data.get("embedding") or data.get("embeddings")
        if emb is None:
            raise ValueError(f"Missing embedding in response: {data}")
        # Some providers return nested arrays; pick first if necessary
        if isinstance(emb, list) and len(emb) and isinstance(emb[0], list):
            emb = emb[0]
        return np.array(emb, dtype="float32")

    def health_check(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=10)
            return r.status_code == 200
        except Exception:
            return False
