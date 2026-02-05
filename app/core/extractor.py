from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

import pdfplumber
from pypdf import PdfReader
from docx import Document


@dataclass
class ExtractedChunk:
    source_file: str
    source_ext: str
    page: Optional[int]
    section: Optional[str]
    order: Optional[int]
    text: str
    extra: Optional[Dict[str, Any]] = None


class ResumeExtractor:
    """
    Extracts text from PDF and DOCX resumes.
    Produces ExtractedChunk objects to keep file/page/order metadata.
    """

    def extract_docx(self, path: str | Path) -> List[ExtractedChunk]:
        path = Path(path)
        doc = Document(str(path))
        chunks: List[ExtractedChunk] = []

        order = 0
        for para in doc.paragraphs:
            txt = (para.text or "").strip()
            if not txt:
                continue
            chunks.append(
                ExtractedChunk(
                    source_file=str(path),
                    source_ext=".docx",
                    page=None,
                    section=None,
                    order=order,
                    text=txt,
                    extra=None,
                )
            )
            order += 1

        return chunks

    def extract_pdf(self, path: str | Path) -> List[ExtractedChunk]:
        path = Path(path)
        chunks: List[ExtractedChunk] = []

        # Try pdfplumber first (often best layout)
        try:
            with pdfplumber.open(str(path)) as pdf:
                for pageno, page in enumerate(pdf.pages):
                    txt = (page.extract_text() or "").strip()
                    if txt:
                        chunks.append(
                            ExtractedChunk(
                                source_file=str(path),
                                source_ext=".pdf",
                                page=pageno,
                                section=None,
                                order=pageno,
                                text=txt,
                                extra=None,
                            )
                        )
            if chunks:
                return chunks
        except Exception:
            pass

        # Fallback to pypdf
        try:
            reader = PdfReader(str(path))
            for pageno, page in enumerate(reader.pages):
                txt = (page.extract_text() or "").strip()
                if txt:
                    chunks.append(
                        ExtractedChunk(
                            source_file=str(path),
                            source_ext=".pdf",
                            page=pageno,
                            section=None,
                            order=pageno,
                            text=txt,
                            extra=None,
                        )
                    )
        except Exception as e:
            chunks.append(
                ExtractedChunk(
                    source_file=str(path),
                    source_ext=".pdf",
                    page=None,
                    section=None,
                    order=None,
                    text="",
                    extra={"skipped": True, "reason": f"pdf parse failed: {e}"},
                )
            )

        return chunks

    def load_folder(self, folder: str | Path) -> List[ExtractedChunk]:
        folder = Path(folder)
        if not folder.exists():
            raise FileNotFoundError(f"Resumes folder not found: {folder}")

        out: List[ExtractedChunk] = []
        for f in folder.rglob("*"):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            if ext == ".pdf":
                out.extend(self.extract_pdf(f))
            elif ext == ".docx":
                out.extend(self.extract_docx(f))

        return out
