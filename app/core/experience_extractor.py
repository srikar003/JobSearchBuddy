from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from collections import defaultdict

from app.core.chunker import RAGChunk


DATE_RE = re.compile(
    r"(?i)\b("
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s*\d{4}"
    r"|"
    r"\d{4}"
    r")\b.*\b(present|current|\d{4})\b"
)

ROLE_HEADER_HINTS = [
    "experience", "work experience", "professional experience", "employment"
]


@dataclass
class ExperienceBlock:
    role_key: str              # stable dedupe key
    title_company: str         # header line to display
    dates: str                 # if detected
    source_files: List[str]
    bullets: List[str]
    raw_lines: List[str]


def _norm(s: str) -> str:
    return " ".join(s.lower().split()).strip()


def _looks_like_role_header(line: str) -> bool:
    l = line.strip()
    if len(l) < 8:
        return False
    # very common resume header forms
    if " — " in l or " - " in l:
        return True
    if DATE_RE.search(l):
        return True
    return False


def _is_section_header(line: str) -> bool:
    l = _norm(line)
    return any(h in l for h in ROLE_HEADER_HINTS) or l in {"experience", "work experience", "professional experience"}


def build_experience_blocks(rag_chunks: List[RAGChunk]) -> List[ExperienceBlock]:
    """
    Heuristic:
    - For each resume file, find lines that look like role headers (title/company/dates)
    - Collect subsequent bullet-like lines until next role header / section header
    - Return blocks; later we dedupe across resumes by role_key
    """
    # group lines by source_file in original-ish order if possible
    by_file = defaultdict(list)
    for c in rag_chunks:
        by_file[c.metadata.get("source_file", "unknown")].append(c)

    blocks: List[ExperienceBlock] = []

    for source_file, chunks in by_file.items():
        # keep stable order by (page, order, split_index) if present
        def sort_key(x: RAGChunk):
            md = x.metadata
            return (md.get("page") or 0, md.get("order") or 0, md.get("split_index") or 0)
        chunks.sort(key=sort_key)

        lines = []
        for c in chunks:
            # split chunk into lines
            for ln in c.text.splitlines():
                ln = ln.strip()
                if ln:
                    lines.append(ln)

        i = 0
        while i < len(lines):
            ln = lines[i]
            if _is_section_header(ln):
                i += 1
                continue

            if _looks_like_role_header(ln):
                header = ln
                dates = ""
                m = DATE_RE.search(ln)
                if m:
                    dates = m.group(0)

                bullets = []
                raw_lines = [header]

                j = i + 1
                while j < len(lines):
                    nxt = lines[j].strip()
                    if _is_section_header(nxt):
                        break
                    if _looks_like_role_header(nxt):
                        break

                    # bullet detection: "- " or "•" or leading verb-ish lines
                    if nxt.startswith(("- ", "•")):
                        bullets.append(nxt.lstrip("•").lstrip("-").strip())
                        raw_lines.append(nxt)
                    else:
                        # treat short lines as continuation; keep as raw evidence
                        raw_lines.append(nxt)

                    j += 1

                if bullets:
                    role_key = _norm(header)
                    blocks.append(
                        ExperienceBlock(
                            role_key=role_key,
                            title_company=header,
                            dates=dates,
                            source_files=[source_file],
                            bullets=bullets,
                            raw_lines=raw_lines,
                        )
                    )
                i = j
            else:
                i += 1

    return blocks


def dedupe_and_merge_blocks(blocks: List[ExperienceBlock]) -> List[ExperienceBlock]:
    """
    Merge blocks that look identical across multiple resumes.
    Keep union of bullets, preserve most complete header.
    """
    merged: Dict[str, ExperienceBlock] = {}

    for b in blocks:
        key = b.role_key
        if key not in merged:
            merged[key] = b
        else:
            existing = merged[key]
            # merge sources
            existing.source_files = sorted(list(set(existing.source_files + b.source_files)))
            # merge bullets (dedupe)
            seen = set(_norm(x) for x in existing.bullets)
            for bt in b.bullets:
                n = _norm(bt)
                if n not in seen:
                    existing.bullets.append(bt)
                    seen.add(n)
            # choose longer header as “more complete”
            if len(b.title_company) > len(existing.title_company):
                existing.title_company = b.title_company
            if len(b.dates) > len(existing.dates):
                existing.dates = b.dates

    # Keep deterministic order
    return list(merged.values())
