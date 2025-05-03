from contextlib import asynccontextmanager

from fastapi.templating import Jinja2Templates
from dependencies.security import verify_admin_key
from fastapi import FastAPI, Request, Depends, Response
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import os
import json
import logging
import sqladmin

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import init_db, SessionLocal, get_db
from database.core import engine
from ai_agent.routes import company_register
from ai_agent.routes.webhook import webhook_router
from ai_agent import adm
from ai_agent.adm import setup_admin
from ai_agent.routes import prompt_test
from ai_agent.routes import dashboard


from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DEBUG mode
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# ✅ Static files with CSP headers
class CSPStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' data: https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob:;"
        )
        return response

def get_base_url():
    return os.getenv("RAILWAY_PUBLIC_DOMAIN", "aiagent-production-a50f.up.railway.app")

sqladmin.helpers.get_static_url_path = lambda name: f"{get_base_url()}/admin/statics/{name}"

# Middleware para headers seguros
class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SecureHeadersMiddleware)

# Rotas e módulos
app.include_router(prompt_test.router)
app.include_router(webhook_router)
app.include_router(company_register.router)
app.include_router(dashboard.admin_router)

# Admin com CSP
app.mount(
    "/admin/statics",
    CSPStaticFiles(directory=os.path.join(os.path.dirname(sqladmin.__file__), "statics")),
    name="admin-statics",
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Painel administrativo
setup_admin(app, engine)

# Rate limiting handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

# Rota principal
@app.get("/")
def home():
    return {"message": "WhatsApp AI Agent is running!"}

# Ping para verificar conexão com o banco
@app.get("/ping-db", dependencies=[Depends(verify_admin_key)])
async def ping_db(session: AsyncSession = Depends(get_db)):
    try:
        await session.execute(text("SELECT 1"))
        logger.info("✅ DB connection OK")
        return {"db": "ok"}
    except Exception as e:
        logger.error("❌ DB error: %s", e)
        return {"db": "error", "detail": str(e)}

# Health check
@app.get("/health")
def health():
    return {"status": "ok"}
