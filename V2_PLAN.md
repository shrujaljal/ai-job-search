# Job Application Agent — V2.0 Plan

**Goal:** turn the personal V1 tool into a configurable product for a general
audience — a local, single-user app where **every part of the profile, the selection
rules, and the résumé content is editable through a proper Settings UI**, with
**optional multi-provider LLM-assisted tailoring**, wrapped in a **richer React UI**.

**Decisions locked in:**
- **Audience:** local single-user, but fully configurable (no accounts/login).
- **UI:** rebuilt as **React (front end) + FastAPI (back end)**.
- **LLM:** **multi-provider** (Claude + OpenAI…), toggleable on/off, falls back to the
  rule-based engine when off.
- **Cross-platform:** must run on **Windows, macOS, and Linux**. No Windows-only
  dependencies in the critical path (portable PDF, Python launcher).
- **Job sources:** **LinkedIn scraping** + **Paste-JD** are **both essential**.
  Indeed and Glassdoor are **dropped** (Cloudflare-blocked, unreliable).
- **Résumé template:** ship the current design as the **built-in default**, **plus**
  let users **upload their own template**.

Work happens on the `v2` branch in `../ai-job-search-v2`; V1 (`master`) is untouched.

---

## 1. Architecture at a glance

```
┌─────────────────────────┐        HTTP/JSON        ┌──────────────────────────────┐
│  React front end (SPA)  │  <------------------->   │  FastAPI back end (Python)   │
│  Vite + TS + Tailwind   │                          │  wraps all the real work     │
│  shadcn/ui + Recharts   │                          │                              │
└─────────────────────────┘                          │  • scoring engine (config)   │
                                                      │  • résumé engine (DOCX/PDF)  │
   Pages:                                             │  • LLM tailoring (providers) │
   Dashboard · Tracker ·                              │  • scrapers (Bun CLIs)       │
   Search · Paste JD · Settings                       │  • config + data store (JSON)│
                                                      └──────────────────────────────┘
```

- **Single process to run:** FastAPI serves the built React app *and* the API on one
  port. One launcher, opens the browser — same feel as V1's one-click start.
- **All V1 logic is reused**, but refactored to read from **config files** instead of
  hardcoded constants.

---

## 2. The core idea: everything becomes configuration

Today, "Shrujal" is baked into the code. In V2, all of it becomes editable data:

| Config file | What it holds | Editable in Settings via |
|-------------|---------------|--------------------------|
| `profile.json` | Identity, experiences, education, skills, projects, leadership | **Profile editor** |
| `rules.json` | Role families + keywords + priority tiers, target companies, preferred/acceptable locations, red-flag roles, seniority terms, max years, sponsorship-blocker phrases, scoring weights | **Scoring Rules editor** |
| `resume_content.json` | Per-family summaries, skill groupings, project selection, bullet library | **Résumé Content editor** |
| `settings.json` | LLM provider/keys/toggle/model, output folder, candidate name for PDF, theme, **active résumé template** | **App Settings** |
| `templates/` | The built-in default `.docx` template + any user-uploaded templates | **Templates manager** |
| `data/tracker.json`, `data/daily_plan.json` | User's live data | Tracker / Dashboard |

**Biggest refactor:** `fit.py` and `resume_engine/profile.py` currently hold constants
(target companies, role families, summaries…). These get rewritten to **load from
config**, so changing a rule is editing a form, not code.

---

## 3. Backend (FastAPI) — modules & endpoints

```
backend/
  app.py                 # FastAPI app, serves API + built React
  config.py              # load/save/validate the JSON config files
  scoring.py             # (was fit.py) reads rules.json
  tailoring.py           # orchestrates rule-based OR LLM tailoring
  resume_engine/         # (from V1) DOCX; PDF via cross-platform path
  llm/
    base.py              # TailorProvider interface
    claude_provider.py   # Anthropic
    openai_provider.py   # OpenAI
    prompts.py           # guardrailed tailoring prompt (never fabricate)
  scrapers.py            # calls the Bun LinkedIn CLI (Indeed/Glassdoor dropped)
  templates.py           # built-in default template + user-uploaded templates
  models.py              # Pydantic request/response schemas
  data/                  # user data + config (git-ignored)
```

**Representative API endpoints**

- `GET/PUT /api/profile` · `GET/PUT /api/rules` · `GET/PUT /api/resume-content`
- `GET/PUT /api/settings`
- `POST /api/search` → `{roles, location, boards, pages}` → scored jobs
- `POST /api/tailor` → `{job or pasted JD, useLLM}` → generated résumé paths
- `GET/POST/PATCH/DELETE /api/applications` → tracker CRUD
- `GET/PUT /api/plan` → today's plan
- `GET /api/dashboard` → aggregated metrics for charts

---

## 4. LLM-assisted tailoring (multi-provider)

- **Provider abstraction** (`llm/base.py`): one interface, implementations for Claude
  and OpenAI. Adding a provider later = one new file.
- **Settings:** `ai_tailoring_enabled` toggle, `provider`, `api_key`, `model`.
- **When ON:** the model receives the JD + the candidate's real profile + the honesty
  guardrails, and rewrites summary/bullets to match the JD — **constrained to only
  rephrase, reorder, and select from real experience, never invent.** Output still
  flows through the same DOCX/PDF engine so formatting is unchanged.
- **When OFF:** the current rule-based template engine (fully offline, free).
- **Keys** are stored locally in `settings.json` (plaintext on your own machine — fine
  for a local tool; documented clearly).

---

## 5. Front end (React) — pages & design system

- **Stack:** React + Vite + TypeScript · Tailwind CSS · shadcn/ui (Radix) components ·
  Recharts (charts) · TanStack Query (data) · lightweight state (Zustand/Context).
- **Design:** a proper theme (light/dark), consistent cards, spacing, and iconography —
  far beyond Streamlit's ceiling.
- **Pages:**
  - **Dashboard** — landing: metrics, pipeline chart, applications over time, Today's
    Plan, motivational strip. Now with real layout control and polish.
  - **Tracker** — sortable/filterable data grid, inline status editing, bulk actions.
  - **Search & Tailor** — role multi-select, filters, results with fit + reasons, queue,
    tailor.
  - **Paste JD** — paste text or URL → tailor.
  - **Settings** (new) — the heart of V2:
    - Profile editor (experiences, education, skills, projects, leadership)
    - Scoring Rules editor (families/keywords/tiers, companies, locations, red flags,
      years, sponsorship phrases, weights)
    - Résumé Content editor (summaries, skills groups, bullet library)
    - **Templates manager** (use the built-in default, or upload your own `.docx`
      template with placeholder tokens; preview and pick the active one)
    - LLM & API keys (provider, key, model, on/off)
    - Appearance (theme) & output folder
  - **First-run onboarding** — since it's no longer Shrujal-only: a guided wizard to
    create the initial profile (manual now; résumé-import later).

---

## 6. Phased roadmap (incremental & testable)

- **Phase 0 — Scaffolding:** repo layout, FastAPI skeleton, React skeleton, dev scripts,
  config schema + defaults, one-command dev run.
- **Phase 1 — Config-driven core:** refactor scoring + résumé engine to read from
  `rules.json` / `resume_content.json`; migrate V1 defaults into config; back-end API
  for search (LinkedIn) / score / tailor / tracker; **cross-platform PDF** (LibreOffice,
  Word fallback on Windows).
- **Phase 2 — UI parity:** rebuild Dashboard, Tracker, Search, Paste JD in React on the
  new API (match V1 functionality).
- **Phase 3 — Settings:** profile editor, rules editor, résumé-content editor,
  **templates manager (default + upload)**, appearance. This is what makes it "for
  everyone."
- **Phase 4 — LLM tailoring:** provider abstraction, Claude + OpenAI, toggle, guardrailed
  prompt, fallback to rules.
- **Phase 5 — Polish & onboarding:** theming/animations, first-run wizard, empty states,
  error handling.
- **Phase 6 — Packaging:** FastAPI serves built React; cross-platform launcher; docs.

Each phase ends with a working, runnable app and a Git checkpoint.

---

## 7. Resolved decisions & design notes

1. **Cross-platform PDF** *(resolved: cross-platform is required).* Generate PDFs via
   **LibreOffice headless** (works on Windows/macOS/Linux). On Windows, if MS Word is
   present, use it for best fidelity; otherwise fall back to LibreOffice. No hard
   dependency on `pywin32`/Word.
2. **Cross-platform launcher** *(resolved).* Ship a **Python-based runner**
   (`run.py` / `python -m …`) that starts FastAPI, serves the built React app, and
   opens the browser — works on all three OSes. Optional thin `.bat`/`.command`/`.sh`
   wrappers for double-click convenience.
3. **Job sources** *(resolved).* **LinkedIn scraping + Paste-JD are both first-class
   and required.** Indeed and Glassdoor are removed from scope. Bun (for the LinkedIn
   CLI) becomes a documented prerequisite.
4. **Custom résumé templates** *(resolved: default + upload).* Design:
   - The built-in default is a `.docx` with **placeholder tokens** (e.g.
     `{{summary}}`, `{{experience}}`, `{{skills}}`) that the engine fills.
   - Users can **upload their own `.docx`** using the same tokens; a **Templates
     manager** lists them, validates that required tokens are present, shows which are
     recognized, and lets the user pick the active template.
   - The one-page **content rules** still apply regardless of template.
   - Documented token reference so anyone can design a compatible template.
5. **API-key storage** is plaintext-on-disk — acceptable for a local single-user tool;
   clearly documented, and keys never leave the machine except to the chosen provider.

---

## 8. What carries over from V1

- The **scoring logic, résumé engine, LinkedIn scraper, sponsorship/experience
  filters** — all reused, just made config-driven.
- The **honesty guardrails** (never fabricate) — carried into both the rule-based and
  LLM paths.
- The **folder-structure output** and **DOCX+PDF** generation (PDF path made
  cross-platform).

---

*Implementation status: Phases 0-6 were completed on the `v2` branch for the
V2.0 release. This document is retained as the architecture and decision record.*
