from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

@debug_router.get("/debug/register-company")
async def debug_register_form(request: Request):
    return templates.TemplateResponse("register_company.html", {
        "request": request,
        "key": "test-debug-key"
    })
