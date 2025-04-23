from fastapi import FastAPI
from ai_agent.lifespan import lifespan
from ai_agent.routes import router

app = FastAPI(lifespan=lifespan)
app.include_router(router)