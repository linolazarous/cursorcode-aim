"""
CursorCode AI - Subscription & Payment Routes
JengaHQ-powered billing with IPN webhooks and recurring billing engine.
"""

import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request

from core.config import FRONTEND_URL
from core.database import db
from core.security import get_current_user
from models.schemas import User, CheckoutRequest
from services.stripe_service import SUBSCRIPTION_PLANS
from services.jenga import (
    is_demo_mode, create_payment_link, process_card_payment,
    verify_ipn_signature
)
from services.email import send_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["subscriptions"])


# ==================== PLANS ====================

@router.get("/plans")
async def get_plans():
    return {"plans": {k: v.model_dump() for k, v in SUBSCRIPTION_PLANS.items()}}


# ==================== CHECKOUT (JengaHQ) ====================

@router.post("/payments/create-order")
async def create_payment_order(data: CheckoutRequest, user: User = Depends(get_current_user)):
    """Create a JengaHQ payment link for subscription checkout."""
    plan = data.plan
    if plan not in SUBSCRIPTION_PLANS or plan == "starter":
        raise HTTPException(status_code=400, detail="Invalid plan")

    plan_data = SUBSCRIPTION_PLANS[plan]
    reference = f"CC-{user.id[:8]}-{plan}-{uuid.uuid4().hex[:8]}"

    callback_url = f"{FRONTEND_URL}/api/webhooks/jenga"
    redirect_url = f"{FRONTEND_URL}/dashboard?success=true&plan={plan}"

    result = await create_payment_link(
        amount=plan_data.price,
        reference=reference,
        description=f"CursorCode AI {plan_data.name} Plan - {plan_data.credits} credits/month",
        customer_email=user.email,
        customer_name=user.name,
        callback_url=callback_url,
        redirect_url=redirect_url,
    )

    # Store pending order in DB
    await db.payment_orders.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user.id,
        "plan": plan,
        "amount": plan_data.price,
        "currency": "USD",
        "reference": result["reference"],
        "status": "pending",
        "demo": result.get("demo", False),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    if result.get("demo"):
        # In demo mode, auto-complete the subscription
        await _activate_subscription(user.id, plan, reference, demo=True)
        return {
            "url": f"{FRONTEND_URL}/dashboard?success=true&plan={plan}",
            "demo": True,
            "reference": result["reference"],
            "message": "Demo mode — JengaHQ keys not configured. Subscription activated.",
        }

    return {
        "url": result["checkout_url"],
        "reference": result["reference"],
        "demo": False,
    }


# Keep legacy endpoint for backward compat
@router.post("/subscriptions/create-checkout")
async def create_checkout_session(data: CheckoutRequest, user: User = Depends(get_current_user)):
    """Legacy endpoint — redirects to JengaHQ payment flow."""
    return await create_payment_order(data, user)


# ==================== IPN WEBHOOK (JengaHQ) ====================

@router.post("/webhooks/jenga")
async def jenga_ipn_webhook(request: Request):
    """JengaHQ IPN (Instant Payment Notification) handler."""
    payload = await request.json()
    signature = request.headers.get("X-Jenga-Signature", "")

    event_ref = payload.get("reference") or payload.get("externalRef") or ""
    logger.info(f"JengaHQ IPN received: ref={event_ref}")

    # Verify signature
    if not verify_ipn_signature(payload, signature):
        logger.error("JengaHQ IPN: Invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Idempotency check
    existing = await db.webhook_events.find_one({"event_id": event_ref})
    if existing:
        logger.info(f"Skipping duplicate IPN: {event_ref}")
        return {"received": True, "duplicate": True}

    await db.webhook_events.insert_one({
        "event_id": event_ref,
        "type": "jenga_ipn",
        "payload": payload,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    })

    # Find the pending order
    order = await db.payment_orders.find_one({"reference": event_ref}, {"_id": 0})
    if not order:
        logger.warning(f"JengaHQ IPN: No matching order for ref={event_ref}")
        return {"received": True, "matched": False}

    # Check payment status
    status = payload.get("status", "").upper()
    transaction_id = payload.get("transactionId") or payload.get("transaction_id") or ""

    if status in ("SUCCESS", "COMPLETED", "PAID", "00"):
        # Activate subscription
        await _activate_subscription(
            user_id=order["user_id"],
            plan=order["plan"],
            reference=event_ref,
            transaction_id=transaction_id,
            card_token=payload.get("cardToken") or payload.get("token"),
        )

        # Update order status
        await db.payment_orders.update_one(
            {"reference": event_ref},
            {"$set": {"status": "completed", "transaction_id": transaction_id,
                      "completed_at": datetime.now(timezone.utc).isoformat()}}
        )

        logger.info(f"Subscription activated via IPN: user={order['user_id']}, plan={order['plan']}")

    elif status in ("FAILED", "DECLINED", "CANCELLED"):
        await db.payment_orders.update_one(
            {"reference": event_ref},
            {"$set": {"status": "failed", "completed_at": datetime.now(timezone.utc).isoformat()}}
        )

        # Notify user
        user_doc = await db.users.find_one({"id": order["user_id"]}, {"_id": 0})
        if user_doc:
            html = f"""<div style="font-family:Arial;max-width:600px;margin:0 auto;background:#0F172A;color:#E2E8F0;padding:30px;">
                <h2 style="color:#EF4444;">Payment Failed</h2>
                <p>Hi {user_doc.get('name','')}, your payment for {order['plan']} plan was not completed. Please try again.</p>
                <a href="{FRONTEND_URL}/pricing" style="display:inline-block;background:#3B82F6;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;margin-top:16px;">Try Again</a>
            </div>"""
            await send_email(user_doc["email"], "Payment Failed - CursorCode AI", html)

        logger.warning(f"Payment failed via IPN: ref={event_ref}")

    return {"received": True}


# ==================== RECURRING BILLING ENGINE ====================

@router.post("/billing/process-renewals")
async def process_renewals():
    """Process due recurring subscriptions. Called by cron or admin."""
    now = datetime.now(timezone.utc)
    due_subs = await db.subscriptions.find({
        "status": "active",
        "next_billing_date": {"$lte": now.isoformat()},
        "card_token": {"$exists": True, "$ne": None},
    }, {"_id": 0}).to_list(100)

    results = {"processed": 0, "succeeded": 0, "failed": 0}

    for sub in due_subs:
        user_doc = await db.users.find_one({"id": sub["user_id"]}, {"_id": 0})
        if not user_doc:
            continue

        plan_data = SUBSCRIPTION_PLANS.get(sub.get("plan", "starter"))
        if not plan_data or plan_data.price == 0:
            continue

        reference = f"RENEW-{sub['user_id'][:8]}-{uuid.uuid4().hex[:8]}"

        result = await process_card_payment(
            amount=plan_data.price,
            reference=reference,
            card_token=sub["card_token"],
            customer_email=user_doc["email"],
        )

        results["processed"] += 1

        if result.get("success"):
            # Reset credits and advance billing date
            next_date = (now + timedelta(days=30)).isoformat()
            await db.users.update_one(
                {"id": sub["user_id"]},
                {"$set": {"credits": plan_data.credits, "credits_used": 0}}
            )
            await db.subscriptions.update_one(
                {"user_id": sub["user_id"]},
                {"$set": {
                    "next_billing_date": next_date,
                    "last_payment_date": now.isoformat(),
                    "updated_at": now.isoformat(),
                }}
            )

            # Record payment
            await db.payments.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": sub["user_id"],
                "reference": reference,
                "transaction_id": result.get("transaction_id", ""),
                "amount": plan_data.price,
                "currency": "USD",
                "type": "renewal",
                "status": "succeeded",
                "created_at": now.isoformat(),
            })

            results["succeeded"] += 1
            logger.info(f"Renewal succeeded: user={sub['user_id']}")
        else:
            results["failed"] += 1
            logger.warning(f"Renewal failed: user={sub['user_id']}")

    return results


# ==================== SUBSCRIPTION MANAGEMENT ====================

@router.get("/subscriptions/current")
async def get_current_subscription(user: User = Depends(get_current_user)):
    plan = SUBSCRIPTION_PLANS.get(user.plan, SUBSCRIPTION_PLANS["starter"])
    sub = await db.subscriptions.find_one({"user_id": user.id}, {"_id": 0})
    return {
        "plan": user.plan,
        "plan_details": plan.model_dump(),
        "credits": user.credits,
        "credits_used": user.credits_used,
        "credits_remaining": user.credits - user.credits_used,
        "subscription": {
            "status": sub.get("status", "none") if sub else "none",
            "next_billing_date": sub.get("next_billing_date") if sub else None,
        },
    }


@router.post("/subscription/cancel")
async def cancel_subscription(user: User = Depends(get_current_user)):
    """Cancel the user's subscription. Credits remain until period ends."""
    sub = await db.subscriptions.find_one({"user_id": user.id}, {"_id": 0})
    if not sub or sub.get("status") != "active":
        raise HTTPException(status_code=400, detail="No active subscription to cancel")

    await db.subscriptions.update_one(
        {"user_id": user.id},
        {"$set": {
            "status": "canceled",
            "canceled_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    # Downgrade at end of period (credits stay until next_billing_date)
    logger.info(f"Subscription canceled: user={user.id}")
    return {"message": "Subscription canceled. Your credits remain active until the end of the billing period."}


@router.get("/user/credits")
async def get_user_credits(user: User = Depends(get_current_user)):
    """Get current credit balance and tier info."""
    plan = SUBSCRIPTION_PLANS.get(user.plan, SUBSCRIPTION_PLANS["starter"])
    return {
        "plan": user.plan,
        "plan_name": plan.name,
        "credits_total": user.credits,
        "credits_used": user.credits_used,
        "credits_remaining": user.credits - user.credits_used,
        "tier_features": plan.features,
    }


# ==================== HELPERS ====================

async def _activate_subscription(
    user_id: str,
    plan: str,
    reference: str,
    transaction_id: str = "",
    card_token: str = None,
    demo: bool = False,
):
    """Activate a subscription: update user credits, create/update subscription record."""
    plan_data = SUBSCRIPTION_PLANS.get(plan)
    if not plan_data:
        return

    now = datetime.now(timezone.utc)
    next_billing = (now + timedelta(days=30)).isoformat()

    # Update user
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "plan": plan,
            "credits": plan_data.credits,
            "credits_used": 0,
        }}
    )

    # Upsert subscription
    await db.subscriptions.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "plan": plan,
            "status": "active",
            "payment_provider": "jenga" if not demo else "demo",
            "reference": reference,
            "card_token": card_token,
            "next_billing_date": next_billing,
            "last_payment_date": now.isoformat(),
            "updated_at": now.isoformat(),
        }},
        upsert=True,
    )

    # Record payment
    await db.payments.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "reference": reference,
        "transaction_id": transaction_id,
        "amount": plan_data.price,
        "currency": "USD",
        "type": "subscription",
        "status": "succeeded" if not demo else "demo",
        "demo": demo,
        "created_at": now.isoformat(),
    })

    logger.info(f"Subscription activated: user={user_id}, plan={plan}, demo={demo}")
