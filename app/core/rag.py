from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import faiss

from app.core.chunker import RAGChunk
from app.core.embeddings import OllamaEmbedder


@dataclass
class RetrievedChunk:
    chunk_id: str
    score: float
    text: str
    metadata: Dict[str, Any]


class FAISSRAGStore:
    def __init__(self, embedder: OllamaEmbedder, store_dir: str | Path = "./vector_store"):
        self.embedder = embedder
        self.store_dir = Path(store_dir)
        self.index: Optional[faiss.Index] = None
        self.ids: List[str] = []
        self.texts: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.dim: Optional[int] = None

    def build(self, chunks: List[RAGChunk], batch_size: int = 32) -> None:
        if not chunks:
            raise ValueError("No chunks provided to build FAISS index.")

        vectors = self._embed_chunks(chunks, batch_size=batch_size)
        self.dim = vectors.shape[1]
        faiss.normalize_L2(vectors)

        index = faiss.IndexFlatIP(self.dim)
        index.add(vectors)

        self.index = index
        self.ids = [c.chunk_id for c in chunks]
        self.texts = [c.text for c in chunks]
        self.metadatas = [c.metadata for c in chunks]

    def save(self) -> None:
        if self.index is None:
            raise ValueError("Index is not built.")

        self.store_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.store_dir / "index.faiss"))

        meta = {"dim": self.dim, "ids": self.ids, "texts": self.texts, "metadatas": self.metadatas}
        (self.store_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> None:
        idx = self.store_dir / "index.faiss"
        meta = self.store_dir / "meta.json"
        if not idx.exists() or not meta.exists():
            raise FileNotFoundError(f"Vector store not found in {self.store_dir}")
        self.index = faiss.read_index(str(idx))
        data = json.loads(meta.read_text(encoding="utf-8"))
        self.dim = int(data["dim"])
        self.ids = list(data["ids"])
        self.texts = list(data["texts"])
        self.metadatas = list(data["metadatas"])

    def retrieve(self, query: str, top_k: int = 8) -> List[RetrievedChunk]:
        if self.index is None:
            raise ValueError("Index not loaded/built.")

        qv = self.embedder.embed_texts([query])
        faiss.normalize_L2(qv)
        scores, idxs = self.index.search(qv, top_k)

        out: List[RetrievedChunk] = []
        for score, i in zip(scores[0].tolist(), idxs[0].tolist()):
            if i < 0:
                continue
            out.append(RetrievedChunk(self.ids[i], float(score), self.texts[i], self.metadatas[i]))
        return out

    def _embed_chunks(self, chunks: List[RAGChunk], batch_size: int = 32) -> np.ndarray:
        texts = [c.text for c in chunks]
        vecs: List[np.ndarray] = []
        for start in range(0, len(texts), batch_size):
            vecs.append(self.embedder.embed_texts(texts[start:start + batch_size]))
        return np.vstack(vecs).astype("float32")
