"""FastAPI application and route registration for TheAppApp backend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from typing import Dict

from backend.api.routes import settings, specialists, projects, tasks, store


def create_app() -> FastAPI:
    app = FastAPI(
        title="TheAppApp Backend",
        version="0.1.0",
        description="AI Agent Orchestration Platform with Custom Specialists"
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
    app.include_router(store.router)  # The AppAppApp Store!
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

    return app


app = create_app()
