from pipeline.step2_manufacturer_to_json import manufacturer_to_json
from pipeline.step2_nepqa_to_json import nepqa_extract_requirements_to_json
from pipeline.step3_generate_report import generate_report



nepalqa_requirements = nepqa_extract_requirements_to_json(pdffile="data/input/nepalqa.pdf", start_page=18, end_page=19)
specs1 = manufacturer_to_json(pdf_path="data/input/manufacture1.pdf", start_page=1, end_page=4)
specs2 = manufacturer_to_json(pdf_path="data/input/manufacture2.pdf", start_page=1, end_page=72)

generate_report()