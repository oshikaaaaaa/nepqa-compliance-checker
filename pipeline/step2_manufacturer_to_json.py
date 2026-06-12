from dotenv import load_dotenv
import os
import json
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from pipeline.step1_pdf_to_md import extract_pdf_pages_as_markdown
from pathlib import Path

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Load the NEPQA requirements JSON
with open("data/extracted_json/nepalqa.json", "r", encoding="utf-8") as f:
    nepqa = json.load(f)

# Extract keys dynamically
nepqa_keys = list(nepqa.keys())
nepqa_keys_str = "\n".join(f"- {key}" for key in nepqa_keys)

extraction_system_prompt = """
You are a photovoltaic product specification extraction agent.

INPUTS

1. requirements_json (keys representing the required fields to extract)
2. product specification document's content (markdown text extracted from a PDF)

TASK

Extract ONLY the fields listed in requirements_json.
Use the keys in requirements_json and extract the corresponding values from the specification document only.

OUTPUT FORMAT

{ 
  "models": [],
  "general_fields": {},
  "models_specs": {}
}

RULES

1. Read the requirements_json first.

2. Read the product specification document.

3. Extract all models mentioned in the product specification document.

4. Search the specification for evidence of each requirement key.

5. Every key in requirements_json MUST appear in the output.

6. If a value is the same for all models, place it in general_fields:

{
  "general_fields": {
      "frequency": "50Hz"
  }
}

Examples of general fields:
- certifications
- manufacturer
- testing laboratory
- topology
- warranty
- IP protection if common to all models
- Rated voltage if same for all models

7. If a value is model-specific, place it in models_specs:

{
  "models_specs": {
      "MODEL_NAME": {
          "rated_power": "5000W"
      }
  }
}

8. If a field is not directly named but related information exists, use reasonable technical 
   judgment to map it to the closest matching requirement key. Document your reasoning 
   in a "_notes" field within that model or general_fields.

9. If you are unsure whether a value is shared or model-specific, include it in the 
   model entry and note the ambiguity in "_notes".

10. If the document does not explicitly provide a value and no related information exists:

{
  "frequency": "NOT_FOUND"
}

11. Use exact values from the document whenever possible.

12. Output valid JSON only.

13. No explanations outside of _notes fields.

14. No assumptions and hardcoded values.

Every requirement key MUST exist somewhere in the output — either in general_fields or 
in models_specs for each model.
"""


specalised_agent = create_agent(
    model=llm,
    system_prompt=extraction_system_prompt,
)


def manufacturer_to_json(
    pdf_path: str,
    start_page: int,
    end_page: int,
) -> dict:
    
    if Path(pdf_path).stem in [Path(p).stem for p in Path("data/extracted_json").glob("*.json")]:
        print(f"JSON for {pdf_path} already exists. Loading from file.")
        with open(f"data/extracted_json/{(Path(pdf_path).stem)}.json","r",encoding="utf-8") as f:
            return json.load(f)
    
    md_content = extract_pdf_pages_as_markdown(
        pdf_path=pdf_path,
        start_page=start_page,
        end_page=end_page,
    )

    result = specalised_agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": md_content,
            }
        ]
    })

    last_msg = result["messages"][-1]
    cleaned_json = last_msg.content.replace("```json", "").replace("```", "").strip()

    
  
    with open(f"data/extracted_json/{(Path(pdf_path).stem)}.json","w",encoding="utf-8") as f:
        json.dump(json.loads(cleaned_json), f, indent=2)
    return json.loads(cleaned_json)


if __name__ == "__main__":
    output = manufacturer_to_json(
        requirements_json_path="data/extracted_json/requirements.json",
        pdf_path="data/input/DSS_GZES230100125901_combined-1.pdf",
        start_page=1,
        end_page=72,
    )
    print(json.dumps(output, indent=2))