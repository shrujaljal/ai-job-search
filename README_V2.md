# Job Application Agent — V2 (in development)

V2 is a cross-platform rewrite: **React front end + FastAPI back end**, with
everything (profile, scoring rules, résumé content, settings) editable through a
Settings UI, and optional multi-provider LLM-assisted tailoring. See
[V2_PLAN.md](V2_PLAN.md) for the full plan and roadmap.

> V1 (the Streamlit app) lives on the `master` branch and is unaffected.

## Status

**Phases 0-3: complete.** React + FastAPI are wired together, the core app pages
are live, and Settings now edits profile, scoring rules, resume content,
appearance, AI settings, and resume templates.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (front end)
- **Bun** (LinkedIn scraper) — added in a later phase
- **LibreOffice** (cross-platform PDF) — added in a later phase

## First-time setup

```bash
# from the project root (ai-job-search-v2)
python -m venv .venv
# Windows:  .venv\Scripts\python -m pip install -r backend/requirements.txt
# macOS/Linux:  .venv/bin/python -m pip install -r backend/requirements.txt

cd frontend && npm install && cd ..
```

## Running

```bash
python run.py --dev     # hot-reload dev: FastAPI + Vite, opens http://localhost:5173
python run.py           # production: builds the UI and serves it at http://localhost:8000
```

## Layout

```
backend/
  main.py            # FastAPI app (health + config endpoints; serves the built UI)
  config.py          # load/save/reset the JSON config store (atomic writes)
  defaults/          # shipped defaults: profile, rules, resume_content, settings
  data/              # user's live config + data (git-ignored, created on first run)
  requirements.txt
frontend/
  src/               # React app (Vite + TypeScript + Tailwind)
run.py               # cross-platform runner
V2_PLAN.md           # the full V2 plan
```

## Configuration

Everything the app uses is JSON in `backend/data/` (copied from `backend/defaults/`
on first run):

- `profile.json` — your identity, experience, education, skills, projects, leadership
- `rules.json` — scoring rules (role families, target companies, locations, red flags,
  seniority, years cap, sponsorship blockers, weights)
- `resume_content.json` — per-family summaries, skills, projects, bullet library
- `settings.json` — LLM provider/keys/toggle, theme, output folder, active template

The API exposes these at `GET/PUT /api/config/{name}` and
`POST /api/config/{name}/reset`.

## Resume templates

Settings -> Templates lets you use the built-in default resume design or upload a
custom `.docx` file. Uploaded templates are stored locally in `backend/data/`
and are never committed.

Custom templates use placeholder tokens. Required tokens:

- `{{summary}}`
- `{{experience}}`
- `{{education}}`
- `{{skills}}`

Optional tokens:

- `{{name}}`, `{{contact}}`, `{{location}}`, `{{phone}}`, `{{email}}`, `{{links}}`
- `{{coursework}}`, `{{projects}}`, `{{leadership}}`, `{{family}}`
