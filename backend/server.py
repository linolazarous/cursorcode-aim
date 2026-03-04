# backend/server.py

import os
import stripe
import logging
from datetime import datetime
from fastapi import FastAPI, APIRouter, Request, HTTPException, Depends
from typing import Optional

# ---------------------------------------------------
# IMPORTS: USER MODEL & AUTH DEPENDENCIES
# ---------------------------------------------------
# Make sure you have these implemented in your project
from models.user import User  # Pydantic or ODM model
from auth.dependencies import get_current_user  # returns logged-in user
from db import users_collection, webhook_events  # Motor async collections

# ---------------------------------------------------
# APP & ROUTER INITIALIZATION
# ---------------------------------------------------

app = FastAPI()
api_router = APIRouter()
logger = logging.getLogger("billing")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------
# ENV VARIABLES & STRIPE INIT
# ---------------------------------------------------

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL")

if not STRIPE_SECRET_KEY:
    raise Exception("STRIPE_SECRET_KEY not set")
if not STRIPE_WEBHOOK_SECRET:
    raise Exception("STRIPE_WEBHOOK_SECRET not set")
if not FRONTEND_URL:
    raise Exception("FRONTEND_URL not set")

stripe.api_key = STRIPE_SECRET_KEY

# ---------------------------------------------------
# PLAN CONFIGURATION
# ---------------------------------------------------

PLAN_CREDITS = {
    "starter": 50,
    "standard": 500,
    "pro": 2000,
    "premier": 10000,
    "ultra": 50000,
}

PLAN_ORDER = ["starter", "standard", "pro", "premier", "ultra"]

# ---------------------------------------------------
# CHECKOUT SESSION
# ---------------------------------------------------

@api_router.post("/subscriptions/create-checkout")
async def create_checkout_session(
    plan: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    try:
        # Fetch Stripe prices
        prices = stripe.Price.list(
            active=True,
            type="recurring",
            expand=["data.product"]
        )

        selected_price = None
        for price in prices.auto_paging_iter():
            metadata_plan = price.product.metadata.get("plan_id")
            if metadata_plan == plan:
                selected_price = price
                break

        if not selected_price:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Create Stripe customer if missing
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(email=current_user.email)
            await users_collection.update_one(
                {"_id": current_user.id},
                {"$set": {"stripe_customer_id": customer.id}}
            )
            stripe_customer_id = customer.id
        else:
            stripe_customer_id = current_user.stripe_customer_id

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": selected_price.id, "quantity": 1}],
            mode="subscription",
            success_url=f"{FRONTEND_URL}/dashboard?success=true",
            cancel_url=f"{FRONTEND_URL}/pricing?canceled=true",
        )

        return {"url": checkout_session.url}

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=500, detail="Stripe error")

# ---------------------------------------------------
# CUSTOMER PORTAL
# ---------------------------------------------------

@api_router.post("/subscriptions/portal")
async def create_customer_portal(current_user: User = Depends(get_current_user)) -> dict:
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer")

    session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/dashboard"
    )
    return {"url": session.url}

# ---------------------------------------------------
# CREDIT SYSTEM
# ---------------------------------------------------

async def deduct_credits(user_id: str, amount: int):
    user = await users_collection.find_one({"_id": user_id})
    if not user or user.get("credits", 0) < amount:
        raise HTTPException(status_code=403, detail="Insufficient credits")

    await users_collection.update_one(
        {"_id": user_id},
        {"$inc": {"credits": -amount}}
    )

async def reset_monthly_credits(user):
    plan = user.get("plan", "starter")
    credits = PLAN_CREDITS.get(plan, PLAN_CREDITS["starter"])
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"credits": credits}}
    )

# ---------------------------------------------------
# SEAT MANAGEMENT
# ---------------------------------------------------

@api_router.post("/subscriptions/update-seats")
async def update_seats(quantity: int, current_user: User = Depends(get_current_user)):
    if not current_user.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No subscription")

    subscription = stripe.Subscription.retrieve(current_user.stripe_subscription_id)
    item_id = subscription["items"]["data"][0]["id"]

    stripe.Subscription.modify(
        current_user.stripe_subscription_id,
        items=[{"id": item_id, "quantity": quantity}]
    )
    return {"message": "Seats updated"}

# ---------------------------------------------------
# WEBHOOK PROCESSING (IDEMPOTENT)
# ---------------------------------------------------

@api_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Idempotency: skip already processed events
    event_id = event["id"]
    if await webhook_events.find_one({"event_id": event_id}):
        return {"status": "already_processed"}

    await webhook_events.insert_one({"event_id": event_id, "created_at": datetime.utcnow()})
    event_type = event["type"]

    # -------------------------
    # CHECKOUT COMPLETED
    # -------------------------
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("mode") == "subscription":
            subscription_id = session["subscription"]
            subscription = stripe.Subscription.retrieve(subscription_id)
            price = subscription["items"]["data"][0]["price"]
            product = stripe.Product.retrieve(price["product"])
            plan_id = product.metadata.get("plan_id")

            await users_collection.update_one(
                {"stripe_customer_id": session["customer"]},
                {"$set": {
                    "plan": plan_id,
                    "credits": PLAN_CREDITS.get(plan_id, 50),
                    "stripe_subscription_id": subscription_id,
                    "subscription_status": subscription["status"]
                }}
            )

    # -------------------------
    # MONTHLY RENEWAL
    # -------------------------
    elif event_type == "invoice.paid":
        invoice = event["data"]["object"]
        user = await users_collection.find_one({"stripe_customer_id": invoice["customer"]})
        if user:
            await reset_monthly_credits(user)

    # -------------------------
    # PAYMENT FAILED
    # -------------------------
    elif event_type == "invoice.payment_failed":
        await users_collection.update_one(
            {"stripe_customer_id": event["data"]["object"]["customer"]},
            {"$set": {"subscription_status": "past_due"}}
        )

    # -------------------------
    # SUB CANCELLED
    # -------------------------
    elif event_type == "customer.subscription.deleted":
        await users_collection.update_one(
            {"stripe_customer_id": event["data"]["object"]["customer"]},
            {"$set": {
                "plan": "starter",
                "subscription_status": "canceled",
                "credits": PLAN_CREDITS["starter"]
            }}
        )

    return {"status": "success"}

# ---------------------------------------------------
# PLAN ENFORCEMENT
# ---------------------------------------------------

def require_plan(required_plan: str):
    async def dependency(current_user: User = Depends(get_current_user)):
        if required_plan not in PLAN_ORDER:
            raise HTTPException(status_code=400, detail="Invalid plan")
        user_plan = current_user.plan or "starter"
        if PLAN_ORDER.index(user_plan) < PLAN_ORDER.index(required_plan):
            raise HTTPException(status_code=403, detail="Upgrade required")
        return current_user
    return dependency

# ---------------------------------------------------
# ADMIN REVENUE DASHBOARD
# ---------------------------------------------------

@api_router.get("/admin/revenue")
async def revenue_dashboard():
    subscriptions = stripe.Subscription.list(limit=100)
    monthly_total = 0
    for sub in subscriptions.auto_paging_iter():
        if sub.status == "active":
            price = sub["items"]["data"][0]["price"]
            monthly_total += price["unit_amount"] / 100
    return {"estimated_monthly_revenue": monthly_total}

# ---------------------------------------------------
# REGISTER ROUTER
# ---------------------------------------------------

app.include_router(api_router, prefix="/api")
