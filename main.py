from __future__ import annotations

import argparse
from pathlib import Path
from collections import defaultdict

from app.core.extractor import ResumeExtractor
from app.core.docx_exporter import DocxExporter
from app.core.resume_writer import ResumeWriter, ResumeWriterConfig
from app.core.structure_parser import (
    split_sections,
    parse_work_experience,
    parse_education,
    merge_roles,
    merge_education,
    build_experience_evidence,
    build_education_evidence,
    extract_template_parts,
)


def read_text_file(path: str | Path) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8").strip()


def build_full_text_by_file(extracted_chunks) -> dict[str, str]:
    grouped = defaultdict(list)
    for c in extracted_chunks:
        if c.extra and c.extra.get("skipped"):
            continue
        grouped[c.source_file].append(c)

    def order_key(c):
        return ((c.page or 0), (c.order or 0))

    out = {}
    for f, chunks in grouped.items():
        chunks.sort(key=order_key)
        text = "\n".join([x.text for x in chunks if x.text.strip()])
        out[f] = text
    return out


def pick_template_resume(texts_by_file: dict[str, str]) -> tuple[str, str]:
    best_file = ""
    best_text = ""
    best_len = -1
    for f, t in texts_by_file.items():
        if len(t) > best_len:
            best_len = len(t)
            best_file = f
            best_text = t
    return best_file, best_text


def main():
    parser = argparse.ArgumentParser(description="JobSearchBuddy (v1) - Template-anchored rewrite")
    parser.add_argument("--resumes", required=True, help="Folder containing .pdf/.docx resumes")
    parser.add_argument("--job-description", required=True, help="Path to job description .txt file")
    parser.add_argument("--output", required=True, help="Output .docx path")
    args = parser.parse_args()

    resumes_dir = Path(args.resumes)
    jd_path = Path(args.job_description)
    output_path = Path(args.output)

    job_description = read_text_file(jd_path)
    if not job_description:
        raise RuntimeError("jd.txt is empty (or not read). Fix the file/path first.")

    extractor = ResumeExtractor()
    extracted = extractor.load_folder(resumes_dir)

    texts_by_file = build_full_text_by_file(extracted)
    if not texts_by_file:
        raise RuntimeError("No resume text extracted. Check /resumes folder and file formats.")

    template_file, template_text = pick_template_resume(texts_by_file)
    print(f"Template resume chosen: {template_file}")

    # Parse ALL resumes -> collect ALL roles + education
    all_roles = []
    all_edu = []

    for fpath, full_text in texts_by_file.items():
        sections = split_sections(full_text)
        work_txt = sections.get("work_experience", "")
        edu_txt = sections.get("academic_education", "")

        if work_txt:
            all_roles.extend(parse_work_experience(work_txt, source_file=fpath))
        if edu_txt:
            all_edu.extend(parse_education(edu_txt, source_file=fpath))

    roles = merge_roles(all_roles)
    edus = merge_education(all_edu)

    if not roles:
        raise RuntimeError("No roles parsed from WORK EXPERIENCE. Parser needs tuning for your files.")
    if not edus:
        raise RuntimeError("No education parsed from ACADEMIC EDUCATION. Parser needs tuning for your files.")

    exp_evidence = build_experience_evidence(roles)
    edu_evidence = build_education_evidence(edus)

    writer = ResumeWriter(config=ResumeWriterConfig(model="llama3.1:8b", timeout_s=900))

    rewritten_work = writer.generate_from_prompt_file(
        "./app/prompts/work_experience_rewriter.txt",
        {
            "JOB_DESCRIPTION": job_description,
            "EXPERIENCE_EVIDENCE": exp_evidence,
        },
    )

    rewritten_edu = writer.generate_from_prompt_file(
        "./app/prompts/education_rewriter.txt",
        {
            "EDUCATION_EVIDENCE": edu_evidence,
        },
    )

    # Inject rewritten sections into template (preserves all other sections verbatim)
    prefix, edu_header, suffix = extract_template_parts(template_text)

    final_resume_text = (
        "\n".join(prefix).rstrip()
        + "\n"
        + rewritten_work.strip()
        + "\n\n"
        + "\n".join(edu_header).rstrip()
        + "\n"
        + rewritten_edu.strip()
        + "\n\n"
        + "\n".join(suffix).lstrip()
    ).strip()

    exporter = DocxExporter()
    exporter.export(final_resume_text, output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
