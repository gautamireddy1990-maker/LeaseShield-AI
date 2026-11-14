"""Stripe Checkout endpoints for one-time audits and broker subscriptions."""
import os
import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Literal

from backend.api.routes import REPORTS

router = APIRouter(prefix="/api/payments")

class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_id: str
    plan_type: Literal["single_audit", "broker_pro"]

@router.post("/create-checkout-session")
def create_checkout_session(body: CheckoutRequest):
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        raise HTTPException(503, "Stripe is not configured")
    if body.report_id not in REPORTS:
        raise HTTPException(404, "Report not found")
    if body.plan_type == "single_audit":
        price = os.getenv("STRIPE_SINGLE_AUDIT_PRICE_ID")
        mode = "payment"
    else:
        price = os.getenv("STRIPE_PRO_SUB_PRICE_ID")
        mode = "subscription"
    if not price:
        raise HTTPException(503, "The requested Stripe price is not configured")
    origin = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    try:
        session = stripe.checkout.Session.create(
            mode=mode, line_items=[{"price": price, "quantity": 1}],
            metadata={"report_id": body.report_id, "plan_type": body.plan_type},
            success_url=f"{origin}/dashboard/{body.report_id}?checkout=success",
            cancel_url=f"{origin}/dashboard/{body.report_id}?checkout=cancelled",
        )
        REPORTS[body.report_id] = REPORTS[body.report_id].model_copy(update={"stripe_session_id": session.id})
        return {"url": session.url}
    except stripe.StripeError as exc:
        raise HTTPException(502, f"Stripe checkout could not be created: {exc.user_message or str(exc)}") from exc

@router.post("/webhook")
async def stripe_webhook(request: Request):
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(503, "Stripe webhook is not configured")
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, signature, secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(400, "Invalid Stripe webhook signature or payload") from exc
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        report_id = (session.get("metadata") or {}).get("report_id")
        report = REPORTS.get(report_id) if report_id else None
        if report and (session.get("mode") == "subscription" or session.get("payment_status") == "paid"):
            REPORTS[report_id] = report.model_copy(update={"is_unlocked": True, "stripe_session_id": session.get("id")})
    return {"received": True}
