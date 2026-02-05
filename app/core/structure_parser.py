from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import re


WORK_HEADERS = {"work experience"}
EDU_HEADERS = {"academic education"}

OTHER_HEADERS = {
    "professional summary",
    "skills",
    "academic projects",
    "projects",
    "achievements",
    "certifications",
}

DATE_LINE_RE = re.compile(
    r"(?i)\b("
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
    r")\b.*\b(\d{4})\b.*\b(present|current|\d{4})\b|(\d{4}).*(\d{4})"
)

BULLET_RE = re.compile(r"^\s*(?:•|-|–)\s*(.+)$")


@dataclass
class RoleBlock:
    company_line: str
    dates_line: str
    title_line: str
    bullets: List[str]
    source_files: List[str]


@dataclass
class EducationBlock:
    institution_line: str
    degree_line: str
    source_files: List[str]


def normalize(s: str) -> str:
    return " ".join(s.lower().split()).strip()


def extract_template_parts(full_text: str) -> tuple[list[str], list[str], list[str]]:
    """
    Returns (prefix_including_work_header, edu_header_line_as_list, suffix_after_edu_section)

    We will inject:
      prefix + rewritten_work + edu_header + rewritten_edu + suffix
    """
    lines = [ln.rstrip() for ln in full_text.splitlines()]

    def find_header_idx(header_set: set[str]) -> int:
        for i, ln in enumerate(lines):
            if normalize(ln) in header_set:
                return i
        return -1

    work_idx = find_header_idx(WORK_HEADERS)
    edu_idx = find_header_idx(EDU_HEADERS)
    if work_idx == -1 or edu_idx == -1 or edu_idx <= work_idx:
        raise RuntimeError("Template is missing WORK EXPERIENCE / ACADEMIC EDUCATION headers or order is wrong.")

    # Find end of education section: next known header after edu_idx
    edu_end = len(lines)
    for j in range(edu_idx + 1, len(lines)):
        key = normalize(lines[j])
        if key in OTHER_HEADERS:
            edu_end = j
            break

    prefix = lines[: work_idx + 1]             # includes "WORK EXPERIENCE"
    edu_header = [lines[edu_idx]]              # "ACADEMIC EDUCATION"
    suffix = lines[edu_end:]                   # everything after education section

    return prefix, edu_header, suffix


def split_sections(full_text: str) -> Dict[str, str]:
    lines = [ln.rstrip() for ln in full_text.splitlines()]
    sections: Dict[str, List[str]] = {"root": []}
    current = "root"

    for ln in lines:
        key = normalize(ln)
        if key in WORK_HEADERS:
            current = "work_experience"
            sections.setdefault(current, [])
            continue
        if key in EDU_HEADERS:
            current = "academic_education"
            sections.setdefault(current, [])
            continue
        sections[current].append(ln)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


def parse_work_experience(work_text: str, source_file: str) -> List[RoleBlock]:
    lines = [ln.strip() for ln in work_text.splitlines() if ln.strip()]
    roles: List[RoleBlock] = []

    i = 0
    while i < len(lines):
        company = lines[i]

        if i + 2 < len(lines) and DATE_LINE_RE.search(lines[i + 1]):
            dates = lines[i + 1]
            title = lines[i + 2]
            i += 3

            bullets: List[str] = []
            bullet_pending = False  # handles standalone '•'

            while i < len(lines):
                ln = lines[i].strip()

                # next role heuristic
                if i + 2 < len(lines) and DATE_LINE_RE.search(lines[i + 1]) and (("|" in ln) or ln.isupper()):
                    break

                if ln in {"•", "-", "–"}:
                    bullet_pending = True
                    i += 1
                    continue

                m = BULLET_RE.match(ln)
                if m:
                    bullets.append(m.group(1).strip())
                    bullet_pending = False
                    i += 1
                    continue

                if bullet_pending:
                    bullets.append(ln)
                    bullet_pending = False
                    i += 1
                    continue

                if bullets:
                    bullets[-1] = (bullets[-1] + " " + ln).strip()

                i += 1

            if bullets:
                roles.append(RoleBlock(company, dates, title, bullets, [source_file]))
        else:
            i += 1

    return roles


def parse_education(edu_text: str, source_file: str) -> List[EducationBlock]:
    lines = [ln.strip() for ln in edu_text.splitlines() if ln.strip()]
    out: List[EducationBlock] = []

    i = 0
    while i < len(lines) - 1:
        inst = lines[i]
        deg = lines[i + 1]

        if BULLET_RE.match(inst) or BULLET_RE.match(deg):
            i += 1
            continue

        out.append(EducationBlock(inst, deg, [source_file]))
        i += 2

        while i < len(lines) and BULLET_RE.match(lines[i]):
            i += 1

    return out


def merge_roles(all_roles: List[RoleBlock]) -> List[RoleBlock]:
    merged: Dict[str, RoleBlock] = {}

    for r in all_roles:
        key = normalize(r.company_line) + "|" + normalize(r.dates_line) + "|" + normalize(r.title_line)
        if key not in merged:
            merged[key] = r
            continue

        ex = merged[key]
        ex.source_files = sorted(list(set(ex.source_files + r.source_files)))

        seen = set(normalize(b) for b in ex.bullets)
        for b in r.bullets:
            nb = normalize(b)
            if nb not in seen:
                ex.bullets.append(b)
                seen.add(nb)

    return list(merged.values())


def merge_education(all_edu: List[EducationBlock]) -> List[EducationBlock]:
    merged: Dict[str, EducationBlock] = {}
    for e in all_edu:
        key = normalize(e.institution_line) + "|" + normalize(e.degree_line)
        if key not in merged:
            merged[key] = e
        else:
            merged[key].source_files = sorted(list(set(merged[key].source_files + e.source_files)))
    return list(merged.values())


def build_experience_evidence(roles: List[RoleBlock]) -> str:
    parts: List[str] = []
    for r in roles:
        parts.append(r.company_line)
        parts.append(r.dates_line)
        parts.append(r.title_line)
        for b in r.bullets:
            parts.append(f"• {b}")
        parts.append("")
    return "\n".join(parts).strip()


def build_education_evidence(edus: List[EducationBlock]) -> str:
    parts: List[str] = []
    for e in edus:
        parts.append(e.institution_line)
        parts.append(e.degree_line)
        parts.append("")
    return "\n".join(parts).strip()
