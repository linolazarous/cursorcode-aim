"""
CursorCode AI - Billing Service
Subscription plans and billing utilities.
(Payment processing handled by services/jenga.py)
"""

import os
import logging
from models.schemas import SubscriptionPlan

logger = logging.getLogger(__name__)

SUBSCRIPTION_PLANS = {
    "starter": SubscriptionPlan(
        name="Starter", price=0, credits=10,
        features=["10 AI credits/month", "1 project", "Subdomain deploy", "Community support"]
    ),
    "standard": SubscriptionPlan(
        name="Standard", price=29, credits=75,
        features=["75 AI credits/month", "Full-stack & APIs", "Native + external deploy", "Version history", "Email support"],
    ),
    "pro": SubscriptionPlan(
        name="Pro", price=59, credits=150,
        features=["150 AI credits/month", "SaaS & multi-tenant", "Advanced agents", "CI/CD integration", "Priority builds"],
    ),
    "premier": SubscriptionPlan(
        name="Premier", price=199, credits=600,
        features=["600 AI credits/month", "Large SaaS", "Multi-org support", "Advanced security scans", "Priority support"],
    ),
    "ultra": SubscriptionPlan(
        name="Ultra", price=499, credits=2000,
        features=["2,000 AI credits/month", "Unlimited projects", "Dedicated compute", "SLA guarantee", "Enterprise support"],
    )
}


# Credit costs per AI operation type
CREDIT_COSTS = {
    "chat": 1,
    "refactor": 2,
    "code_generation": 2,
    "architecture": 3,
    "code_review": 2,
    "documentation": 1,
    "simple_query": 1,
    "complex_reasoning": 3,
    "multi_agent_build": 5,
    "security_scan": 3,
    "test_generation": 2,
    "debug": 2,
    "sandbox_execution": 4,
}


def get_credit_cost(operation: str) -> int:
    """Get credit cost for an AI operation."""
    return CREDIT_COSTS.get(operation, 2)


def check_credits(user_credits: int, user_credits_used: int, operation: str) -> tuple:
    """Check if user has enough credits. Returns (has_enough, cost, remaining)."""
    cost = get_credit_cost(operation)
    remaining = user_credits - user_credits_used
    return remaining >= cost, cost, remaining
