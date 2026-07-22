# Job Application Agent V2

A local, configurable job-search application that scores LinkedIn roles, tailors
one-page resumes, and tracks applications. The V2 interface is React and the local
API is FastAPI; no account or hosted service is required.

## Features

- Dashboard, daily plan, pipeline metrics, and application tracker
- LinkedIn search with configurable fit scoring and sponsorship checks
- Paste-JD workflow for roles found anywhere
- DOCX and PDF resume generation from an uploaded resume blueprint
- Fully editable profile, scoring rules, resume content, and appearance
- Optional Claude or OpenAI tailoring with source-evidence guardrails
- First-run setup wizard and automatic offline fallback

Profile, tracker, generated files, and API keys remain on the local machine. When
AI tailoring is enabled, the job description and candidate facts required for
tailoring are sent to the selected provider; contact details are excluded.

## Quick Start

Install Python 3.10+ and Node.js 18+, then use the launcher for your platform:

- **Windows:** double-click `Job Application Agent.bat`
- **macOS:** double-click `Job Application Agent.command`
- **Linux:** run `./job-application-agent.sh`

The first launch creates `.venv`, installs dependencies, builds the web app, and
opens [http://localhost:8000](http://localhost:8000). Bun is optional but required
for LinkedIn search. LibreOffice is recommended for PDF output; Microsoft Word is
also supported on Windows.

Manual setup and troubleshooting are documented in [SETUP.md](SETUP.md).

## Runner

```bash
python run.py --install             # install backend/frontend dependencies
.venv/bin/python run.py --doctor    # Windows: .venv\Scripts\python run.py --doctor
.venv/bin/python run.py             # production build + local server
.venv/bin/python run.py --dev       # FastAPI reload + Vite
```

Useful options: `--port 8010`, `--host 0.0.0.0`, `--no-browser`, and
`--skip-build`.

## Project Layout

```text
backend/          FastAPI API, scoring, tailoring, rendering, local data
frontend/         React + TypeScript web app
run.py            cross-platform installer, diagnostics, and launcher
backend/data/     live local configuration (created at runtime, git-ignored)
```

See [README_V2.md](README_V2.md) for profile imports, configuration, AI behavior,
and onboarding details. V1 remains available on the `master` branch.

## Release

V2.0 implements roadmap Phases 0-6. See [V2_PLAN.md](V2_PLAN.md) for the original
architecture and phase definitions.
