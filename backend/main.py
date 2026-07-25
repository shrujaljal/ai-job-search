"""
V2 back end — FastAPI.

Phase 0: a runnable skeleton that
  • ensures the config store exists,
  • exposes a health check,
  • exposes generic read/write/reset for the config documents,
  • serves the built React app in production (frontend/dist), if present.

Later phases add: /api/search, /api/tailor, /api/applications, /api/plan,
/api/dashboard, profile imports, and the LLM providers.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
from pathlib import Path

import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field as PydanticField

import re

import config
import company_jobs
import profile_import
import scoring
import scrapers
import store
import resume_render
import tailoring
from llm import ProviderError, create_provider

app = FastAPI(title="Job Application Agent API", version="2.0.0")

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
    config.initialize_accounts()


# ── Health ───────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


# Accounts are isolated local job profiles, not remote authentication users.
class AccountCreate(BaseModel):
    name: str


class AccountActivate(BaseModel):
    account_id: str


@app.get("/api/accounts")
def get_accounts() -> dict:
    return config.accounts()


@app.post("/api/accounts")
def post_account(req: AccountCreate) -> dict:
    try:
        account = config.create_account(req.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"account": account, "active_id": account["id"]}


@app.put("/api/accounts/active")
def put_active_account(req: AccountActivate) -> dict:
    try:
        account = config.activate_account(req.account_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"account": account, "active_id": account["id"]}


@app.patch("/api/accounts/{account_id}")
def patch_account(account_id: str, req: AccountCreate) -> dict:
    try:
        return config.rename_account(account_id, req.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


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
    if name == "profile":
        body = profile_import.clean_profile(body)
    config.save(name, body)
    return {"saved": True, "name": name}


@app.post("/api/config/{name}/reset")
def reset_config(name: str) -> dict:
    if name not in config.CONFIG_NAMES:
        raise HTTPException(404, f"Unknown config '{name}'")
    return config.reset(name)


# Profile sources
MAX_PROFILE_FILES = 10
MAX_PROFILE_FILE_BYTES = 10 * 1024 * 1024


@app.post("/api/profile/import")
async def import_profile(files: list[UploadFile] = File(...)) -> dict:
    if not files or len(files) > MAX_PROFILE_FILES:
        raise HTTPException(400, f"Upload between 1 and {MAX_PROFILE_FILES} files.")

    parsed_documents = []
    pending_sources: list[tuple[Path, str, dict]] = []
    with tempfile.TemporaryDirectory(prefix="profile-import-") as temp_dir:
        temp_root = Path(temp_dir)
        for index, upload in enumerate(files):
            original_name = Path(upload.filename or f"profile-{index + 1}.md").name
            suffix = Path(original_name).suffix.lower()
            if suffix not in profile_import.SUPPORTED_SUFFIXES:
                raise HTTPException(400, f"{original_name}: use a DOCX, PDF, MD, or Markdown file.")
            contents = await upload.read(MAX_PROFILE_FILE_BYTES + 1)
            if len(contents) > MAX_PROFILE_FILE_BYTES:
                raise HTTPException(400, f"{original_name}: file exceeds the 10 MB limit.")
            path = temp_root / f"{index}{suffix}"
            path.write_bytes(contents)
            try:
                parsed = profile_import.parse_resume(
                    profile_import.extract_lines(path), original_name
                )
            except (ValueError, OSError) as exc:
                raise HTTPException(400, f"Could not import {original_name}: {exc}") from exc
            parsed_documents.append(parsed)
            pending_sources.append((path, original_name, parsed))

        for path, original_name, parsed in pending_sources:
            stored_name = profile_import.save_source(path, original_name)
            parsed["resume_blueprint"]["source_files"] = [stored_name]

        profile, stats = profile_import.merge_profile(
            config.load("profile"), parsed_documents
        )
        config.save("profile", profile)

    settings = config.load("settings")
    imported_name = profile.get("identity", {}).get("name", "")
    if imported_name and settings.get("candidate_name", "") in {"", "Your Name"}:
        settings["candidate_name"] = imported_name
        config.save("settings", settings)

    return {
        "profile": profile,
        "stats": stats,
        "sources": profile.get("resume_blueprint", {}).get("source_files", []),
    }


@app.get("/api/profile/enrichment-prompt")
def get_profile_enrichment_prompt() -> dict:
    prompt = profile_import.enrichment_prompt(config.load("profile"))
    return {"prompt": prompt, "filename": "profile-enrichment.md"}


@app.post("/api/profile/rebuild")
def rebuild_profile() -> dict:
    current = config.load("profile")
    backup_dir = config.DATA_DIR / "profile_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_name = f"profile-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    (backup_dir / backup_name).write_text(
        json.dumps(current, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    try:
        profile, stats = profile_import.rebuild_from_sources(current)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc
    config.save("profile", profile)
    return {
        "profile": profile,
        "stats": stats,
        "sources": profile.get("resume_blueprint", {}).get("source_files", []),
        "backup": backup_name,
    }


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


# ── First-run onboarding ────────────────────────────────────────────────────
class OnboardingRequest(BaseModel):
    full_name: str
    display_name: str = ""
    location: str = ""
    work_authorization: str = ""
    needs_sponsorship: bool = False
    target_roles: list[str]
    preferred_locations: list[str] = PydanticField(default_factory=list)
    max_years_experience: int = 4
    output_dir: str = ""
    ai_enabled: bool = False
    ai_provider: str = "openrouter"
    ai_model: str = ""
    ai_api_key: str = ""


def _profile_is_configured(profile: dict) -> bool:
    name = str(profile.get("identity", {}).get("name", "")).strip().lower()
    return bool(name and name not in {"your name", "name"})


def _clean_target_roles(values: list[str]) -> list[str]:
    roles: list[str] = []
    seen: set[str] = set()
    for value in values:
        role = re.sub(r"\s+", " ", value).strip()
        key = role.casefold()
        if role and key not in seen:
            seen.add(key)
            roles.append(role)
    return roles


def _role_keywords(role: str) -> list[str]:
    base = role.casefold()
    variants = [base]
    if "&" in base:
        variants.append(re.sub(r"\s*&\s*", " and ", base))
    if " and " in base:
        variants.append(base.replace(" and ", " & "))
    if "/" in base:
        variants.append(re.sub(r"\s*/\s*", " ", base))
    return list(dict.fromkeys(re.sub(r"\s+", " ", value).strip() for value in variants))


@app.get("/api/onboarding")
def onboarding_status() -> dict:
    settings = config.load("settings")
    profile = config.load("profile")
    explicit = settings.get("onboarding_complete")
    complete = bool(explicit) if explicit is not None else _profile_is_configured(profile)
    rules = config.load("rules")
    identity = profile.get("identity", {})
    llm = settings.get("llm", {})
    provider = llm.get("provider", "openrouter")
    model_fields = {
        "claude": "model",
        "openai": "openai_model",
        "openrouter": "openrouter_model",
        "groq": "groq_model",
        "ollama": "ollama_model",
    }
    return {
        "complete": complete,
        "can_cancel": config.can_cancel_account_setup(),
        "legacy_inferred": explicit is None and complete,
        "role_families": [
            {"name": family.get("name", ""), "tier": family.get("tier", 3)}
            for family in rules.get("role_families", []) if family.get("name")
        ],
        "defaults": {
            "full_name": identity.get("name", "") if _profile_is_configured(profile) else "",
            "display_name": settings.get("username", ""),
            "location": identity.get("location", ""),
            "work_authorization": identity.get("work_authorization", ""),
            "needs_sponsorship": bool(identity.get("needs_sponsorship")),
            "target_roles": [
                family.get("name") for family in rules.get("role_families", [])
                if family.get("name") and int(family.get("tier", 3)) == 1
            ],
            "preferred_locations": rules.get("preferred_locations", []),
            "max_years_experience": rules.get("max_years_experience", 4),
            "output_dir": settings.get("output_dir", ""),
            "ai_enabled": bool(llm.get("enabled")),
            "ai_provider": provider,
            "ai_model": llm.get(model_fields.get(provider, "openrouter_model"), ""),
            "ai_api_key": "",
        },
    }


@app.post("/api/onboarding")
def complete_onboarding(req: OnboardingRequest) -> dict:
    name = req.full_name.strip()
    selected_roles = _clean_target_roles(req.target_roles)
    if not name:
        raise HTTPException(400, "Full name is required.")
    if not selected_roles:
        raise HTTPException(400, "Add at least one target role.")
    if len(selected_roles) > 20:
        raise HTTPException(400, "Add no more than 20 target roles.")
    if any(len(role) > 100 for role in selected_roles):
        raise HTTPException(400, "Target role names must be 100 characters or fewer.")
    if not 0 <= req.max_years_experience <= 30:
        raise HTTPException(400, "Maximum years of experience must be between 0 and 30.")
    if req.ai_provider not in {"claude", "openai", "openrouter", "groq", "ollama"}:
        raise HTTPException(400, "Choose a supported AI provider.")

    profile = config.load("profile")
    identity = profile.setdefault("identity", {})
    identity.update({
        "name": name,
        "location": req.location.strip(),
        "work_authorization": req.work_authorization.strip(),
        "needs_sponsorship": req.needs_sponsorship,
    })

    rules = config.load("rules")
    families = rules.setdefault("role_families", [])
    known_roles = {
        str(family.get("name", "")).casefold(): family
        for family in families if family.get("name")
    }
    selected_names: set[str] = set()
    for role in selected_roles:
        family = known_roles.get(role.casefold())
        if family is None:
            family = {"name": role, "tier": 1, "keywords": _role_keywords(role)}
            families.append(family)
            known_roles[role.casefold()] = family
        selected_names.add(family["name"])
    for family in families:
        if family.get("name") in selected_names:
            family["tier"] = 1
        elif int(family.get("tier", 3)) == 1:
            family["tier"] = 2
    rules["preferred_locations"] = list(dict.fromkeys(
        location.strip().lower() for location in req.preferred_locations if location.strip()))
    rules["max_years_experience"] = req.max_years_experience

    settings = config.load("settings")
    settings.update({
        "candidate_name": name,
        "username": req.display_name.strip() or name.split()[0],
        "output_dir": req.output_dir.strip(),
        "onboarding_complete": True,
    })
    llm = settings.setdefault("llm", {})
    llm["enabled"] = req.ai_enabled
    llm["provider"] = req.ai_provider
    model_fields = {
        "claude": ("model", "claude-sonnet-5"),
        "openai": ("openai_model", "gpt-4o"),
        "openrouter": ("openrouter_model", "openrouter/free"),
        "groq": ("groq_model", "openai/gpt-oss-20b"),
        "ollama": ("ollama_model", "gpt-oss:20b"),
    }
    model_field, default_model = model_fields[req.ai_provider]
    llm[model_field] = req.ai_model.strip() or llm.get(model_field, default_model)
    if req.ai_api_key:
        llm.setdefault("api_keys", {})[req.ai_provider] = req.ai_api_key.strip()

    config.save("profile", profile)
    config.save("rules", rules)
    config.save("settings", settings)
    config.finish_account_setup()
    return {"complete": True}


@app.post("/api/onboarding/cancel")
def cancel_onboarding() -> dict:
    try:
        account = config.cancel_account_setup()
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"cancelled": True, "active_id": account["id"]}


@app.post("/api/onboarding/reset")
def reset_onboarding() -> dict:
    config.finish_account_setup()
    settings = config.load("settings")
    settings["onboarding_complete"] = False
    config.save("settings", settings)
    return {"complete": False}


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


# ── Target-company career search ─────────────────────────────────────────────
class CompanySource(BaseModel):
    name: str
    url: str
    enabled: bool = True


class TargetCompanySearchRequest(BaseModel):
    sites: list[CompanySource]
    recent_days: int = PydanticField(default=14, ge=1, le=90)
    minimum_fit_score: int = PydanticField(default=0, ge=0, le=100)


@app.post("/api/target-company-jobs/search")
def search_target_company_jobs(req: TargetCompanySearchRequest) -> dict:
    sources = [source.model_dump() for source in req.sites if source.enabled]
    if not sources:
        raise HTTPException(400, "Add at least one enabled company career site.")

    config.save("target_companies", {
        "sites": [source.model_dump() for source in req.sites],
        "recent_days": req.recent_days,
        "minimum_fit_score": req.minimum_fit_score,
    })
    jobs: list[dict] = []
    errors: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(6, len(sources))) as executor:
        futures = {executor.submit(company_jobs.fetch_source, source): source for source in sources}
        for future in as_completed(futures):
            source = futures[future]
            try:
                jobs.extend(company_jobs.filter_recent(future.result(), req.recent_days))
            except Exception as exc:
                errors.append({"name": source["name"], "message": str(exc)})

    rules = config.load("rules")
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict] = []
    for job in jobs:
        if not job.get("title"):
            continue
        key = (
            company_jobs.normalize_url(job.get("url", "")),
            job.get("company", "").lower().strip(),
            job.get("title", "").lower().strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        fit = scoring.score_job(
            job.get("title", ""), job.get("company", ""),
            job.get("location", ""), job.get("jd_text", ""), rules,
        )
        job.update({name: fit[name] for name in
                    ("score", "tier", "family", "reason", "blocked", "scored_on_jd")})
        if job["score"] >= req.minimum_fit_score:
            unique.append(job)

    company_jobs.annotate_tracker(unique, store.list_applications())

    def _posted_timestamp(job: dict) -> float:
        try:
            return datetime.fromisoformat(
                job.get("posted_at", "").replace("Z", "+00:00")
            ).timestamp()
        except (ValueError, AttributeError):
            return 0

    unique.sort(key=lambda job: (
        bool(job.get("already_applied")),
        -job.get("score", 0),
        -_posted_timestamp(job),
    ))
    return {
        "jobs": unique,
        "errors": errors,
        "counts": {
            "total": len(unique),
            "applied": sum(1 for job in unique if job.get("already_applied")),
            "tracked": sum(1 for job in unique if job.get("tracked")),
            "sources": len(sources),
        },
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
    if custom:
        return Path(custom)
    root = Path.home() / "JobApplications"
    account_id = config.active_account_id()
    return root if account_id == "default" else root / account_id


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

    resume_render.render_docx(ctx, str(docx_path))
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
