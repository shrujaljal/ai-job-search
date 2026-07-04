"""
V2 back end — FastAPI.

Phase 0: a runnable skeleton that
  • ensures the config store exists,
  • exposes a health check,
  • exposes generic read/write/reset for the config documents,
  • serves the built React app in production (frontend/dist), if present.

Later phases add: /api/search, /api/tailor, /api/applications, /api/plan,
/api/dashboard, /api/templates, and the LLM providers.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config

app = FastAPI(title="Job Application Agent API", version="2.0.0-dev")

# In dev the React app runs on its own port (Vite, 5173); allow it to call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:8000", "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    config.ensure_config()


# ── Health ───────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


# ── Config read / write / reset ──────────────────────────────────────────────
@app.get("/api/config/{name}")
def get_config(name: str) -> dict:
    if name not in config.CONFIG_NAMES:
        raise HTTPException(404, f"Unknown config '{name}'")
    return config.load(name)


@app.put("/api/config/{name}")
def put_config(name: str, body: dict) -> dict:
    if name not in config.CONFIG_NAMES:
        raise HTTPException(404, f"Unknown config '{name}'")
    config.save(name, body)
    return {"saved": True, "name": name}


@app.post("/api/config/{name}/reset")
def reset_config(name: str) -> dict:
    if name not in config.CONFIG_NAMES:
        raise HTTPException(404, f"Unknown config '{name}'")
    return config.reset(name)


# ── Serve the built React app in production (if it exists) ────────────────────
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")
