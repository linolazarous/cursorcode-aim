"""
CursorCode AI - Stripe Payments
"""

import stripe
from fastapi import HTTPException
from backend.db_models import Users
import os

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL")
stripe.api_key = STRIPE_SECRET_KEY

def create_checkout_session(user_email: str):
    if not user_email:
        raise HTTPException(401, "Unauthorized")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": "CursorCode AI Pro"},
                "unit_amount": 2000,
            },
            "quantity": 1,
        }],
        success_url=f"{FRONTEND_URL}/success",
        cancel_url=f"{FRONTEND_URL}/cancel",
        metadata={"user_email": user_email}
    )

    return session.url
