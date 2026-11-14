"""Print-ready executive lease audit PDF generation."""

from datetime import date
from pathlib import Path
import tempfile
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

from backend.models.schemas import LeaseAuditReport, RiskFlag


NAVY = colors.HexColor("#10243A")
BLUE = colors.HexColor("#175CD3")
PALE = colors.HexColor("#F1F5F9")
SEVERITY = {"HIGH": colors.HexColor("#FEE2E2"), "MEDIUM": colors.HexColor("#FEF3C7"), "LOW": colors.HexColor("#DCFCE7")}
DISCLAIMER = "Informational AI analysis only; not legal advice. Review final redlines with a licensed real estate attorney."


def _p(value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(value).replace("\n", "<br/>"), style)


def generate_audit_pdf(report: LeaseAuditReport) -> str:
    """Generate a printable PDF and return its temporary filesystem path."""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="LeaseTitle", parent=styles["Title"], textColor=NAVY, alignment=TA_LEFT, fontSize=20, leading=24, spaceAfter=8))
    styles.add(ParagraphStyle(name="LeaseBody", parent=styles["BodyText"], fontSize=9, leading=13))
    styles.add(ParagraphStyle(name="LeaseSmall", parent=styles["BodyText"], fontSize=8, leading=11, textColor=colors.HexColor("#475569")))
    styles.add(ParagraphStyle(name="LeaseSection", parent=styles["Heading2"], textColor=NAVY, spaceBefore=14, spaceAfter=7))
    styles.add(ParagraphStyle(name="LeaseQuote", parent=styles["BodyText"], fontName="Helvetica-Oblique", fontSize=9, leading=13))
    fd, path = tempfile.mkstemp(prefix="leaseshield-report-", suffix=".pdf")
    import os
    os.close(fd)
    def footer(canvas, doc):
        canvas.saveState(); canvas.setFont("Helvetica", 7); canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(0.65*inch, 0.38*inch, DISCLAIMER); canvas.drawRightString(7.85*inch, 0.38*inch, f"{doc.page}"); canvas.restoreState()
    doc = SimpleDocTemplate(path, pagesize=letter, rightMargin=.65*inch, leftMargin=.65*inch, topMargin=.6*inch, bottomMargin=.7*inch, title=f"LeaseShield AI Audit - {report.file_name}")
    story = [_p("LeaseShield AI — Commercial Lease Risk Audit", styles["LeaseTitle"]), _p(f"File: {report.file_name}  |  Audit date: {date.today().isoformat()}", styles["LeaseSmall"]), Spacer(1, 8)]
    score_color = "#FEE2E2" if report.overall_risk_score >= 70 else "#FEF3C7" if report.overall_risk_score >= 40 else "#DCFCE7"
    badge = Table([[f"OVERALL RISK SCORE   {report.overall_risk_score} / 100"]], colWidths=[2.6*inch]); badge.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(score_color)),("TEXTCOLOR",(0,0),(-1,-1),NAVY),("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),("PADDING",(0,0),(-1,-1),8)])); story += [badge, Paragraph("Financial Summary", styles["LeaseSection"])]
    fs = report.financial_summary
    money = lambda v: f"${v:,.2f}"
    rows = [["Item", "Amount"], ["Base Monthly Rent", money(fs.base_monthly_rent)], ["Estimated CAM / NNN", money(fs.estimated_cam_nnn)], ["Total Monthly Outflow", money(fs.total_estimated_monthly_outflow)], ["Security Deposit", money(fs.security_deposit)]]
    table=Table([[ _p(str(c),styles["LeaseBody"]) for c in row] for row in rows], colWidths=[4.8*inch,2*inch]); table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.HexColor("#CBD5E1")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE]),("PADDING",(0,0),(-1,-1),7)])); story += [table, _p("Annual escalations: " + fs.annual_escalation_summary, styles["LeaseSmall"]), Paragraph("Critical Dates",styles["LeaseSection"])]
    dates=[["Deadline", "Notice", "Required Action"]]+[[d.date_or_deadline, f"{d.notice_period_days} days" if d.notice_period_days is not None else "Not specified", d.event_name+": "+d.action_required] for d in report.critical_dates]
    dt=Table([[_p(str(c),styles["LeaseBody"]) for c in row] for row in dates],colWidths=[1.5*inch,1*inch,4.3*inch],repeatRows=1); dt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.HexColor("#CBD5E1")),("PADDING",(0,0),(-1,-1),6)])); story += [dt]
    for severity in ("HIGH","MEDIUM","LOW"):
        flags=[f for f in report.risk_flags if f.severity==severity]
        if not flags: continue
        story.append(Paragraph(f"{severity} Risk Flags",styles["LeaseSection"]))
        for f in flags:
            story.append(KeepTogether([Paragraph(escape(f.title),styles["Heading3"]),_p(f"{f.section_reference} · Page {f.page_number}",styles["LeaseSmall"]),Spacer(1,4)]))
            quote=Table([[_p('“'+f.verbatim_quote+'”',styles["LeaseQuote"])]],colWidths=[6.8*inch]); quote.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),SEVERITY[severity]),("BOX",(0,0),(-1,-1),.5,colors.HexColor("#CBD5E1")),("PADDING",(0,0),(-1,-1),9)])); story += [quote, _p("Risk: "+f.plain_english_explanation,styles["LeaseBody"]),Spacer(1,4),_p("Recommended counter-clause: "+f.recommended_redline,styles["LeaseBody"]),Spacer(1,10)]
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return path
