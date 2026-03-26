import logging
import stripe as stripe_lib
from models.schemas import SUBSCRIPTION_PLANS
from core.config import STRIPE_SECRET_KEY

stripe_lib.api_key = STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


async def ensure_stripe_products():
    if not stripe_lib.api_key:
        logger.warning("Stripe API key not configured")
        return
    try:
        products = stripe_lib.Product.list(limit=10)
        existing_names = {p.name: p.id for p in products.data}
        for plan_key, plan in SUBSCRIPTION_PLANS.items():
            if plan.price == 0:
                continue
            product_name = f"CursorCode AI {plan.name}"
            if product_name not in existing_names:
                product = stripe_lib.Product.create(
                    name=product_name,
                    description=f"{plan.credits} AI credits/month - " + ", ".join(plan.features[:2]),
                    metadata={"plan": plan_key}
                )
                product_id = product.id
            else:
                product_id = existing_names[product_name]
            prices = stripe_lib.Price.list(product=product_id, active=True, limit=1)
            if not prices.data:
                price = stripe_lib.Price.create(
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
