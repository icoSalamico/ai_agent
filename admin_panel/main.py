from fastapi import FastAPI
from sqladmin import Admin
from starlette.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import create_async_engine
from admin import setup_admin
import sqladmin
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL)

app = FastAPI()

# Serve SQLAdmin statics
app.mount(
    "/admin/statics",
    StaticFiles(directory=os.path.join(os.path.dirname(sqladmin.__file__), "statics")),
    name="admin-statics",
)

setup_admin(app, engine)
