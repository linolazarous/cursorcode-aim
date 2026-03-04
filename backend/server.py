# backend/server.py

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
import stripe
import uuid
import asyncio

# -------------------------------
# CONFIG & INIT
# -------------------------------

logger = logging.getLogger("billing")
logging.basicConfig(level=logging.INFO)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_yourkey")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_yoursecret")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

stripe.api_key = STRIPE_SECRET_KEY

client = AsyncIOMotorClient(MONGO_URI)
db = client["appdb"]
users_collection = db["users"]
webhook_events = db["webhook_events"]

app = FastAPI()
api_router = APIRouter()

PLAN_CREDITS = {"starter": 50, "standard": 500, "pro": 2000, "premier": 10000, "ultra": 50000}
PLAN_ORDER = ["starter", "standard", "pro", "premier", "ultra"]

# -------------------------------
# USER MODEL
# -------------------------------

class User(BaseModel):
    id: str
    email: EmailStr
    plan: str = "starter"
    credits: int = 0
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    badges: List[str] = []
    leaderboard_points: int = 0
    last_credit_reset: Optional[datetime] = None
    plan_suggestion: Optional[str] = None

async def get_current_user() -> User:
    test_email = "user@example.com"
    user_data = await users_collection.find_one({"email": test_email})
    if not user_data:
        user_data = {
            "_id": str(uuid.uuid4()),
            "email": test_email,
            "plan": "starter",
            "credits": PLAN_CREDITS["starter"],
            "badges": [],
            "leaderboard_points": 0,
            "last_credit_reset": datetime.utcnow(),
            "plan_suggestion": None
        }
        await users_collection.insert_one(user_data)
    return User(**user_data)

# -------------------------------
# CREDIT MANAGEMENT
# -------------------------------

async def deduct_credits(user_id: str, amount: int):
    user = await users_collection.find_one({"_id": user_id})
    if not user or user.get("credits", 0) < amount:
        raise HTTPException(status_code=403, detail="Insufficient credits")

    new_points = user.get("leaderboard_points", 0) + amount
    badges = user.get("badges", [])
    if new_points > 1000 and "Power User" not in badges:
        badges.append("Power User")

    await users_collection.update_one(
        {"_id": user_id},
        {"$inc": {"credits": -amount, "leaderboard_points": amount}, "$set": {"badges": badges}}
    )

    # Check AI upgrade suggestion
    await evaluate_plan_suggestion(user_id)

async def reset_monthly_credits(user: User):
    credits = PLAN_CREDITS.get(user.plan, PLAN_CREDITS["starter"])
    await users_collection.update_one({"_id": user.id}, {"$set": {"credits": credits, "last_credit_reset": datetime.utcnow()}})
    # Evaluate AI suggestion monthly
    await evaluate_plan_suggestion(user.id)

# -------------------------------
# AI PLAN SUGGESTIONS
# -------------------------------

async def evaluate_plan_suggestion(user_id: str):
    user = await users_collection.find_one({"_id": user_id})
    if not user:
        return

    plan = user.get("plan", "starter")
    max_credits = PLAN_CREDITS.get(plan, 50)
    used = max_credits - user.get("credits", 0)
    used_ratio = used / max_credits if max_credits > 0 else 0

    suggestion = None

    # Suggest upgrade if >80% used
    if used_ratio > 0.8 and PLAN_ORDER.index(plan) < len(PLAN_ORDER) - 1:
        suggestion = PLAN_ORDER[PLAN_ORDER.index(plan) + 1]
    # Suggest downgrade if <20% used and not starter
    elif used_ratio < 0.2 and PLAN_ORDER.index(plan) > 0:
        suggestion = PLAN_ORDER[PLAN_ORDER.index(plan) - 1]

    await users_collection.update_one({"_id": user_id}, {"$set": {"plan_suggestion": suggestion}})

# -------------------------------
# PLAN ENFORCEMENT
# -------------------------------

def require_plan(required_plan: str):
    async def dependency(current_user: User = Depends(get_current_user)):
        if required_plan not in PLAN_ORDER:
            raise HTTPException(status_code=400, detail="Invalid plan")
        if PLAN_ORDER.index(current_user.plan) < PLAN_ORDER.index(required_plan):
            raise HTTPException(status_code=403, detail="Upgrade required")
        return current_user
    return dependency

# -------------------------------
# STRIPE CHECKOUT SESSION
# -------------------------------

@api_router.post("/subscriptions/create-checkout")
async def create_checkout_session(plan: str, current_user: User = Depends(get_current_user)):
    prices = stripe.Price.list(active=True, type="recurring", expand=["data.product"])
    selected_price = None
    for price in prices.auto_paging_iter():
        if price.product.metadata.get("plan_id") == plan:
            selected_price = price
            break
    if not selected_price:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not current_user.stripe_customer_id:
        customer = stripe.Customer.create(email=current_user.email)
        await users_collection.update_one({"_id": current_user.id}, {"$set": {"stripe_customer_id": customer.id}})
        stripe_customer_id = customer.id
    else:
        stripe_customer_id = current_user.stripe_customer_id
    session = stripe.checkout.Session.create(
        customer=stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{"price": selected_price.id, "quantity": 1}],
        mode="subscription",
        success_url=f"{FRONTEND_URL}/dashboard?success=true",
        cancel_url=f"{FRONTEND_URL}/pricing?canceled=true"
    )
    return {"url": session.url}

# -------------------------------
# CUSTOMER PORTAL
# -------------------------------

@api_router.post("/subscriptions/portal")
async def create_customer_portal(current_user: User = Depends(get_current_user)):
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer")
    session = stripe.billing_portal.Session.create(customer=current_user.stripe_customer_id, return_url=f"{FRONTEND_URL}/dashboard")
    return {"url": session.url}

# -------------------------------
# SEAT MANAGEMENT
# -------------------------------

@api_router.post("/subscriptions/update-seats")
async def update_seats(quantity: int, current_user: User = Depends(get_current_user)):
    if not current_user.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No subscription")
    subscription = stripe.Subscription.retrieve(current_user.stripe_subscription_id)
    item_id = subscription["items"]["data"][0]["id"]
    stripe.Subscription.modify(current_user.stripe_subscription_id, items=[{"id": item_id, "quantity": quantity}])
    return {"message": "Seats updated"}

# -------------------------------
# STRIPE WEBHOOK
# -------------------------------

@api_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    if await webhook_events.find_one({"event_id": event["id"]}):
        return {"status": "already_processed"}
    await webhook_events.insert_one({"event_id": event["id"], "created_at": datetime.utcnow()})
    obj = event["data"]["object"]

    # Checkout completed
    if event["type"] == "checkout.session.completed" and obj.get("subscription"):
        sub_id = obj["subscription"]
        subscription = stripe.Subscription.retrieve(sub_id)
        product = stripe.Product.retrieve(subscription["items"]["data"][0]["price"]["product"])
        plan_id = product.metadata.get("plan_id", "starter")
        await users_collection.update_one({"stripe_customer_id": obj["customer"]},
                                         {"$set": {"plan": plan_id, "credits": PLAN_CREDITS[plan_id],
                                                   "stripe_subscription_id": sub_id,
                                                   "subscription_status": subscription["status"]}})
        await evaluate_plan_suggestion(obj["customer"])

    # Monthly reset
    elif event["type"] == "invoice.paid":
        user = await users_collection.find_one({"stripe_customer_id": obj["customer"]})
        if user:
            await reset_monthly_credits(User(**user))

    # Payment failed
    elif event["type"] == "invoice.payment_failed":
        await users_collection.update_one({"stripe_customer_id": obj["customer"]}, {"$set": {"subscription_status": "past_due"}})

    # Subscription deleted
    elif event["type"] == "customer.subscription.deleted":
        await users_collection.update_one({"stripe_customer_id": obj["customer"]},
                                          {"$set": {"plan": "starter", "credits": PLAN_CREDITS["starter"], "subscription_status": "canceled"}})
    return {"status": "success"}

# -------------------------------
# REAL-TIME ANALYTICS
# -------------------------------

@api_router.get("/admin/analytics")
async def analytics_dashboard():
    active_users = await users_collection.count_documents({"stripe_subscription_id": {"$ne": None}})
    top_users = await users_collection.find().sort("leaderboard_points", -1).to_list(length=10)
    plan_suggestions = await users_collection.find({"plan_suggestion": {"$ne": None}}).to_list(length=100)
    return {
        "active_users": active_users,
        "total_users": await users_collection.count_documents({}),
        "top_users": [{"email": u["email"], "points": u["leaderboard_points"]} for u in top_users],
        "plan_suggestions": [{"email": u["email"], "suggested_plan": u["plan_suggestion"]} for u in plan_suggestions]
    }

# -------------------------------
# ADMIN REVENUE
# -------------------------------

@api_router.get("/admin/revenue")
async def revenue_dashboard():
    subscriptions = stripe.Subscription.list(limit=100)
    total = sum(sub["items"]["data"][0]["price"]["unit_amount"] / 100
                for sub in subscriptions.auto_paging_iter() if sub.status == "active")
    return {"estimated_monthly_revenue": total}

# -------------------------------
# REGISTER ROUTER
# -------------------------------

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
