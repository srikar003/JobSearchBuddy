# JobSearchBuddy (Prototype) — Template-Anchored Resume Tailoring (v1)

JobSearchBuddy is a **local, privacy-first** prototype that helps job seekers tailor their resume to a job description using **Ollama** (local LLM). It reads multiple resumes from a folder, builds evidence from all of them, rewrites only specific sections using focused prompts, and injects the rewritten sections into a chosen “template resume” to preserve formatting/structure.

✅ Runs locally (Ollama).

✅ Uses multiple resumes as evidence.

✅ Rewrites only **WORK EXPERIENCE** + **ACADEMIC EDUCATION**.

✅ Preserves all other sections from the chosen template resume.

✅ Exports output to `.docx`.

✅ CLI-first.

---

## How It Works (Current Implementation)

### Inputs

* A folder of resumes: `--resumes ./resumes`
* A job description text file: `--job-description jd.txt`
* Output docx path: `--output ./output/tailored_resume.docx`

### Processing Steps

1. **Extract text** from all resumes in the folder (`.pdf` and `.docx`)
2. Choose a **template resume** (currently: the **longest extracted resume**)
3. Parse **all resumes** to collect:

   * All roles from **WORK EXPERIENCE**
   * All entries from **ACADEMIC EDUCATION**
4. Merge and deduplicate roles/education across resumes
5. Generate updated sections using two prompts:

   * `work_experience_rewriter.txt` → rewrites **WORK EXPERIENCE** (JD-aware)
   * `education_rewriter.txt` → rewrites **ACADEMIC EDUCATION** (JD-agnostic)
6. Inject the rewritten sections into the template resume:

   * Replaces the template’s WORK EXPERIENCE section with rewritten work section
   * Replaces the template’s ACADEMIC EDUCATION section with rewritten education section
   * Keeps everything else **verbatim**
7. Export as `.docx`

---

## Project Structure

```txt
jobsearchbuddy/
├── app/
│   ├── core/
│   │   ├── extractor.py
│   │   ├── docx_exporter.py
│   │   ├── resume_writer.py
│   │   ├── structure_parser.py
│   │   └── ... (other modules)
│   ├── prompts/
│   │   ├── work_experience_rewriter.txt
│   │   └── education_rewriter.txt
├── resumes/
├── output/
├── main.py
├── requirements.txt
└── README.md
```

---

## Setup

### 1) Create and activate a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

---

## Install & Run Ollama

### 1) Confirm Ollama is running

```powershell
python -c "import requests; print(requests.get('http://localhost:11434/api/tags').status_code)"
```

Expected output: `200`

> If you get `ModuleNotFoundError: requests`, run:

```powershell
pip install requests
```

### 2) Pull required model(s)

LLM used by `main.py`:

```powershell
ollama pull llama3.1:8b
```

(You can switch models by updating `ResumeWriterConfig(model=...)`.)

---

## Usage (CLI)

### 1) Put resumes in `./resumes`

Supported formats:

* `.pdf`
* `.docx`

### 2) Create a JD file

Create `jd.txt` (plain text job description).

### 3) Run the tool

```powershell
python main.py `
  --resumes ./resumes `
  --job-description jd.txt `
  --output ./output/tailored_resume.docx
```

The script prints which resume file is being used as the **template**:

```
Template resume chosen: resumes\...
Saved: output\tailored_resume.docx
```

---

## Prompts (Two-Prompt System)

### 1) `app/prompts/work_experience_rewriter.txt`

* Input variables:

  * `{{JOB_DESCRIPTION}}`
  * `{{EXPERIENCE_EVIDENCE}}`
* Output:

  * A complete **WORK EXPERIENCE** section (in your resume format)

Typical requirements enforced by the prompt:

* All experiences must appear (from merged evidence)
* No repeated experiences
* Minimum **4 bullet points per role**
* Tailor bullet wording to match the JD keywords and responsibilities

### 2) `app/prompts/education_rewriter.txt`

* Input variables:

  * `{{EDUCATION_EVIDENCE}}`
* Output:

  * Education content to be placed under the template’s **ACADEMIC EDUCATION** header

Notes:

* This prompt is typically JD-agnostic (but you can make it JD-aware if desired)

---

## Template Anchoring (Why the Output Format Stays Consistent)

This version preserves your formatting by:

* Selecting a “template resume” text (the longest resume)
* Using `extract_template_parts(template_text)` to split the template into:

  * `prefix` (everything before WORK EXPERIENCE)
  * `edu_header` (the ACADEMIC EDUCATION header area)
  * `suffix` (everything after ACADEMIC EDUCATION section)
* Injecting rewritten sections in between

This ensures sections like:

* Header name/contact
* Summary, Skills, Projects, Achievements, etc.
  remain unchanged unless explicitly rewritten.

---

## Troubleshooting

### JD file reads as empty

If you see:
`jd.txt is empty (or not read)`

Check:

* `--job-description` path is correct
* File has content
* UTF-8 encoding

---

### Ollama port in use

If you see:
`listen tcp 127.0.0.1:11434: bind: Only one usage of each socket address...`

It means Ollama is already running. Don’t start another instance.

---

### Model not found

If you see:
`model 'llama3.1:8b' not found`

Run:

```powershell
ollama pull llama3.1:8b
```

---

## Notes / Known Behavior

* Template resume is currently chosen as the **longest extracted resume**.
* Work/education evidence is built from **all resumes** in the folder.
* Output speed depends mostly on local model performance (CPU/GPU).

---

## Next Improvements

* Improve template selection (choose the resume that best matches your preferred format)
* Add keyword match scoring (ATS score report)
* Add caching for extracted text + merged evidence
* Add an optional FastAPI wrapper around `main.py`

---
