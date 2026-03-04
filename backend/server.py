import stripe
import os
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, Depends
from pymongo import ReturnDocument

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL")

PLAN_CREDITS = {
    "starter": 50,
    "standard": 500,
    "pro": 2000,
    "premier": 10000,
    "ultra": 50000
}

@api_router.post("/subscriptions/create-checkout")
async def create_checkout_session(
    plan: str,
    current_user: User = Depends(get_current_user)
):
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

    checkout_session = stripe.checkout.Session.create(
        customer_email=current_user.email,
        payment_method_types=["card"],
        line_items=[{
            "price": selected_price.id,
            "quantity": 1,
        }],
        mode="subscription",
        success_url=f"{FRONTEND_URL}/dashboard?success=true",
        cancel_url=f"{FRONTEND_URL}/pricing?canceled=true",
    )

    return {"url": checkout_session.url}

@api_router.post("/subscriptions/portal")
async def create_customer_portal(current_user: User = Depends(get_current_user)):
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer")

    session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/dashboard",
    )

    return {"url": session.url}

async def deduct_credits(user_id: str, amount: int):
    user = await users_collection.find_one({"_id": user_id})

    if user["credits"] < amount:
        raise HTTPException(status_code=403, detail="Not enough credits")

    await users_collection.update_one(
        {"_id": user_id},
        {"$inc": {"credits": -amount}}
    )

async def reset_monthly_credits(user):
    plan = user.get("plan", "starter")
    new_credits = PLAN_CREDITS.get(plan, 50)

    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"credits": new_credits}}
    )

@api_router.post("/subscriptions/update-seats")
async def update_seats(quantity: int, current_user: User = Depends(get_current_user)):
    stripe.Subscription.modify(
        current_user.stripe_subscription_id,
        items=[{
            "id": current_user.stripe_item_id,
            "quantity": quantity,
        }]
    )

    return {"message": "Seats updated"}

@api_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook")

    event_type = event["type"]

    # -----------------------------
    # CHECKOUT COMPLETED
    # -----------------------------
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]

        if session["mode"] == "subscription":
            subscription_id = session["subscription"]
            customer_email = session["customer_email"]

            subscription = stripe.Subscription.retrieve(subscription_id)
            price = subscription["items"]["data"][0]["price"]
            product = stripe.Product.retrieve(price["product"])

            plan_id = product.metadata.get("plan_id")

            await users_collection.update_one(
                {"email": customer_email},
                {
                    "$set": {
                        "plan": plan_id,
                        "credits": PLAN_CREDITS.get(plan_id, 50),
                        "stripe_subscription_id": subscription_id,
                        "stripe_customer_id": session["customer"],
                        "subscription_status": subscription["status"]
                    }
                }
            )

    # -----------------------------
    # INVOICE PAID (Monthly Reset)
    # -----------------------------
    elif event_type == "invoice.paid":
        invoice = event["data"]["object"]
        customer_id = invoice["customer"]

        user = await users_collection.find_one(
            {"stripe_customer_id": customer_id}
        )

        if user:
            await reset_monthly_credits(user)

    # -----------------------------
    # PAYMENT FAILED
    # -----------------------------
    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]

        await users_collection.update_one(
            {"stripe_customer_id": invoice["customer"]},
            {"$set": {"subscription_status": "past_due"}}
        )

    # -----------------------------
    # SUB CANCELLED
    # -----------------------------
    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]

        await users_collection.update_one(
            {"stripe_customer_id": subscription["customer"]},
            {
                "$set": {
                    "plan": "starter",
                    "subscription_status": "canceled",
                    "credits": PLAN_CREDITS["starter"]
                }
            }
        )

    return {"status": "success"}

def require_plan(required_plan: str):
    async def dependency(current_user: User = Depends(get_current_user)):
        user_plan = current_user.plan

        plan_levels = ["starter", "standard", "pro", "premier", "ultra"]

        if plan_levels.index(user_plan) < plan_levels.index(required_plan):
            raise HTTPException(status_code=403, detail="Upgrade required")

        return current_user

    return dependency

@api_router.get("/admin/revenue")
async def revenue_dashboard():
    subscriptions = stripe.Subscription.list(limit=100)

    total = 0
    for sub in subscriptions.auto_paging_iter():
        if sub.status == "active":
            total += sub["items"]["data"][0]["price"]["unit_amount"] / 100

    return {"monthly_revenue_estimate": total}

