from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import logging

from core.config import CORS_ORIGINS
from core.database import client

from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.projects import router as projects_router
from routes.shared import router as shared_router
from routes.ai import router as ai_router
from routes.deployments import router as deployments_router
from routes.subscriptions import router as subscriptions_router
from routes.admin import router as admin_router
from routes.templates import router as templates_router
from routes.autonomous import router as autonomous_router

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(title="CursorCode AI API", version="2.1.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Include all sub-routers into the api_router
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(projects_router)
api_router.include_router(shared_router)
api_router.include_router(ai_router)
api_router.include_router(deployments_router)
api_router.include_router(subscriptions_router)
api_router.include_router(admin_router)
api_router.include_router(templates_router)
api_router.include_router(autonomous_router)


# Health & Root
@api_router.get("/")
async def root():
    return {"message": "CursorCode AI API", "version": "2.1.0", "status": "running"}


@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# Include the api_router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    from services.storage import init_storage, is_storage_available
    if is_storage_available():
        try:
            init_storage()
            logger.info("Object storage initialized")
        except Exception as e:
            logger.error(f"Storage init failed (deployments will use simulation mode): {e}")
    logger.info("CursorCode AI v2.2 started (JengaHQ billing, real file hosting)")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
