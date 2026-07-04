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

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import scoring
import scrapers

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


# ── Search (LinkedIn) → JD parse → config-driven scoring ─────────────────────
class SearchRequest(BaseModel):
    roles: list[str]
    location: str = ""
    date_posted: str = "any"
    job_type: str = "any"
    pages: int = 1


@app.post("/api/search")
def search(req: SearchRequest) -> dict:
    if not req.roles:
        raise HTTPException(400, "Provide at least one role.")
    rules = config.load("rules")

    # 1. Scrape every role, dedupe by (title, company).
    unique: list[dict] = []
    seen: set = set()
    statuses: list[str] = []
    for role in req.roles:
        jobs, status = scrapers.search_linkedin(
            role, req.location, req.date_posted, req.job_type, req.pages)
        statuses.append(status)
        for j in jobs:
            key = (j.get("title", "").lower().strip(), j.get("company", "").lower().strip())
            if not j.get("title") or key in seen:
                continue
            seen.add(key)
            j["query"] = role
            unique.append(j)

    # 2. Fetch each JD in parallel (this is what makes scoring realistic).
    if unique:
        def _fetch(job: dict) -> None:
            job["jd_text"] = scrapers.fetch_jd(job.get("id") or job.get("url") or "")
        with ThreadPoolExecutor(max_workers=6) as ex:
            list(as_completed([ex.submit(_fetch, j) for j in unique]))

    # 3. Score on the full JD text.
    for j in unique:
        fit = scoring.score_job(j.get("title", ""), j.get("company", ""),
                                j.get("location", ""), j.get("jd_text", ""), rules)
        j.update({k: fit[k] for k in
                  ("score", "tier", "family", "reason", "blocked", "scored_on_jd")})
    unique.sort(key=lambda j: j["score"], reverse=True)

    board_status = "ok" if "ok" in statuses else (
        "blocked" if "blocked" in statuses else
        "error" if "error" in statuses else "empty")
    return {
        "jobs": unique,
        "board_status": {"LinkedIn": board_status},
        "counts": {"total": len(unique),
                   "scored_on_jd": sum(1 for j in unique if j.get("scored_on_jd")),
                   "blocked": sum(1 for j in unique if j.get("blocked"))},
    }


# ── Serve the built React app in production (if it exists) ────────────────────
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")
