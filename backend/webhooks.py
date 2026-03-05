"""
CursorCode AI - Webhooks
Stripe and external webhook handling
"""

from fastapi import APIRouter, Request, HTTPException
import stripe
import os
from backend.db_models import Payments

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET_KEY

router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Handle payment success
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        Payments.insert_one({
            "user_email": session["metadata"]["user_email"],
            "amount": session["amount_total"],
            "currency": session["currency"],
            "status": "paid",
            "session_id": session["id"]
        })

    return {"status": "success"}
