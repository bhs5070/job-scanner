"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routers.auth import router as auth_router
from src.api.routers.chat import router as chat_router
from src.api.routers.profile import router as profile_router

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"

app = FastAPI(
    title="Job Scanner",
    description="AI 채용 분석 에이전트 API",
    version="0.1.0",
)

# CORS for frontend (dev: localhost only)
# allow_origins=["*"] + allow_credentials=True is an invalid combination per CORS spec
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

# API routes
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(profile_router)

# Serve frontend static files
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
