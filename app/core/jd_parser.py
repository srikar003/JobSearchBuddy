from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Dict, Iterable, Tuple, Optional


@dataclass
class JDSignals:
    tools: List[str]
    keywords: List[str]
    responsibilities: List[str]


# ----------------------------
# Utilities
# ----------------------------

_STOPWORDS = {
    "a", "an", "and", "or", "the", "to", "of", "in", "on", "for", "with", "as", "at", "by",
    "from", "that", "this", "these", "those", "be", "is", "are", "was", "were", "will",
    "you", "we", "our", "their", "they", "your", "it", "its", "into", "within", "across",
    "ability", "experience", "years", "relevant", "preferred", "requirements", "qualification",
    "responsibilities", "skills", "strong", "knowledge", "expert", "including", "such",
    "etc", "may", "must", "should", "can", "able"
}

# Common bullet markers across JDs (hyphen, dot, unicode bullets, numbered)
_BULLET_RE = re.compile(r"^\s*(?:[-•●▪◦‣–—]|\d+[\).\]]|[a-zA-Z][\).\]])\s+")

# Section header heuristic
_HEADER_RE = re.compile(
    r"^\s*(?:"
    r"responsibilities|requirements|preferred qualifications|qualifications|"
    r"what you'll do|what you will do|you will|you'll|about you|"
    r"education|experience|tech stack|stack|tools|technologies|"
    r"nice to have|bonus|stand out|we're looking for"
    r")\s*:?\s*$",
    re.IGNORECASE,
)

# Action verbs commonly used in responsibilities (generic across domains)
_ACTION_VERBS = (
    "build", "ship", "develop", "design", "implement", "deliver", "own", "lead", "drive",
    "collaborate", "partner", "coordinate", "improve", "optimize", "maintain", "support",
    "debug", "resolve", "analyze", "create", "architect", "test", "review", "deploy",
    "monitor", "operate", "integrate", "automate", "document", "mentor"
)

_ACTION_RE = re.compile(rf"\b(?:{'|'.join(map(re.escape, _ACTION_VERBS))})\b", re.IGNORECASE)

# Token patterns for tools/technologies (generic)
_TOOL_PATTERNS = [
    # Cloud vendors / platforms
    r"\b(?:aws|amazon web services|azure|gcp|google cloud|oci|oracle cloud)\b",
    # CI/CD
    r"\bci\s*/\s*cd\b|\bci-cd\b|\bcontinuous integration\b|\bcontinuous delivery\b",
    # Auth / security
    r"\boauth\s*2(?:\.0)?\b|\boauth2\b|\bsaml\b|\boidc\b|\bpingfed\b|\bkey vault\b|\bapim\b",
    # Languages (captures C#, C++, .NET, Go)
    r"\b(?:python|java(?:script)?|typescript|golang|go|c\+\+|c#|dotnet|\.net|ruby|php|scala|kotlin|rust)\b",
    # Frontend frameworks
    r"\b(?:react|angular|vue|next\.js|nuxt|svelte)\b",
    # Backend/runtime
    r"\b(?:node\.?js|express|fastify|nestjs|spring boot|django|flask|fastapi)\b",
    # Databases / search
    r"\b(?:postgres(?:ql)?|mysql|mariadb|sql server|mongodb|redis|dynamodb|cassandra|elasticsearch|opensearch)\b",
    # Containers / orchestration
    r"\b(?:docker|kubernetes|k8s|aks|eks|gke|helm)\b",
    # Observability
    r"\b(?:grafana|kibana|prometheus|datadog|new relic|splunk|cloudwatch)\b",
    # AI/LLM stack (kept broad, not vendor-specific only)
    r"\b(?:llm|llms|rag|graphrag|agentic|agents|langchain|langgraph|vector search|embeddings?)\b",
    r"\b(?:openai|azure openai|bedrock|vertex ai|hugging face)\b",
]

_TOOL_RE = re.compile("|".join(f"(?:{p})" for p in _TOOL_PATTERNS), re.IGNORECASE)

# Phrase candidates like "Azure OpenAI", "Azure AI Search", "Domain-Driven Design", "event-driven"
_PHRASE_RE = re.compile(
    r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}|[A-Z]{2,}(?:\s+[A-Z]{2,}){0,3})\b"
)

def _norm_space(s: str) -> str:
    return " ".join(s.split()).strip()

def _norm_lower(s: str) -> str:
    return _norm_space(s).lower()

def _dedup(seq: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for x in seq:
        k = _norm_lower(x)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


# ----------------------------
# Core extraction logic
# ----------------------------

def _split_lines(text: str) -> List[str]:
    # Keep original order; normalize weird bullets spacing
    lines = []
    for raw in text.splitlines():
        ln = raw.rstrip()
        if ln.strip():
            lines.append(ln)
    return lines

def _is_header(line: str) -> bool:
    # Uppercase short lines or matches common header patterns
    stripped = line.strip()
    if _HEADER_RE.match(stripped):
        return True
    # ALL CAPS headers like "REQUIREMENTS"
    if len(stripped) <= 40 and stripped.isupper() and any(c.isalpha() for c in stripped):
        return True
    return False

def _extract_responsibilities(lines: List[str]) -> List[str]:
    res = []

    # Heuristic: capture bullet lines with action verbs
    for ln in lines:
        clean = ln.strip()

        is_bullet = bool(_BULLET_RE.match(clean))
        candidate = _BULLET_RE.sub("", clean) if is_bullet else clean

        # Include if it looks like a responsibility line:
        # - bullet + verb OR contains action verb and is sentence-like
        if is_bullet and _ACTION_RE.search(candidate):
            res.append(_norm_space(candidate).rstrip("."))
        else:
            # Non-bulleted responsibility sentences often start with verbs:
            if _ACTION_RE.search(candidate) and len(candidate.split()) >= 6:
                # Avoid capturing requirement-only lines like "7+ years experience..."
                if not re.search(r"\b\d+\s*\+?\s*years?\b", candidate, re.IGNORECASE):
                    res.append(_norm_space(candidate).rstrip("."))

    return _dedup(res)

def _extract_tools(text: str) -> List[str]:
    found = []

    # 1) Regex-based tool hits
    for m in _TOOL_RE.finditer(text):
        token = m.group(0)
        found.append(_norm_space(token))

    # 2) Catch common slash-separated tokens (e.g., "React/Node/Go", "AWS/Azure")
    for m in re.finditer(r"\b[A-Za-z][A-Za-z0-9\.\+#-]*(?:\s*/\s*[A-Za-z0-9\.\+#-]+)+\b", text):
        chunk = _norm_space(m.group(0))
        # Split and keep parts that look tool-like
        parts = [p.strip() for p in re.split(r"\s*/\s*", chunk)]
        for p in parts:
            if len(p) >= 2:
                found.append(p)

    # 3) Catch dotted tools like "Node.js"
    for m in re.finditer(r"\b[A-Za-z]+(?:\.[A-Za-z0-9]+)+\b", text):
        found.append(m.group(0))

    # Normalize aliases
    alias_map = {
        "nodejs": "node.js",
        "node js": "node.js",
        "postgres": "postgresql",
        "k8s": "kubernetes",
        "dotnet": ".net",
        "ci-cd": "ci/cd",
    }

    normed = []
    for t in found:
        key = _norm_lower(t).replace(".", "").replace("-", " ").strip()
        # Preserve important casing for known terms if present
        out = alias_map.get(key, t)
        normed.append(out)

    # Light cleanup: remove overly generic matches
    drop = {"api", "apis", "sql"}  # keep these as keywords instead; too broad as "tools"
    tools = []
    for t in _dedup(normed):
        if _norm_lower(t) in drop:
            continue
        # Avoid single letters or ultra-short junk
        if len(t) < 2:
            continue
        tools.append(t)

    return tools

def _tokenize_words(text: str) -> List[str]:
    # Keep + and # (C++, C#), dots (node.js) as separators handled earlier
    words = re.findall(r"[A-Za-z][A-Za-z0-9\+\#-]*", text.lower())
    return [w for w in words if w and w not in _STOPWORDS]

def _extract_keywords(text: str, tools: List[str], top_n: int = 18) -> List[str]:
    """
    Keyword extraction = top n-grams (2-3 words) + promoted phrases from headers.
    Avoids duplicating extracted tools.
    """
    lowered = text.lower()
    words = _tokenize_words(text)

    # Build n-grams
    ngrams: Dict[str, int] = {}
    for n in (2, 3):
        for i in range(len(words) - n + 1):
            ng = " ".join(words[i:i+n])
            # Skip if mostly stopword-ish or too generic
            if any(w in _STOPWORDS for w in ng.split()):
                continue
            ngrams[ng] = ngrams.get(ng, 0) + 1

    # Promote phrases from common JD sections by grabbing Title Case phrases
    promoted = []
    for m in _PHRASE_RE.finditer(text):
        ph = _norm_space(m.group(0))
        # Exclude single common words and pure ALLCAPS short acronyms already in tools
        if len(ph.split()) == 1 and len(ph) <= 3:
            continue
        promoted.append(ph.lower())

    # Down-rank anything that is already a tool token
    tool_set = {_norm_lower(t) for t in tools}

    # Score candidates
    scored: List[Tuple[int, str]] = []
    for k, c in ngrams.items():
        if k in tool_set:
            continue
        # Prefer “enterprise-ish” terms that show seniority/governance patterns
        boost = 0
        if any(x in k for x in ["govern", "standard", "security", "monitor", "orchestrat", "integration", "auth", "compliance", "risk", "responsible"]):
            boost += 1
        scored.append((c + boost, k))

    # Add promoted phrases (low weight, but helpful)
    for p in promoted:
        if p in tool_set:
            continue
        if len(p.split()) >= 2:
            scored.append((1, p))

    scored.sort(key=lambda x: (-x[0], x[1]))
    out = []
    for _, kw in scored:
        if kw not in out:
            out.append(kw)
        if len(out) >= top_n:
            break

    return out


def parse_jd(jd_text: str) -> JDSignals:
    text = jd_text.strip()
    lines = _split_lines(text)

    # Section-aware: you can later extend this to separately parse Requirements vs Responsibilities
    responsibilities = _extract_responsibilities(lines)
    tools = _extract_tools(text)
    keywords = _extract_keywords(text, tools=tools, top_n=20)

    return JDSignals(
        tools=tools,
        keywords=keywords,
        responsibilities=responsibilities,
    )
