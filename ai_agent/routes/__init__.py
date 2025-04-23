from fastapi import APIRouter
from ai_agent.routes.webhook import webhook_router
from ai_agent.routes.health import health_router
from ai_agent.routes.db import db_router

router = APIRouter()
router.include_router(webhook_router)
router.include_router(health_router)
router.include_router(db_router)