from dotenv import load_dotenv
import os

from langchain_openai import ChatOpenAI
import tavily

load_dotenv()

from tavily import TavilyClient
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from pipeline.step1_pdf_to_md import extract_pdf_pages_as_markdown
import json
from pathlib import Path

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     temperature=0,
#     api_key=os.getenv("GEMINI_API_KEY"),
# )


client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def search_web(query: str) -> str:
    """Use this to search specs that mention standards (like NEA grid code, IEC standards)."""
    print(f"SEARCHING: {query}")
    results = client.search(query)

    return results

nepqa_json_prompt = """
You are a PV inverter compliance and requirements extraction agent.

Your job is to extract ALL requirements from the provided document and convert them into structured JSON.
Extract general requirements, required documents, and technical requirements.

────────────────────────────
OUTPUT FORMAT
────────────────────────────
Return ONLY a valid JSON object. No markdown, no explanation, no preamble.

{
  "parameter_name": "concise constraint"
}

────────────────────────────
EXTRACTION RULES
────────────────────────────
- Extract every requirement — do not skip anything
- Keep values short, precise, and technical
- Merge duplicate keys into one
- Normalize technical expressions (e.g. "±10%" not "plus or minus 10 percent")

────────────────────────────
TOOL USAGE RULE
────────────────────────────
You MUST call search_web when:
- Whenever the document references a standard without giving a specific value (e.g. "as per NEA grid code" or "must meet IEC 61727 requirements")
- A requirement references an external standard (IEC, NEA, ISO, EN, etc.)
- A value is missing and can be looked up (e.g. "Nepal grid voltage")
- You are uncertain about a numeric constraint

Always search BEFORE writing the final value.
Always include the standard number and year in the search query if known.
  Example: "IEC 61727:2004 THD limit PV inverter"
  NOT:     "IEC THD requirement"

────────────────────────────
OUTPUT PRIORITY RULE
────────────────────────────
For each requirement, use this priority order:

1. BEST → Actual numeric/technical value from the document or search result
           e.g. "< 5% THD at rated power (IEC 61727:2004)"

2. GOOD → Standard reference if search did not return the specific value
           e.g. "complies with IEC 61727:2004"
           Rules:
           - Always include standard number and year e.g. "IEC 61727:2004" not "IEC 61727"
           - Never write "latest" — look up and write the actual year

3. LAST → "UNKNOWN" only if no standard is referenced AND no value was found after searching

────────────────────────────
WHAT TO NEVER DO
────────────────────────────
- Never write "as per latest standard" or "as per NEA grid code" without a value or standard number
- Never hallucinate values — if unsure, search first
- Never skip searching when a standard is referenced
- Never include markdown, backticks, or explanation in the output — JSON only

────────────────────────────
EXAMPLES
────────────────────────────
Input: "must comply with Nepal grid standard"
  → search: "Nepal Electricity Authority grid voltage frequency"
  → output: "230V ±10%, 50Hz ±5% (NEA grid code)"

Input: "THD must meet IEC 61727 requirements"
  → search: "IEC 61727:2004 THD limit PV inverter"
  → output: "< 5% at rated power (IEC 61727:2004)"

Input: "anti-islanding protection required"
  → search: "IEC 62116 anti-islanding detection time limit"
  → output: "detection and trip within 2s (IEC 62116:2014)"

Input: "must have IP rating for outdoor use"
  → search: "IEC 60529 IP65 protection standard outdoor"
  → output: "≥ IP65 (IEC 60529)"

────────────────────────────
FINAL OUTPUT EXAMPLE
────────────────────────────
{
  "grid_voltage": "230V ±10% (NEA grid code)",
  "grid_frequency": "50Hz ±5% (NEA grid code)",
  "thd_current": "< 5% at rated power (IEC 61727:2004)",
  "power_factor": "> 0.9 lagging at > 50% load",
  "dc_injection": "< 1% of rated output current (IEC 61727:2004)",
  "anti_islanding": "detection and trip within 2s (IEC 62116:2014)",
  "ip_rating": "≥ IP65 (IEC 60529)",
  "safety_standard": "complies with IEC 62109-1:2010",
  "mppt_efficiency": "UNKNOWN"
}
"""
specalised_agent = create_agent(
    model=llm,
    tools=[search_web],
    system_prompt=nepqa_json_prompt,
)

def nepqa_extract_requirements_to_json(pdffile, start_page, end_page) -> dict:
    """
    Extract requirements from the provided Markdown text and return as structured JSON.

    Args:
        md_text: Markdown string containing the extracted text from the PDF.

    Returns:
        A dictionary representing the extracted requirements in JSON format.
    """
    pdf_name = Path(pdffile).stem
    json_path = Path(f"data/extracted_json/{pdf_name}.json")

    if json_path.exists():
        print(f"JSON for {pdffile} already exists. Loading from file.")
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print("Extracting requirements and converting to JSON...")
    # return "Extracting requirements and converting to JSON..."
    md_text = extract_pdf_pages_as_markdown(pdf_path=pdffile, start_page= start_page, end_page= end_page)
    sec133_text = extract_pdf_pages_as_markdown(pdf_path = pdffile, start_page = 16, end_page = 17)
    full_text = md_text + sec133_text
    result = specalised_agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": full_text,
            }
        ]
    })
    last_msg = result["messages"][-1]
    # Handle both string and list cases
    if isinstance(last_msg.content, list):
        cleaned_json = last_msg.content[0]["text"]
    else:        cleaned_json = last_msg.content    
    # remove markdown safely (DON'T use strip for this)
    cleaned_json = cleaned_json.replace("```json", "").replace("```", "").strip()
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json.loads(cleaned_json), f, indent=2)

    return json.loads(cleaned_json)

   

# pdf = "data/nepal-photovoltaic-quality-assurance-2025-nepqa-2025.pdf"

# inputtext =extract_pdf_pages_as_markdown(
#         pdf, start_page=18, end_page=19)
    

# result = specalised_agent.invoke({
#     "messages": [
#         {
#             "role": "user",
#             "content": inputtext,
#         }
#     ]
# })
# import json

# last_msg = result["messages"][-1]

# # Handle both string and list cases
# if isinstance(last_msg.content, list):
#     cleaned_json = last_msg.content[0]["text"]
# else:
#     cleaned_json = last_msg.content

# # remove markdown safely (DON'T use strip for this)
# cleaned_json = cleaned_json.replace("```json", "").replace("```", "").strip()

# data = json.loads(cleaned_json)

# with open("output.json", "w", encoding="utf-8") as f:
#     json.dump(data, f, indent=2)

if __name__ == "__main__":
    md_text = extract_pdf_pages_as_markdown(
        pdf_path="data/input/nepalqa.pdf",
        start_page=18,
        end_page=19,
    )

    output = nepqa_extract_requirements_to_json(md_text, pdffile="data/input/nepalqa.pdf")
    print(json.dumps(output, indent=2))