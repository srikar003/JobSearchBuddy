from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class JDSignals:
    tools: List[str]
    keywords: List[str]
    responsibilities: List[str]


def _norm(s: str) -> str:
    return " ".join(s.lower().split()).strip()


def parse_jd(jd_text: str) -> JDSignals:
    text = jd_text.strip()
    low = text.lower()

    # Quick tool extractor: look for a "tech stack" line and common tech tokens
    known_tools = [
        "react", "typescript", "javascript", "node.js", "node", "fastify", "golang", "go",
        "postgresql", "postgres", "sql", "api", "rest", "microservices", "aws", "docker",
        "kubernetes", "testing", "jest", "vitest", "ci/cd", "oauth", "saas", "fintech",
        "b2b", "integrations", "third-party apis", "data pipelines", "orchestration"
    ]

    tools_found = []
    for t in known_tools:
        if t in low:
            tools_found.append(t)

    # Normalize some aliases
    alias = {
        "node": "node.js",
        "postgres": "postgresql",
        "go": "golang",
        "third-party apis": "third-party APIs",
        "ci/cd": "CI/CD",
    }
    tools = []
    for t in tools_found:
        tools.append(alias.get(t, t))

    # Responsibilities: take bullet-like lines
    resp = []
    for line in text.splitlines():
        ln = line.strip()
        if not ln:
            continue
        if ln.startswith(("-", "•")) or ln.endswith("."):
            if any(v in ln.lower() for v in ["build", "ship", "develop", "implement", "write", "debug", "collaborate"]):
                resp.append(ln.lstrip("-•").strip())

    # Keywords: basic extraction from “stand out” + stack
    keywords = []
    for k in ["b2b saas", "fintech", "integrations", "data syncing", "orchestration", "account management",
              "reporting", "forms", "code reviews", "tested code", "production issues", "databases"]:
        if k in low:
            keywords.append(k)

    # Dedup while preserving order
    def dedup(seq):
        seen = set()
        out = []
        for x in seq:
            nx = _norm(x)
            if nx in seen:
                continue
            seen.add(nx)
            out.append(x)
        return out

    return JDSignals(
        tools=dedup(tools),
        keywords=dedup(keywords),
        responsibilities=dedup(resp),
    )
