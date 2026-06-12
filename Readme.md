# Solar Inverter Import Compliance Workflow

An AI-powered pipeline that takes Chinese manufacturer specification PDFs and the NEPQA 2025 Nepal import guideline, extracts structured data from each, cross-references them, and produces a ready-to-share compliance review document automatically.

---

## How It Works

Importing grid-tied solar inverters from China into Nepal requires mapping what the Chinese manufacturer provides against what NEPQA 2025  Nepal's photovoltaic quality assurance standard  actually asks for. Doing this manually means reading through dense export PDFs, hunting for technical parameters, resolving references to IEC and NEA standards, and writing up a coherent review that a Nepal import agent can act on. It's slow, repetitive, and easy to miss things.

This workflow automates that process. Drop in up to two Chinese manufacturer PDFs alongside the NEPQA 2025 guideline. The pipeline extracts structured data from all three sources, resolves external standard references via web search, cross-references manufacturer specs against NEPQA requirements, and generates a professional compliance draft which is a  complete with a parameter-by-parameter comparison table, certification status, labeling review, document checklist, and a clear summary of any conflicts or gaps between the two manufacturer sources.

---

## Workflow Overview

```
Chinese Manufacturer PDFs + NEPQA 2025 Guideline
                │
                ▼
    [ Step 1 ]  PDF → Markdown
                │   pdfplumber extracts text and tables page by page
                │   Custom spanning-cell detection for complex tables
                │
        ┌───────┴────────┐
        ▼                ▼
[ Step 2a ]         [ Step 2b ]
NEPQA Guideline     Manufacturer Specs
→ Requirements JSON → Structured JSON
  LLM agent extracts   LLM agent maps specs
  all requirements     to NEPQA requirement keys
  + Tavily web search  Separates shared fields
  to resolve IEC/NEA   from per-model fields
  standard values
        │                │
        └───────┬────────┘
                ▼
    [ Step 3 ]  JSON inputs → Compliance Report
                LLM generates a structured Markdown draft
                Assessments: MEETS · CONFLICT · NOT PROVIDED · PARTIAL
```

Each step caches its output to disk. Re-runs skip steps where results already exist, keeping iteration fast and API costs low.

---

## Project Structure

```
├── run.py                              # Entry point — runs the full pipeline
├── .env                                # API keys (not committed)
│
├── pipeline/
│   ├── step1_pdf_to_md.py              # PDF → Markdown (pdfplumber)
│   ├── step2_nepqa_to_json.py          # NEPQA guideline → requirements JSON
│   ├── step2_manufacturer_to_json.py   # Manufacturer specs → structured JSON
│   └── step3_generate_report.py        # All JSONs → compliance report
│
├── data/
│   ├── input/                          # Source PDFs go here
│   │   ├── manufacture1.pdf            # Manufacturer PDF 1 (3-phase SUN series)
│   │   ├── manufacture2.pdf            # Manufacturer PDF 2 (1-phase CE series)
│   │   └── nepalqa.pdf                 # NEPQA 2025 import guideline
│   ├── extracted_md/                   # Cached Markdown from Step 1
│   └── extracted_json/                 # Cached JSON from Steps 2a and 2b
│
└── output/
    └── compliance_report.md            # Final generated report
```

---

## Pipeline

### Step 1 — PDF to Markdown (`step1_pdf_to_md.py`)

Extracts text and tables from PDF pages using **pdfplumber**, with a custom spanning-cell detection algorithm that handles merged/spanning cells common in Chinese manufacturer datasheets. Output is cached to `data/extracted_md/` so re-runs skip extraction.

### Step 2a — NEPQA Requirements to JSON (`step2_nepqa_to_json.py`)

An LLM agent reads the NEPQA 2025 guideline and extracts all import requirements as a flat key-value JSON — for example `"thd_current": "< 5% at rated power (IEC 61727:2004)"`. This runs first because its output keys are used as the extraction schema for the manufacturer agent in Step 2b.

Where NEPQA references an external standard without stating the actual value (e.g. "must comply with IEC 62116"), the agent calls **Tavily web search** to look up the specific numeric threshold. Output is cached to `data/extracted_json/nepalqa.json`.

### Step 2b — Manufacturer Specs to JSON (`step2_manufacturer_to_json.py`)

An LLM agent reads the extracted manufacturer Markdown and produces structured JSON using the NEPQA requirement keys as its schema, so extracted fields map directly to what Nepal review asks for. Output is organised as:

- `models` — list of product model names found in the document
- `general_fields` — specs shared across all models (e.g. certifications, topology, warranty)
- `models_specs` — per-model technical parameters

Output is cached to `data/extracted_json/`.

### Step 3 — Compliance Report Generation (`step3_generate_report.py`)

Takes all three JSON files (NEPQA requirements, Manufacturer 1, Manufacturer 2) and calls the LLM with a structured prompt to produce a professional Markdown compliance draft. See [Report Output](#report-output) below for what the report covers.

---

## Setup

**Requirements:** Python 3.10+, an OpenAI API key, and a Tavily API key.

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

---

## Usage

```bash
python run.py
```

The pipeline runs all steps in sequence and writes the final report to `output/compliance_report.md`.

To force a re-run of a specific step, delete its cached output:

| Step | Cache to delete |
|---|---|
| PDF extraction | `data/extracted_md/<filename>.md` |
| NEPQA JSON | `data/extracted_json/nepalqa.json` |
| Manufacturer JSON | `data/extracted_json/manufacture1.json` or `manufacture2.json` |
| Report | `output/compliance_report.md` |

---

## Report Output

The generated `output/compliance_report.md` is a structured compliance draft covering:

1. **Cover note** — memo format, ready to share with a Nepal import agent
2. **Product and manufacturer overview** — model ranges, phase types, key differences between variants
3. **Technical specification review** — parameter-by-parameter comparison table (SUN series vs CE series vs NEPQA requirements)
4. **Certifications and test reports** — what is confirmed, what is missing, which body issued it
5. **Labeling review** — required label fields vs. what the manufacturer documents confirm
6. **Document checklist** — availability status for each document required by NEPQA 2025
7. **Open items and discrepancies** — conflicts between the two manufacturer sources, data gaps, recommended next steps
8. **Preparer's notes** —methodology, assumptions, and limitations of the draft

---

## Design Notes


**Separate agents for separate tasks.** Manufacturer extraction and NEPQA extraction have different output shapes and different challenges, one needs per-model structured data, the other needs flat requirement key-value pairs with external standard resolution. Keeping them as separate agents with separate prompts and schemas makes each easier to tune independently.

**Web search for standards resolution.** NEPQA frequently references IEC and NEA standards without stating the actual numeric threshold. The NEPQA agent uses Tavily to look up specific values (e.g. THD limits, anti-islanding trip times, grid voltage tolerances) so the requirements JSON contains actionable numbers, not just citation strings.

**Honest gap reporting.** The report generation prompt explicitly instructs the LLM not to infer or fill gaps. Unknown values surface as `NOT PROVIDED`, conflicting values between the two manufacturer sources surface as `CONFLICT`. A compliance draft that hides uncertainty is worse than one that flags it clearly.

---
