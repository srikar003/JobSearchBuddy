from __future__ import annotations

import numpy as np
import requests

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_EMBED_MODEL = "nomic-embed-text"


class OllamaEmbedder:
    def __init__(self, model: str = DEFAULT_EMBED_MODEL, host: str = DEFAULT_OLLAMA_HOST, timeout_s: int = 120):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout_s = timeout_s

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
        emb = data.get("embedding")
        if emb is None:
            raise ValueError(f"Missing embedding in response: {data}")
        return np.array(emb, dtype="float32")

    def health_check(self) -> bool:
        r = requests.get(f"{self.host}/api/tags", timeout=10)
        return r.status_code == 200
