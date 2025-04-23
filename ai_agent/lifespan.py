from contextlib import asynccontextmanager
from database import init_db

@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield