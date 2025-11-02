"""FastAPI application and route registration for TheAppApp backend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from typing import Dict
import os

from backend.api.routes import settings, specialists, projects, tasks, store
from backend.api.dependencies import initialize_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:55432/theappapp")
    # Use postgresql+psycopg for psycopg3
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    print(f"🚀 Initializing database engine with URL: {database_url}")
    initialize_engine(database_url)
    print("✅ Database engine initialized successfully")
    yield
    # Shutdown (if needed)
    pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="TheAppApp Backend",
        version="0.1.0",
        description="AI Agent Orchestration Platform with Custom Specialists",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite default
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(settings.router)
    app.include_router(store.router)  # TheAppApp App Store!
    app.include_router(specialists.router)
    app.include_router(projects.router)
    app.include_router(tasks.router)

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}
    
    @app.get("/")
    def root() -> Dict[str, str]:
        return {
            "message": "TheAppApp API",
            "version": "0.1.0",
            "docs": "/docs"
        }
    
    @app.get("/debug/specialists")
    def debug_specialists():
        """Debug endpoint to check specialists in database."""
        from backend.api.dependencies import _engine
        from sqlalchemy import text
        try:
            if _engine is None:
                return {"error": "Engine not initialized"}
            with _engine.connect() as conn:
                result = conn.execute(text("SELECT id, name, display_name, required FROM specialists"))
                rows = result.fetchall()
                return {"count": len(rows), "specialists": [{"id": str(r[0]), "name": r[1], "display_name": r[2], "required": r[3]} for r in rows]}
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}

    return app


app = create_app()
