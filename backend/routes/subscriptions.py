import uuid
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
import stripe

from core.config import FRONTEND_URL, STRIPE_WEBHOOK_SECRET
from core.database import db
from core.security import get_current_user
from models.schemas import User, CheckoutRequest
from services.stripe_service import SUBSCRIPTION_PLANS, ensure_stripe_products
from services.email import send_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["subscriptions"])


@router.get("/plans")
async def get_plans():
    return {"plans": {k: v.model_dump() for k, v in SUBSCRIPTION_PLANS.items()}}


@router.post("/subscriptions/create-checkout")
async def create_checkout_session(data: CheckoutRequest, user: User = Depends(get_current_user)):
    plan = data.plan
    if plan not in SUBSCRIPTION_PLANS or plan == "starter":
        raise HTTPException(status_code=400, detail="Invalid plan")
    plan_data = SUBSCRIPTION_PLANS[plan]
    if not stripe.api_key:
        return {"url": f"{FRONTEND_URL}/dashboard?plan={plan}&demo=true", "demo": True}
    await ensure_stripe_products()
    if not plan_data.stripe_price_id:
        return {"url": f"{FRONTEND_URL}/dashboard?plan={plan}&demo=true", "demo": True}
    try:
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email, name=user.name, metadata={"user_id": user.id})
            await db.users.update_one({"id": user.id}, {"$set": {"stripe_customer_id": customer.id}})
            customer_id = customer.id
        else:
            customer_id = user.stripe_customer_id
        session = stripe.checkout.Session.create(
            customer=customer_id, payment_method_types=["card"],
            line_items=[{"price": plan_data.stripe_price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{FRONTEND_URL}/dashboard?success=true&plan={plan}",
            cancel_url=f"{FRONTEND_URL}/pricing?canceled=true",
            metadata={"user_id": user.id, "plan": plan}
        )
        return {"url": session.url, "session_id": session.id}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout failed: {e}")
        raise HTTPException(status_code=500, detail="Payment processing failed")


@router.post("/subscriptions/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if STRIPE_WEBHOOK_SECRET and sig_header:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except ValueError:
            logger.error("Stripe webhook: Invalid payload")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Stripe webhook: Invalid signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        event = json.loads(payload)

    event_id = event.get("id", "")
    event_type = event.get("type", "")
    logger.info(f"Stripe webhook received: {event_type} (id: {event_id})")

    existing = await db.webhook_events.find_one({"event_id": event_id})
    if existing:
        logger.info(f"Skipping duplicate webhook event: {event_id}")
        return {"received": True, "duplicate": True}
    await db.webhook_events.insert_one({
        "event_id": event_id, "type": event_type,
        "processed_at": datetime.now(timezone.utc).isoformat()
    })

    try:
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session.get("metadata", {}).get("user_id")
            plan = session.get("metadata", {}).get("plan")
            subscription_id = session.get("subscription")
            customer_id = session.get("customer")
            if user_id and plan:
                plan_data = SUBSCRIPTION_PLANS.get(plan)
                if plan_data:
                    await db.users.update_one(
                        {"id": user_id},
                        {"$set": {
                            "plan": plan, "credits": plan_data.credits, "credits_used": 0,
                            "stripe_subscription_id": subscription_id,
                            "stripe_customer_id": customer_id,
                        }}
                    )
                    await db.subscriptions.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "user_id": user_id, "plan": plan,
                            "stripe_subscription_id": subscription_id,
                            "stripe_customer_id": customer_id,
                            "status": "active",
                            "current_period_start": session.get("current_period_start"),
                            "current_period_end": session.get("current_period_end"),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }},
                        upsert=True,
                    )
                    logger.info(f"User {user_id} upgraded to {plan}")

        elif event_type == "invoice.payment_succeeded":
            invoice = event["data"]["object"]
            customer_id = invoice.get("customer")
            amount = invoice.get("amount_paid", 0)
            if customer_id:
                user_doc = await db.users.find_one({"stripe_customer_id": customer_id}, {"_id": 0})
                if user_doc:
                    plan_data = SUBSCRIPTION_PLANS.get(user_doc.get("plan", "starter"))
                    if plan_data:
                        await db.users.update_one(
                            {"stripe_customer_id": customer_id},
                            {"$set": {"credits": plan_data.credits, "credits_used": 0}}
                        )
                    await db.payments.insert_one({
                        "id": str(uuid.uuid4()),
                        "user_id": user_doc["id"],
                        "stripe_invoice_id": invoice.get("id"),
                        "amount": amount,
                        "currency": invoice.get("currency", "usd"),
                        "status": "succeeded",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                    logger.info(f"Payment succeeded for customer {customer_id}: ${amount/100:.2f}")

        elif event_type == "invoice.payment_failed":
            invoice = event["data"]["object"]
            customer_id = invoice.get("customer")
            if customer_id:
                user_doc = await db.users.find_one({"stripe_customer_id": customer_id}, {"_id": 0})
                if user_doc:
                    await db.payments.insert_one({
                        "id": str(uuid.uuid4()),
                        "user_id": user_doc["id"],
                        "stripe_invoice_id": invoice.get("id"),
                        "amount": invoice.get("amount_due", 0),
                        "currency": invoice.get("currency", "usd"),
                        "status": "failed",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                    html = f"""<div style="font-family:Arial;max-width:600px;margin:0 auto;background:#0F172A;color:#E2E8F0;padding:30px;">
                        <h2 style="color:#EF4444;">Payment Failed</h2>
                        <p>Hi {user_doc.get('name','')}, your latest payment failed. Please update your payment method to continue using CursorCode AI.</p>
                        <a href="{FRONTEND_URL}/settings" style="display:inline-block;background:#3B82F6;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;margin-top:16px;">Update Payment</a>
                    </div>"""
                    await send_email(user_doc["email"], "Payment Failed - CursorCode AI", html)
                    logger.warning(f"Payment failed for customer {customer_id}")

        elif event_type == "customer.subscription.updated":
            subscription = event["data"]["object"]
            customer_id = subscription.get("customer")
            status = subscription.get("status")
            if customer_id:
                update_fields = {"stripe_subscription_status": status}
                if status == "past_due":
                    logger.warning(f"Subscription past due for customer {customer_id}")
                elif status in ("canceled", "unpaid"):
                    update_fields.update({"plan": "starter", "credits": 10, "credits_used": 0, "stripe_subscription_id": None})
                await db.users.update_one({"stripe_customer_id": customer_id}, {"$set": update_fields})
                await db.subscriptions.update_one(
                    {"stripe_customer_id": customer_id},
                    {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
                )

        elif event_type == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            customer_id = subscription.get("customer")
            if customer_id:
                await db.users.update_one(
                    {"stripe_customer_id": customer_id},
                    {"$set": {"plan": "starter", "credits": 10, "credits_used": 0, "stripe_subscription_id": None}}
                )
                await db.subscriptions.update_one(
                    {"stripe_customer_id": customer_id},
                    {"$set": {"status": "canceled", "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                logger.info(f"Subscription canceled for customer {customer_id}")

    except Exception as e:
        logger.error(f"Webhook processing error for {event_type}: {e}")

    return {"received": True}


@router.get("/subscriptions/current")
async def get_current_subscription(user: User = Depends(get_current_user)):
    plan = SUBSCRIPTION_PLANS.get(user.plan, SUBSCRIPTION_PLANS["starter"])
    return {
        "plan": user.plan, "plan_details": plan.model_dump(),
        "credits": user.credits, "credits_used": user.credits_used,
        "credits_remaining": user.credits - user.credits_used
    }
