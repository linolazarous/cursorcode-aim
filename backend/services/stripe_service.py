import os
import logging
import stripe
from models.schemas import SubscriptionPlan

logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')

SUBSCRIPTION_PLANS = {
    "starter": SubscriptionPlan(
        name="Starter", price=0, credits=10,
        features=["10 AI credits/month", "1 project", "Subdomain deploy", "Community support"]
    ),
    "standard": SubscriptionPlan(
        name="Standard", price=29, credits=75,
        features=["75 AI credits/month", "Full-stack & APIs", "Native + external deploy", "Version history", "Email support"],
        stripe_price_id=os.environ.get('STRIPE_STANDARD_PRICE_ID')
    ),
    "pro": SubscriptionPlan(
        name="Pro", price=59, credits=150,
        features=["150 AI credits/month", "SaaS & multi-tenant", "Advanced agents", "CI/CD integration", "Priority builds"],
        stripe_price_id=os.environ.get('STRIPE_PRO_PRICE_ID')
    ),
    "premier": SubscriptionPlan(
        name="Premier", price=199, credits=600,
        features=["600 AI credits/month", "Large SaaS", "Multi-org support", "Advanced security scans", "Priority support"],
        stripe_price_id=os.environ.get('STRIPE_PREMIER_PRICE_ID')
    ),
    "ultra": SubscriptionPlan(
        name="Ultra", price=499, credits=2000,
        features=["2,000 AI credits/month", "Unlimited projects", "Dedicated compute", "SLA guarantee", "Enterprise support"],
        stripe_price_id=os.environ.get('STRIPE_ULTRA_PRICE_ID')
    )
}


async def ensure_stripe_products():
    if not stripe.api_key:
        logger.warning("Stripe API key not configured")
        return
    try:
        products = stripe.Product.list(limit=10)
        existing_names = {p.name: p.id for p in products.data}
        for plan_key, plan in SUBSCRIPTION_PLANS.items():
            if plan.price == 0:
                continue
            product_name = f"CursorCode AI {plan.name}"
            if product_name not in existing_names:
                product = stripe.Product.create(
                    name=product_name,
                    description=f"{plan.credits} AI credits/month - " + ", ".join(plan.features[:2]),
                    metadata={"plan": plan_key}
                )
                product_id = product.id
            else:
                product_id = existing_names[product_name]
            prices = stripe.Price.list(product=product_id, active=True, limit=1)
            if not prices.data:
                price = stripe.Price.create(
                    product=product_id, unit_amount=plan.price * 100, currency="usd",
                    recurring={"interval": "month"}, metadata={"plan": plan_key}
                )
                SUBSCRIPTION_PLANS[plan_key].stripe_price_id = price.id
                SUBSCRIPTION_PLANS[plan_key].stripe_product_id = product_id
            else:
                SUBSCRIPTION_PLANS[plan_key].stripe_price_id = prices.data[0].id
                SUBSCRIPTION_PLANS[plan_key].stripe_product_id = product_id
        logger.info("Stripe products initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Stripe: {e}")
