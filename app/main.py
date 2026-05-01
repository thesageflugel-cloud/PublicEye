from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.bootstrap import init_database
from app.config import APP_NAME, SECRET_KEY, STATIC_DIR, UPLOAD_DIR
from app.routes.web import router, templates


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax", https_only=False)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.include_router(router)


def format_datetime(value):
    if not value:
        return "-"
    if isinstance(value, str):
        return value
    return value.strftime("%d %b %Y, %I:%M %p")


def format_relative_sla(value):
    if not value:
        return "-"
    remaining = value - datetime.utcnow()
    hours = int(remaining.total_seconds() // 3600)
    if hours >= 0:
        return f"{hours}h remaining"
    return f"{abs(hours)}h overdue"


templates.env.filters["datetime"] = format_datetime
templates.env.filters["sla"] = format_relative_sla
