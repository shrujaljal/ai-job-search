# Job Application Agent — V2.0

V2 is a cross-platform rewrite: **React front end + FastAPI back end**, with
everything (profile, scoring rules, résumé content, settings) editable through a
Settings UI, and optional multi-provider LLM-assisted tailoring. See
[V2_PLAN.md](V2_PLAN.md) for the full plan and roadmap.

> V1 (the Streamlit app) lives on the `master` branch and is unaffected.

## Status

**Phases 0-6: complete.** React + FastAPI are wired together, the core app pages
are live, Settings edits all profile and tailoring configuration, optional
Claude/OpenAI-assisted resume tailoring runs behind factual guardrails, and new
installations open with a guided setup flow, and cross-platform launchers provide
installation diagnostics, production builds, and one-command startup.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (front end)
- **Bun** (optional; required for LinkedIn search)
- **LibreOffice** (recommended for cross-platform PDF; Word also works on Windows)

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

- `profile.json` — identity, resume sources, section order/headings, experience,
  education, skills, projects, leadership, honors, and custom sections
- `rules.json` — scoring rules (role families, target companies, locations, red flags,
  seniority, years cap, sponsorship blockers, weights)
- `resume_content.json` — per-family summaries, skills, projects, bullet library
- `settings.json` — LLM provider/keys/toggle, theme, and output folder

The API exposes these at `GET/PUT /api/config/{name}` and
`POST /api/config/{name}/reset`.

## Profile sources and resume structure

Settings -> Profile accepts up to ten `.docx`, `.pdf`, `.md`, or `.markdown`
files at once. The first uploaded resume supplies the section order and headings;
later files add facts and sections. Imported sources are stored locally under
`backend/data/profile_sources/` and are never committed.

The importer allocates identity, experience, education, skills, projects,
leadership, honors, and unknown custom sections into the profile. It merges bullet
libraries within the matching experience or section and removes exact and close
duplicates. The Profile editor lets users revise the imported facts, headings,
and section order.

The uploaded file is a content and structure blueprint. DOCX, PDF, and Markdown
do not provide a common safe way to reproduce arbitrary visual styling, so the
renderer uses the app's stable built-in typography while following the imported
heading names and section order.

Use **Download AI prompts** in Profile to create a Markdown file containing one
factual bullet-expansion prompt per experience. Run those prompts in a preferred
chatbot, save its Markdown response, and import that file back into Profile. New
unique bullets are merged into the appropriate experience.

## AI-assisted tailoring

Enable AI under Settings -> AI & Providers, choose Claude or OpenAI, save the
provider key and model, then use Test connection. Keys stay in the local
`backend/data/settings.json` file and requests go only to the selected provider.

AI output must cite source bullets and exact profile evidence. Unsupported
skills, source references, or quantified claims are rejected. If a provider is
unavailable or its response fails validation, resume generation continues with
the offline rule-based engine and the result displays the fallback reason.

## First-run setup

Fresh installations open a four-step setup flow for identity and work
authorization, target role families and locations, generated-file output, and
optional AI configuration. Existing configured V2 profiles are detected and are
not forced through setup. Run the wizard again from Settings -> Account without
deleting current values.

For isolated testing or portable deployments, set `JOB_AGENT_DATA_DIR` to use a
configuration directory other than `backend/data/`.
