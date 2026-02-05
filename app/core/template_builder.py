from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
from collections import defaultdict


CANONICAL_ORDER = [
    "NAME",
    "CONTACT",
    "PROFESSIONAL SUMMARY",
    "SKILLS",
    "WORK EXPERIENCE",
    "ACADEMIC EDUCATION",
    "ACADEMIC PROJECTS",
    "PROJECTS",
    "ACHIEVEMENTS",
]


@dataclass
class CanonicalTemplate:
    name: str
    contact: str
    sections: Dict[str, str]

    def render(self) -> str:
        out = []
        out.append(self.name.strip())
        out.append(self.contact.strip())
        for sec in CANONICAL_ORDER[2:]:
            body = self.sections.get(sec, "").strip()
            if not body:
                continue
            out.append(sec)
            out.append(body)
        return "\n".join(out).strip()


def build_canonical_template(parsed_resumes: List[Dict[str, str]]) -> CanonicalTemplate:
    """
    parsed_resumes: list of dicts with keys like:
      NAME, CONTACT, PROFESSIONAL SUMMARY, SKILLS, WORK EXPERIENCE, ACADEMIC EDUCATION, ...
    Strategy:
      - pick the most common name/contact (or longest)
      - merge sections: keep the richest content, but union skills lines
    """
    # Name/contact: choose the longest non-empty
    name = max((r.get("NAME", "").strip() for r in parsed_resumes), key=len, default="").strip()
    contact = max((r.get("CONTACT", "").strip() for r in parsed_resumes), key=len, default="").strip()

    merged: Dict[str, str] = {}

    # Summary: take the longest summary (usually richest)
    summaries = [r.get("PROFESSIONAL SUMMARY", "").strip() for r in parsed_resumes if r.get("PROFESSIONAL SUMMARY")]
    merged["PROFESSIONAL SUMMARY"] = max(summaries, key=len, default="")

    # Skills: union unique lines
    skill_lines = []
    seen = set()
    for r in parsed_resumes:
        sk = r.get("SKILLS", "").strip()
        if not sk:
            continue
        for ln in sk.splitlines():
            n = " ".join(ln.lower().split())
            if not n or n in seen:
                continue
            seen.add(n)
            skill_lines.append(ln.strip())
    merged["SKILLS"] = "\n".join(skill_lines).strip()

    # For the remaining sections, pick the longest (most complete)
    for sec in ["WORK EXPERIENCE", "ACADEMIC EDUCATION", "ACADEMIC PROJECTS", "PROJECTS", "ACHIEVEMENTS"]:
        candidates = [r.get(sec, "").strip() for r in parsed_resumes if r.get(sec)]
        merged[sec] = max(candidates, key=len, default="")

    return CanonicalTemplate(name=name, contact=contact, sections=merged)
