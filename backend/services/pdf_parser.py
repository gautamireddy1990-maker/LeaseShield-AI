"""PDF text/table extraction with OCR fallback for scanned pages."""

from __future__ import annotations

from typing import Any

import pdfplumber
import pytesseract


OCR_TEXT_THRESHOLD = 50


def _clean_cell(value: Any) -> str:
    """Normalize a table cell for readable Markdown output."""
    if value is None:
        return ""
    return " ".join(str(value).replace("|", "\\|").split())


def _table_to_markdown(table: list[list[Any]] | None) -> str:
    """Format a pdfplumber table as a Markdown table."""
    if not table:
        return ""

    rows = [[_clean_cell(cell) for cell in row] for row in table]
    width = max((len(row) for row in rows), default=0)
    if width == 0:
        return ""

    # Keep rows rectangular so Markdown columns stay aligned.
    rows = [row + [""] * (width - len(row)) for row in rows]
    header = rows[0]
    separator = ["---"] * width
    markdown_rows = [header, separator, *rows[1:]]
    return "\n".join("| " + " | ".join(row) + " |" for row in markdown_rows)


def extract_pages_from_pdf(file_path: str) -> list[dict]:
    """Extract each PDF page's text and tables, using OCR for sparse pages.

    The returned page numbers are one-based, matching the numbering people see
    in PDF viewers. OCR is triggered when native text extraction contains fewer
    than 50 non-whitespace characters. Tables are included as Markdown after
    the page's extracted text.
    """
    extracted_pages: list[dict] = []

    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""

            if len("".join(text.split())) < OCR_TEXT_THRESHOLD:
                image = page.to_image(resolution=300).original
                text = pytesseract.image_to_string(image) or ""

            table_blocks = [
                _table_to_markdown(table)
                for table in page.extract_tables()
            ]
            table_blocks = [block for block in table_blocks if block]

            content_parts = [text.strip()] if text.strip() else []
            content_parts.extend(table_blocks)
            extracted_pages.append(
                {
                    "page_number": page_number,
                    "content": "\n\n".join(content_parts),
                }
            )

    return extracted_pages
