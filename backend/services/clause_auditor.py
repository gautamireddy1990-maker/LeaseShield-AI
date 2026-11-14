"""LLM-backed, source-verified commercial lease auditing."""

from __future__ import annotations

import os
from uuid import uuid4

from openai import AsyncOpenAI

from backend.models.schemas import LeaseAuditReport
from backend.prompts.cre_audit_rubric import CRE_AUDIT_SYSTEM_PROMPT


def _get_client() -> AsyncOpenAI:
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set LLM_API_KEY (or OPENAI_API_KEY) to enable lease audits")
    base_url = os.getenv("LLM_BASE_URL")
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def audit_lease_document(pages: list[dict], file_name: str) -> LeaseAuditReport:
    """Audit page-tagged lease content and verify citations against the input."""
    if not pages:
        raise ValueError("No pages were extracted from the PDF")

    page_map: dict[int, str] = {}
    tagged_text: list[str] = []
    for page in pages:
        number = page.get("page_number")
        content = page.get("content")
        if not isinstance(number, int) or number < 1 or not isinstance(content, str):
            raise ValueError("Each page must contain a positive integer page_number and string content")
        page_map[number] = content
        tagged_text.append(f"<<< PAGE {number} >>>\n{content}\n<<< END PAGE {number} >>>")

    client = _get_client()
    response = await client.beta.chat.completions.parse(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": CRE_AUDIT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Audit this lease file: {file_name}\n\n"
                    "Treat the page markers as authoritative citation boundaries.\n\n"
                    + "\n\n".join(tagged_text)
                ),
            },
        ],
        response_format=LeaseAuditReport,
    )
    report = response.choices[0].message.parsed
    if report is None:
        raise RuntimeError("The LLM returned no structured lease audit")

    # Structured output enforces shape; this check enforces source provenance.
    for flag in report.risk_flags:
        cited_page = page_map.get(flag.page_number)
        if cited_page is None or not flag.verbatim_quote or flag.verbatim_quote not in cited_page:
            raise ValueError(
                f"Risk flag {flag.id!r} has a quote that does not exactly match page {flag.page_number}"
            )

    # Keep identifiers/filename tied to the uploaded document, not model guesses.
    return report.model_copy(update={"report_id": str(uuid4()), "file_name": file_name})
