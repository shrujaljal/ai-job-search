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

import shutil
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import re

import config
import scoring
import scrapers
import store
import resume_render
import tailoring
import templates as template_store
from llm import ProviderError, create_provider

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


@app.post("/api/llm/test")
def test_llm_connection() -> dict:
    llm_settings = config.load("settings").get("llm", {})
    try:
        provider = create_provider(llm_settings)
        raw = provider.complete_json(
            "Return JSON only.",
            'Return exactly {"ok": true}.',
        )
        parsed = tailoring.parse_provider_json(raw)
        if parsed.get("ok") is not True:
            raise ProviderError("Provider returned an unexpected test response.")
        return {"ok": True, "provider": provider.name, "model": provider.model}
    except (ProviderError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


# ── Resume templates ────────────────────────────────────────────────────────
class ActiveTemplateRequest(BaseModel):
    id: str


@app.get("/api/templates")
def list_templates() -> dict:
    settings = config.load("settings")
    active = settings.get("active_template", template_store.DEFAULT_TEMPLATE_ID)
    return {
        "active_template": active,
        "required_tokens": sorted(template_store.REQUIRED_TOKENS),
        "known_tokens": sorted(template_store.KNOWN_TOKENS),
        "templates": template_store.list_templates(active),
    }


@app.post("/api/templates")
def upload_template(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "Upload a .docx template.")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        shutil.copyfileobj(file.file, tmp)
    try:
        try:
            item = template_store.save_upload(file.filename, tmp_path)
        except Exception as e:
            raise HTTPException(400, f"Template could not be read: {e}") from e
        return item
    finally:
        tmp_path.unlink(missing_ok=True)


@app.put("/api/templates/active")
def set_active_template(req: ActiveTemplateRequest) -> dict:
    template_id = req.id or template_store.DEFAULT_TEMPLATE_ID
    if template_id != template_store.DEFAULT_TEMPLATE_ID:
        path = template_store.resolve_template(template_id)
        if not path or not path.exists():
            raise HTTPException(404, "Template not found.")
        info = template_store.validate_template(path)
        if not info["valid"]:
            missing = ", ".join(info["missing_tokens"])
            raise HTTPException(400, f"Template is missing required tokens: {missing}")

    settings = config.load("settings")
    settings["active_template"] = template_id
    config.save("settings", settings)
    return {"active_template": template_id}


@app.delete("/api/templates/{template_id}")
def delete_template(template_id: str) -> dict:
    try:
        template_store.delete_template(template_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(404, "Template not found.") from e

    settings = config.load("settings")
    if settings.get("active_template") == template_id:
        settings["active_template"] = template_store.DEFAULT_TEMPLATE_ID
        config.save("settings", settings)
    return {"deleted": True}


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


# ── Tailor a résumé (from a job or pasted JD) ────────────────────────────────
_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe(name: str, maxlen: int = 120) -> str:
    name = _INVALID.sub("", name or "").strip()
    name = re.sub(r"\s+", " ", name).rstrip(". ")
    return name[:maxlen].strip() or "Untitled"


def _output_root() -> Path:
    settings = config.load("settings")
    custom = (settings.get("output_dir") or "").strip()
    return Path(custom) if custom else (Path.home() / "JobApplications")


class TailorRequest(BaseModel):
    company: str
    role: str
    jd_text: str = ""
    job_id: str = ""       # LinkedIn id/url to fetch the JD if jd_text is empty
    location: str = ""
    enforce_sponsorship: bool = False
    use_llm: bool | None = None


@app.post("/api/tailor")
def tailor(req: TailorRequest) -> dict:
    if not req.company.strip() or not req.role.strip():
        raise HTTPException(400, "Company and role are required.")
    rules = config.load("rules")
    profile = config.load("profile")
    content = config.load("resume_content")
    settings = config.load("settings")

    jd_text = req.jd_text or (scrapers.fetch_jd(req.job_id) if req.job_id else "")

    blocked, sp_matched = scoring.analyze_sponsorship(jd_text, rules)
    if blocked and req.enforce_sponsorship:
        return {"ok": True, "blocked": True, "company": req.company, "role": req.role,
                "block_reason": ", ".join(sp_matched)}

    family, _ = scoring.detect_family(req.role, jd_text, rules)
    ctx, tailoring_meta = tailoring.build_tailored_context(
        profile=profile,
        content=content,
        family=family,
        jd_text=jd_text,
        role=req.role,
        company=req.company,
        settings=settings,
        use_llm=req.use_llm,
    )

    out_dir = _output_root() / _safe(req.company) / _safe(req.role)
    out_dir.mkdir(parents=True, exist_ok=True)
    role_name = _safe(req.role)
    candidate = (profile.get("identity", {}).get("name")
                 or settings.get("candidate_name") or "Resume")
    docx_path = out_dir / f"{role_name}.docx"
    pdf_path = out_dir / f"{_safe(candidate)}.pdf"

    template_path = template_store.resolve_template(settings.get("active_template"))
    resume_render.render_docx(ctx, str(docx_path), template_path=template_path)
    pdf_error = ""
    try:
        resume_render.docx_to_pdf(docx_path, pdf_path)
    except Exception as e:  # PDF is best-effort (needs LibreOffice / Word)
        pdf_error = str(e)
        pdf_path = None

    exp_warning = ""
    max_years = int(rules.get("max_years_experience", 4))
    my = scoring.extract_min_years(jd_text)
    if my is not None and my > max_years:
        exp_warning = f"This role asks for {my}+ years of experience."

    return {
        "ok": True, "blocked": False, "company": req.company, "role": req.role,
        "family": family, "out_dir": str(out_dir),
        "docx_path": str(docx_path), "pdf_path": str(pdf_path) if pdf_path else "",
        "warnings": ctx.get("warnings", []),
        "sponsorship_warning": (", ".join(sp_matched) if blocked else ""),
        "exp_warning": exp_warning, "pdf_error": pdf_error,
        **tailoring_meta,
    }


# ── Tracker ──────────────────────────────────────────────────────────────────
class NewApplication(BaseModel):
    company: str
    role: str
    location: str = ""
    url: str = ""
    status: str = "To Apply"
    notes: str = ""


@app.get("/api/applications")
def get_applications() -> list[dict]:
    return store.list_applications()


@app.post("/api/applications")
def create_application(app_in: NewApplication) -> dict:
    row = store.add_application(**app_in.model_dump())
    if row is None:
        raise HTTPException(409, "That company + role is already tracked.")
    return row


@app.patch("/api/applications/{app_id}")
def patch_application(app_id: int, fields: dict) -> dict:
    if not store.update_application(app_id, fields):
        raise HTTPException(404, "Application not found.")
    return {"updated": True}


@app.delete("/api/applications/{app_id}")
def remove_application(app_id: int) -> dict:
    if not store.delete_application(app_id):
        raise HTTPException(404, "Application not found.")
    return {"deleted": True}


# ── Daily plan + dashboard ───────────────────────────────────────────────────
@app.get("/api/plan")
def get_plan() -> dict:
    return store.get_plan()


@app.put("/api/plan")
def put_plan(body: dict) -> dict:
    store.save_plan(body)
    return {"saved": True}


@app.get("/api/dashboard")
def get_dashboard() -> dict:
    return store.dashboard()


# ── Download a generated résumé file (restricted to the output root) ─────────
@app.get("/api/download")
def download(path: str):
    p = Path(path).resolve()
    root = _output_root().resolve()
    if p != root and root not in p.parents:
        raise HTTPException(403, "File is outside the output directory.")
    if not p.exists() or not p.is_file():
        raise HTTPException(404, "File not found.")
    return FileResponse(str(p), filename=p.name)


# ── Serve the built React app in production (if it exists) ────────────────────
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")
