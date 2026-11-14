"""Strict response models for LeaseShield AI lease audits."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model that rejects unknown fields and implicit coercion."""

    model_config = ConfigDict(extra="forbid", strict=True)


class FinancialSummary(StrictModel):
    base_monthly_rent: float
    estimated_cam_nnn: float
    total_estimated_monthly_outflow: float
    security_deposit: float
    annual_escalation_summary: str


class CriticalDate(StrictModel):
    event_name: str
    date_or_deadline: str
    notice_period_days: int | None
    action_required: str


class RiskFlag(StrictModel):
    id: str
    category: Literal[
        "CAM_NNN",
        "PERSONAL_GUARANTEE",
        "RENT_ESCALATION",
        "HVAC_REPAIRS",
        "SUBLEASE_EXIT",
        "AUTO_RENEWAL",
        "OTHER",
    ]
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    title: str
    plain_english_explanation: str
    page_number: int = Field(ge=1)
    section_reference: str
    verbatim_quote: str
    recommended_redline: str


class LeaseAuditReport(StrictModel):
    report_id: str
    file_name: str
    overall_risk_score: int = Field(ge=1, le=100)
    financial_summary: FinancialSummary
    critical_dates: list[CriticalDate]
    risk_flags: list[RiskFlag]
    landlord_negotiation_email: str
    is_unlocked: bool = False
    stripe_session_id: str | None = None
