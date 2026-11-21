"""HTTP routes for lease audits, reports, and calendar reminders."""

from __future__ import annotations

import os
import re
import tempfile
import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from starlette.background import BackgroundTask

from backend.models.schemas import LeaseAuditReport
from backend.services.clause_auditor import audit_lease_document
from backend.services.pdf_parser import extract_pages_from_pdf
from backend.services.report_exporter import generate_audit_pdf

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
UPLOAD_DIR = Path(os.getenv("LEASESHIELD_UPLOAD_DIR", Path(tempfile.gettempdir()) / "leaseshield-uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORTS: dict[str, LeaseAuditReport] = {}


def _preview_report(report: LeaseAuditReport) -> LeaseAuditReport:
    if report.is_unlocked:
        return report
    flags = [flag.model_copy(update={"recommended_redline": "Unlock the full audit to view this counter-clause." , "verbatim_quote": "Unlock the full audit to view cited lease text."}) for flag in report.risk_flags]
    return report.model_copy(update={"risk_flags": flags, "landlord_negotiation_email": "Unlock the full audit to view your negotiation email."})


@router.post("/audit", response_model=LeaseAuditReport)
async def create_audit(file: UploadFile = File(...)) -> LeaseAuditReport:
    filename = Path(file.filename or "lease.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload must be a PDF file")

    temp_path = UPLOAD_DIR / f"{uuid4().hex}.pdf"
    size = 0
    try:
        with temp_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="PDF exceeds the 25 MB upload limit")
                destination.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="Uploaded PDF is empty")

        pages = extract_pages_from_pdf(str(temp_path))
        logger.info("Extracted %d pages from upload %s; starting audit", len(pages), filename)
        report = await audit_lease_document(pages, filename)
        REPORTS[report.report_id] = report
        logger.info("Completed lease audit %s", report.report_id)
        return _preview_report(report)
    except (asyncio.TimeoutError, TimeoutError) as exc:
        logger.exception("Lease audit timed out for %s", filename)
        raise HTTPException(status_code=504, detail="The audit service timed out while generating the report. Check the LLM endpoint and try again.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Lease audit failed for %s", filename)
        raise HTTPException(status_code=422, detail=f"Could not process lease PDF: {exc}") from exc
    finally:
        await file.close()
        temp_path.unlink(missing_ok=True)


@router.get("/report/{report_id}", response_model=LeaseAuditReport)
async def get_report(report_id: str) -> LeaseAuditReport:
    report = REPORTS.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _preview_report(report)


@router.get("/report/{report_id}/export-pdf")
async def export_report_pdf(report_id: str) -> FileResponse:
    report = REPORTS.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.is_unlocked:
        raise HTTPException(status_code=403, detail="Unlock this report to export the full audit")
    path = generate_audit_pdf(report)
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", Path(report.file_name).stem) or "lease-audit"
    return FileResponse(path, media_type="application/pdf", filename=f"{safe_name}-leaseshield-audit.pdf", background=BackgroundTask(Path(path).unlink, missing_ok=True))


def _parse_calendar_date(value: str) -> date | None:
    """Parse common explicit date formats; skip vague, non-calendar deadlines."""
    candidate = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    # ISO timestamps are accepted too.
    try:
        return datetime.fromisoformat(candidate.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _ics_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@router.get("/report/{report_id}/calendar")
async def download_calendar(report_id: str) -> Response:
    report = REPORTS.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//LeaseShield AI//Lease Deadlines//EN", "CALSCALE:GREGORIAN"]
    for critical_date in report.critical_dates:
        deadline = _parse_calendar_date(critical_date.date_or_deadline)
        if deadline is None:
            continue
        reminder = deadline - timedelta(days=30)
        uid = f"{uuid4()}@leaseshield.ai"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{reminder:%Y%m%d}",
            f"SUMMARY:{_ics_escape('Lease notice reminder: ' + critical_date.event_name)}",
            f"DESCRIPTION:{_ics_escape(critical_date.action_required + ' Deadline: ' + critical_date.date_or_deadline)}",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    ics = "\r\n".join(lines) + "\r\n"
    safe_report_id = re.sub(r"[^A-Za-z0-9_-]", "_", report.report_id)
    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_report_id}-reminders.ics"'},
    )
