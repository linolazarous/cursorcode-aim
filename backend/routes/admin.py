import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends

from core.database import db
from core.security import get_admin_user
from models.schemas import User
from services.stripe_service import SUBSCRIPTION_PLANS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def get_admin_stats(user: User = Depends(get_admin_user)):
    total_users = await db.users.count_documents({})
    total_projects = await db.projects.count_documents({})
    total_generations = await db.credit_usage.count_documents({})
    total_deployments = await db.deployments.count_documents({})
    pipeline = [{"$group": {"_id": "$plan", "count": {"$sum": 1}}}]
    plan_counts = await db.users.aggregate(pipeline).to_list(None)
    plan_distribution = {item["_id"]: item["count"] for item in plan_counts if item["_id"]}
    for plan in SUBSCRIPTION_PLANS.keys():
        if plan not in plan_distribution:
            plan_distribution[plan] = 0
    revenue = sum(SUBSCRIPTION_PLANS[plan].price * count for plan, count in plan_distribution.items())
    from ai_metrics import get_platform_stats
    ai_stats = get_platform_stats()
    return {
        "total_users": total_users, "total_projects": total_projects,
        "total_generations": total_generations, "total_deployments": total_deployments,
        "plan_distribution": plan_distribution, "monthly_revenue": revenue,
        "ai_metrics": ai_stats
    }


@router.get("/users")
async def get_admin_users(user: User = Depends(get_admin_user), limit: int = 50, skip: int = 0):
    users = await db.users.find(
        {}, {"_id": 0, "password_hash": 0, "github_access_token": 0, "verification_token": 0}
    ).skip(skip).limit(limit).to_list(limit)
    return {"users": users, "total": await db.users.count_documents({})}


@router.get("/usage")
async def get_admin_usage(user: User = Depends(get_admin_user), days: int = 30):
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    usage = await db.credit_usage.find(
        {"created_at": {"$gte": start_date.isoformat()}}, {"_id": 0}
    ).to_list(1000)
    return {"usage": usage}
