from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from database.models import Company
from sqlalchemy import select
from database import get_db
import os

router = APIRouter()
templates = Jinja2Templates(directory="ai_agent/templates")
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.get("/admin/prompt-test-tool", response_class=HTMLResponse)
@router.post("/admin/prompt-test-tool", response_class=HTMLResponse)
async def prompt_test_tool(
    request: Request,
    db: AsyncSession = Depends(get_db),
    company_id: int = Form(None),
    message: str = Form(None),
):
    companies_result = await db.execute(select(Company))
    companies = companies_result.scalars().all()
    ai_response = ""

    if request.method == "POST" and company_id and message:
        company = await db.get(Company, int(company_id))
        if company:
            system_prompt = company.ai_prompt or "You are a helpful assistant."
            completion = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
            )
            ai_response = completion.choices[0].message.content

    return templates.TemplateResponse(
        "prompt_test.html",
        {
            "request": request,
            "companies": companies,
            "selected_company_id": company_id,
            "message": message,
            "ai_response": ai_response,
        },
    )
