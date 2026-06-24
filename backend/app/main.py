"""
app/main.py — FastAPI application entry point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.db.database import engine, Base
from app.api.routes import dashboard_router, ticket_router, team_router, ai_router
from app.api.connector import connector_router
from app.api.import_tickets import import_router
from app.api.ai_enhanced import ai_enhanced_router
from app.api.auth import auth_router


settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)


# ── Startup / Shutdown ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting ServiceDesk HQ — %s", settings.environment)

    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables verified")

    # Seed data if empty
    from app.db.init_db import seed_if_empty
    seed_if_empty()
    logger.info("✅ Database seeded")

    # Warm up AI models
    from app.ai.routing_agent import get_routing_model
    from app.ai.sla_predictor import get_sla_predictor
    from app.ai.rag_pipeline import get_kb_embeddings
    get_routing_model()
    get_sla_predictor()
    get_kb_embeddings()
    logger.info("✅ AI models ready")

    yield

    logger.info("ServiceDesk HQ shutting down.")


# ── App ───────────────────────────────────────────────────
app = FastAPI(
    title="ServiceDesk HQ API",
    description="AI-powered service desk leadership dashboard API — Project ATLAS",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(ticket_router)
app.include_router(team_router)
app.include_router(ai_router)
app.include_router(connector_router)
app.include_router(import_router)
app.include_router(ai_enhanced_router)
# ── Serve frontend static files ───────────────────────────
import os
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ── Health check ──────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }


@app.get("/api", tags=["Health"])
def api_root():
    return {
        "message": "ServiceDesk HQ API",
        "docs": "/docs",
        "endpoints": ["/api/dashboard/summary", "/api/tickets", "/api/teams", "/api/ai/chat"]
    }
