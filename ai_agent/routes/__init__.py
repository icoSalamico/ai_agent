from fastapi import APIRouter
from app.routes.webhook import webhook_router
from app.routes.health import health_router
from app.routes.db import db_router

router = APIRouter()
router.include_router(webhook_router)
router.include_router(health_router)
router.include_router(db_router)