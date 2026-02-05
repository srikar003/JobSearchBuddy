from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from app.core.extractor import ExtractedChunk


@dataclass
class RAGChunk:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]


class Chunker:
    def __init__(
        self,
        max_chars: int = 2800,
        overlap_chars: int = 400,
        min_chunk_chars: int = 120
    ):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.min_chunk_chars = min_chunk_chars

    def chunk(self, extracted: List[ExtractedChunk]) -> List[RAGChunk]:
        rag_chunks: List[RAGChunk] = []

        for ex in extracted:
            if ex.extra and ex.extra.get("skipped"):
                continue
            base_text = (ex.text or "").strip()
            if not base_text:
                continue

            splits = self._split_with_overlap(base_text)

            for j, piece in enumerate(splits):
                piece = piece.strip()
                if len(piece) < self.min_chunk_chars:
                    continue

                chunk_id = self._make_chunk_id(ex, j)
                metadata = {
                    "source_file": ex.source_file,
                    "source_ext": ex.source_ext,
                    "page": ex.page,
                    "section": ex.section,
                    "order": ex.order,
                    "split_index": j,
                }
                rag_chunks.append(RAGChunk(chunk_id=chunk_id, text=piece, metadata=metadata))

        return rag_chunks

    def _split_with_overlap(self, text: str) -> List[str]:
        if len(text) <= self.max_chars:
            return [text]

        chunks: List[str] = []
        start = 0
        n = len(text)

        while start < n:
            end = min(start + self.max_chars, n)
            chunk = text[start:end]

            if end < n:
                cut = self._find_nice_cut(chunk)
                if cut is not None and cut > self.min_chunk_chars:
                    end = start + cut
                    chunk = text[start:end]

            chunks.append(chunk)

            if end >= n:
                break

            start = max(0, end - self.overlap_chars)

        return chunks

    def _find_nice_cut(self, chunk: str) -> Optional[int]:
        lookback = min(350, len(chunk))
        tail = chunk[-lookback:]

        separators = ["\n", ". ", "; ", " "]
        for sep in separators:
            pos = tail.rfind(sep)
            if pos != -1:
                return len(chunk) - lookback + pos + len(sep)

        return None

    def _make_chunk_id(self, ex: ExtractedChunk, split_index: int) -> str:
        page = ex.page if ex.page is not None else 0
        order = ex.order if ex.order is not None else 0
        return f"{ex.source_file}|p{page}|o{order}|s{split_index}"
