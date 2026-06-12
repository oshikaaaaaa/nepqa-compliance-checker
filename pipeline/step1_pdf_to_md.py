"""
pdf_extract_utils.py
Extract text as Markdown from PDF pages using pdfplumber (+ pypdf fallback).
No external API required.

Usage:
    from pdf_extract_utils import extract_pdf_pages_as_markdown

    md = extract_pdf_pages_as_markdown(
        pdf_path="document.pdf",
        start_page=18,
        end_page=19,
    )
    print(md)
"""

from pathlib import Path

from numpy import rint


def fill_spanning_cells_bbox(page, table_obj) -> list[list]:
    """
    Use bounding box width to detect spanning cells.
    A spanning cell will be physically wider than a normal cell.
    Repeats the value across all columns it spans.
    """
    col_count = len(table_obj.rows[0].cells)
    page_table_width = table_obj.bbox[2] - table_obj.bbox[0]
    typical_col_width = page_table_width / col_count

    rows = []
    for row in table_obj.rows:
        new_row = []
        for cell in row.cells:

            if cell is None:                  
                new_row.append("")           
                continue                        

            # Guard against malformed/zero-size cells
            if cell[2] - cell[0] < 1 or cell[3] - cell[1] < 1:
                new_row.append("")
                continue

            cell_width = cell[2] - cell[0]
            text = page.within_bbox(cell).extract_text() or ""
            text = text.strip()

            # If cell is wider than 1.5x a normal col, it's spanning
            is_spanning = cell_width > typical_col_width * 1.5
            repeat_count = round(cell_width / typical_col_width) if is_spanning else 1

            new_row.extend([text] * repeat_count)
        rows.append(new_row)

    return rows


def extract_pdf_pages_as_markdown(
    pdf_path: str,
    start_page: int,
    end_page: int,
    save_path: str | None = None,
) -> str:
    """
    Extract text from PDF pages [start_page, end_page] and return as Markdown.

    Args:
        pdf_path:   Path to the source PDF file.
        start_page: First page to extract (1-based).
        end_page:   Last page to extract (1-based, inclusive).
        save_path:  Optional path to save the Markdown output (e.g. "output.md").
                    If None, the result is returned but not saved.

    Returns:
        Extracted text as a Markdown string.
    """
    pdf_name = Path(pdf_path).stem
    print(pdf_name)

    if pdf_name in [p.stem for p in Path("data/extracted_md").glob("*.md")]:
        print(f"Markdown for {pdf_name} already exists. Loading from file.")
        return Path(f"data/extracted_md/{pdf_name}.md").read_text(encoding="utf-8")
    
    try:
        import pdfplumber
    except ImportError:
        import subprocess
        subprocess.check_call(["pip", "install", "pdfplumber", "-q", "--break-system-packages"])
        import pdfplumber

    sections: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        actual_end = min(end_page, total)

        for page_num in range(start_page, actual_end + 1):
            page = pdf.pages[page_num - 1]  # pdfplumber is 0-indexed

            parts: list[str] = [f"## Page {page_num}\n"]

            # ── Tables ──────────────────────────────────────────────────────
            found_tables = page.find_tables()  # table objects with bbox info
            table_bboxes = [t.bbox for t in found_tables]

            for table_obj in found_tables:
                if not table_obj.rows:
                    continue

                # Use bbox-aware spanning cell detection
                filled_rows = fill_spanning_cells_bbox(page, table_obj)

                md_rows: list[str] = []
                for i, row in enumerate(filled_rows):
                    cells = [str(c or "").replace("\n", " ").strip() for c in row]
                    md_rows.append("| " + " | ".join(cells) + " |")
                    if i == 0:
                        md_rows.append("| " + " | ".join("---" for _ in cells) + " |")
                parts.append("\n".join(md_rows))

            # ── Text (excluding table regions) ───────────────────────────
            if table_bboxes:
                # Crop away table areas so text isn't duplicated
                remaining = page
                for bbox in table_bboxes:
                    try:
                        remaining = remaining.filter(
                            lambda obj, b=bbox: not (
                                b[0] <= obj.get("x0", 0) and obj.get("x1", 0) <= b[2]
                                and b[1] <= obj.get("top", 0) and obj.get("bottom", 0) <= b[3]
                            )
                        )
                    except Exception:
                        pass
                text = remaining.extract_text(x_tolerance=3, y_tolerance=3) or ""
            else:
                text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""

            if text.strip():
                parts.append(text.strip())

            sections.append("\n\n".join(p for p in parts if p.strip()))

    markdown = "\n\n---\n\n".join(sections)

    if save_path:
        Path(save_path).write_text(markdown, encoding="utf-8")

    return markdown


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    pdf      = "data/input/manufacture1.pdf"
    start    = 1
    end      = 72
    out_path = "data/extracted_md/manufacture1.md"

    result = extract_pdf_pages_as_markdown(pdf, start_page=start, end_page=end, save_path=out_path)
    # print(result)