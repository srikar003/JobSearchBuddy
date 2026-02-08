# JobSearchBuddy (Prototype) — Template-Anchored Resume Tailoring (v1)

JobSearchBuddy is a **local, privacy-first** prototype that helps job seekers tailor their resume to a job description using **Ollama** (local LLM). It reads multiple resumes from a folder, builds evidence from all of them, rewrites only specific sections using focused prompts, and injects the rewritten sections into a chosen “template resume” to preserve formatting/structure.

🛡️  **Privacy-first** · ⚙️ **Local LLM** · 📄 **Template-anchored output**

- ✅ Runs locally (Ollama)
- 📚 Uses multiple resumes as evidence
- ✍️ Rewrites only **WORK EXPERIENCE** + **ACADEMIC EDUCATION**
- 🧾 Preserves other sections from the template resume
- 📤 Exports output to `.docx`
- 🖥️ CLI-first

---

## How It Works (Current Implementation)

### Inputs

* A folder of resumes: `--resumes ./resumes`
* A job description text file: `--job-description jd.txt`
* Output docx path: `--output ./output/tailored_resume.docx`

### Processing Steps

1. 📝 **Extract text** from all resumes in the folder (`.pdf` and `.docx`)
2. 🧾 **Choose a template resume** (currently: the **longest extracted resume**)
3. 🔎 **Parse all resumes** to collect:

  - All roles from **WORK EXPERIENCE**
  - All entries from **ACADEMIC EDUCATION**
4. 🔁 **Merge and deduplicate** roles/education across resumes
5. ✍️ **Generate updated sections** using two prompts:

  - `work_experience_rewriter.txt` → rewrites **WORK EXPERIENCE** (JD-aware)
  - `education_rewriter.txt` → rewrites **ACADEMIC EDUCATION** (JD-agnostic)
6. 🧩 **Inject rewritten sections** into the template resume:

  - Replace the template’s WORK EXPERIENCE with the rewritten work section
  - Replace the template’s ACADEMIC EDUCATION with the rewritten education section
  - Keep everything else **verbatim**
7. 📤 **Export** as `.docx`

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

## 🛠️ Install & Run Ollama

### 1) Pull required model(s)

LLM used by `main.py`:

```powershell
ollama pull llama3.1:8b
```

(You can switch models by updating `ResumeWriterConfig(model=...)`).

### 🔧 Managing models & running Ollama in background

- **Pull or update a model:** re-running `ollama pull <model>` will download or update the specified model.

```powershell
ollama pull llama3.1:8b
ollama pull gpt-oss:20b-cloud
```

- **List local models:**

```powershell
ollama list
```

### 🧪 Nomic `nomic-embed-text` — pull & test

If you plan to use `nomic-embed-text` for embeddings, pull and test it with these steps.

- **Attempt to pull the model** (model name can vary by registry):

```powershell
ollama pull nomic-embed-text
```

- **Quick embedding test** (replace model name if different):

PowerShell:
```powershell
Invoke-RestMethod -Method POST -Uri 'http://localhost:11434/api/embeddings' -Body (@{ model='nomic-embed-text'; prompt='hello world' } | ConvertTo-Json) -ContentType 'application/json'
```

curl (bash):
```bash
curl -s -X POST "http://localhost:11434/api/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"model":"nomic-embed-text","prompt":"hello world"}'
```

If the request returns a JSON object containing an `embedding` array, the model is available and working.

If you see `model not found`, confirm the exact model name available in your Ollama model registry or use an alternative embedding provider.

- **Run the Ollama server in the background (Windows PowerShell):**

```powershell
# Start Ollama as a background process (ensure `ollama` is in PATH)
Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden

# Confirm the server is responding
Invoke-RestMethod -Uri 'http://localhost:11434/api/tags'
```

> ⚠️ Tip: to see server logs, run `ollama serve` in a visible shell instead of starting it hidden.

- **Switch the model used by the tool (code):** edit the `model` argument in `main.py` where `ResumeWriterConfig` is instantiated.

Example (in `main.py`):

```py
MODEL_NAME='gpt-oss:20b-cloud' #update it to 'llama3.1:8b'
writer = ResumeWriter(config=ResumeWriterConfig(model=MODEL_NAME, timeout_s=900))
```

Replace the string with any model you have pulled (for example `gpt-oss:20b-cloud`).

Notes:
- Ensure `ollama` is on your PATH so the `Start-Process` call succeeds.
- `Start-Process` will launch `ollama serve` asynchronously; if you need logs, run `ollama serve` in a visible shell instead.
- If the server takes time to load models, allow several seconds before sending requests.

### ▶️ Confirm Ollama is running

Quick check (PowerShell). If Ollama isn't responding this will start `ollama serve` for you.

```powershell
# Try a quick API check; if it fails, start ollama serve and re-check
try {
  Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 2 | Out-Null
  Write-Output 'Ollama is running (200)'
} catch {
  Write-Output 'Ollama not responding — starting ollama serve...'
  # Starts ollama in a new process (ensure `ollama` is in PATH)
  Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden
  Start-Sleep -Seconds 3
  # Re-check the API once the server has started
  Invoke-RestMethod -Uri 'http://localhost:11434/api/tags'
}
```

Alternatively, the original Python one-liner (requires `requests`):

```powershell
python -c "import requests; print(requests.get('http://localhost:11434/api/tags').status_code)"
```

Expected output: `200`

If you get `ModuleNotFoundError: requests`, run:

```powershell
pip install requests
```

---

## 🚀 Usage (CLI)

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

## 🧠 Prompts (Two-Prompt System)

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
