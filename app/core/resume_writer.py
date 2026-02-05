from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import requests


DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_LLM_MODEL = "llama3.1:8b"


@dataclass
class ResumeWriterConfig:
    model: str = DEFAULT_LLM_MODEL
    host: str = DEFAULT_OLLAMA_HOST
    timeout_s: int = 900


class ResumeWriter:
    def __init__(self, config: ResumeWriterConfig | None = None):
        self.cfg = config or ResumeWriterConfig()

    def generate_from_prompt_file(self, prompt_path: str | Path, variables: dict[str, str]) -> str:
        prompt_path = Path(prompt_path)
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        template = prompt_path.read_text(encoding="utf-8")

        # Replace placeholders
        prompt = template
        for k, v in variables.items():
            prompt = prompt.replace(f"{{{{{k}}}}}", (v or "").strip())

        # Guard: if placeholders remain, fail fast (prevents generic output)
        if "{{" in prompt and "}}" in prompt:
            raise RuntimeError(
                "Unreplaced placeholders remain in prompt. "
                "Check prompt tokens vs variables keys."
            )

        # Guard: prevent silent “no JD provided”
        if variables.get("JOB_DESCRIPTION") is not None and not variables["JOB_DESCRIPTION"].strip():
            raise RuntimeError("Job description is empty. Check jd.txt path/content.")
        if variables.get("EXPERIENCE_EVIDENCE") is not None and not variables["EXPERIENCE_EVIDENCE"].strip():
            raise RuntimeError("Experience evidence is empty. Extraction/parsing failed.")
        if variables.get("EDUCATION_EVIDENCE") is not None and not variables["EDUCATION_EVIDENCE"].strip():
            raise RuntimeError("Education evidence is empty. Extraction/parsing failed.")

        return self._ollama_chat(prompt)

    def _ollama_chat(self, prompt: str) -> str:
        host = self.cfg.host.rstrip("/")
        url = f"{host}/v1/chat/completions"

        payload = {
            "model": self.cfg.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Follow instructions exactly. Do not add placeholders like [Your Name]. Use only provided evidence."
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "top_p": 0.9,
            "stream": False,
        }

        r = requests.post(url, json=payload, timeout=self.cfg.timeout_s)
        r.raise_for_status()
        data = r.json()

        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
