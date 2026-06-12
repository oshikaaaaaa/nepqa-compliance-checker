from pipeline.step2_manufacturer_to_json import llm
import json
from pathlib import Path

with open('data/extracted_json/nepalqa.json') as f:
    nepqa_json = json.load(f)
with open('data/extracted_json/manufacture1.json') as f:
    specs1 = json.load(f)
with open('data/extracted_json/manufacture2.json') as f:
    specs2 = json.load(f)
report_gen_prompt = f"""
You are a compliance documentation specialist helping a Kathmandu-based solar equipment importer 
prepare a draft import review file for their Nepal agent.

────────────────────────────
BACKGROUND
────────────────────────────
Client: SunBridge Trading, Kathmandu
Purpose: Draft compliance file for Nepal import review of grid-tied solar inverters sourced from China
Audience: Local Nepal import agent (not the manufacturer, not a certification body)
Reference standard: NEPQA 2025 (Nepal) — use as a guide for what Nepal import reviews typically 
ask for, not as a template to copy verbatim

Two manufacturer export documents have been provided. They appear to describe related but 
potentially distinct product variants from the same manufacturer group. Where the two sources 
agree, present consolidated information. Where they differ, show both values honestly and flag 
the discrepancy. Do not infer or fabricate missing data — note gaps clearly.

────────────────────────────
TONE AND STYLE
────────────────────────────
- Write as a professional compliance drafter, not as a data extraction tool
- Use proper product and manufacturer names throughout — never refer to sources as "JSON 1", 
  "JSON 2", "PDF 1", or "PDF 2" in the body of the report
  - Refer to the three-phase SUN series products by their model names/series
  - Refer to the single-phase CE series products by their model names/series
  - Where a finding applies to both, say "both product series" or "across both variants"
  - Where sources conflict, name them by product series (e.g. "SUN series states... CE series states...")
- Write in clear, plain English suitable for a business document
- Use tables where they aid clarity (e.g. specification comparison, document checklist)
- Use short narrative paragraphs for context, findings, and notes — not bullet dumps
- This is a working draft — honest, structured, professional

────────────────────────────
REPORT STRUCTURE
────────────────────────────
Give output in markdown format, structured into the following sections:
SECTION 1 — COVER NOTE
A short professional memo:
  To: Nepal Import Agent
  From: SunBridge Trading, Kathmandu
  Re: Draft Import Compliance File — Grid-Tied Solar Inverters
  Date: [today's date]
Write 2–3 sentences explaining this is a draft submission for review, what it covers, and 
that further documentation may be needed.

SECTION 2 — PRODUCT AND MANUFACTURER OVERVIEW
Present clearly:
- Manufacturer name and location
- Product type
- Series names and model number ranges covered
- Phase type and rated power range for each series
- Any notable differences between the two product variants
Keep this factual and concise — 1 short paragraph per series or a clean summary table.

SECTION 3 — TECHNICAL SPECIFICATIONS REVIEW
Compare manufacturer-provided data against what Nepal import reviews typically examine 
(using NEPQA 2025 as reference).

Present as a table with columns:
  Parameter | NEPQA 2025 Requirement | SUN Series (3-phase) | CE Series (1-phase) | Assessment

Assessment values:
- MEETS — data provided and satisfies the requirement
- DOES NOT MEET — data provided but falls short
- NOT PROVIDED — data absent from manufacturer documents
- CONFLICT — the two product sources give differing values (show both)
- PARTIAL — some data available but incomplete

After the table, write a short paragraph (3–5 sentences) summarising the overall picture: 
what looks solid, what is missing, and what conflicts need resolution.

SECTION 4 — CERTIFICATIONS AND TESTING
Two sub-parts:

4a. Required vs. Available Certifications
A table or structured list showing:
- Each certification required by NEPQA 2025
- Whether it is confirmed for SUN series, CE series, both, or neither
- The certifying body where known
- Any gaps

4b. Test Reports
Note what test documentation exists, who issued it, and what is missing.
Write 2–3 sentences summarising the certification position.

SECTION 5 — LABELING
Two sub-parts:

5a. Required label fields (per NEPQA 2025)
5b. Confirmed vs. unconfirmed fields from manufacturer documents

Keep concise. Flag any fields not confirmed.

SECTION 6 — DOCUMENT CHECKLIST
A simple table:
  Document | Required by NEPQA 2025 | Status

Status options: Available / Partial / Not Available / Not Confirmed

SECTION 7 — OPEN ITEMS AND DISCREPANCIES
Prose section (not a bullet dump). Write in short paragraphs covering:
- Conflicts between the two product series that need factory clarification
- Missing technical data that should be requested from the manufacturer
- Document gaps to be resolved before submission
- Any observations about the two PDFs that SunBridge should be aware of
  (e.g. whether they appear to be the same or different products)

SECTION 8 — PREPARER'S APPROACH AND LIMITATIONS
2–3 short paragraphs explaining:
- How this draft was prepared (two manufacturer documents cross-referenced against NEPQA 2025)
- What assumptions were made, if any
- What this draft is and is not (working reference, not a certified filing)
- Recommended next steps

────────────────────────────
INPUTS
────────────────────────────
Manufacturer Document 1 (SUN series — three-phase grid-tied inverters, 3kW–15kW):
{specs1}

Manufacturer Document 2 (CE series — single-phase grid-tied inverters, 300W–2kW):
{specs2}

Nepal Import Reference Standard (NEPQA 2025):
{nepqa_json}
"""


def generate_report():
    if Path("output/compliance_report.md").exists():
        print("Report already exists. Loading from file.")
        return Path("output/compliance_report.md").read_text(encoding="utf-8")
    print("Generating compliance report...")
    
    response = llm.invoke(report_gen_prompt)
    return response


if __name__ == "__main__":

    with open('3draft_compliance_report.md', 'w', encoding='utf-8') as f:
        report = generate_report()
        f.write(report)
    print("Report generated and saved to 3draft_compliance_report.md")