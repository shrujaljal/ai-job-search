# Job Application Agent V2 Setup

## Prerequisites

### Required for first installation

- Python 3.10 or newer
- Node.js 18 or newer, including npm

### Optional capabilities

- Bun: required for LinkedIn search; Paste JD works without it
- LibreOffice: recommended for DOCX-to-PDF conversion on every platform
- Microsoft Word: supported as the PDF fallback on Windows
- Claude or OpenAI API key: only required when AI-assisted tailoring is enabled

Verify the required runtimes:

```bash
python --version
node --version
npm --version
```

## Platform Launchers

### Windows

Double-click `Job Application Agent.bat`. For a desktop shortcut and explicit
setup output, run:

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

### macOS

On first use, macOS may require permission to execute the launcher:

```bash
chmod +x "Job Application Agent.command"
./"Job Application Agent.command"
```

### Linux

```bash
chmod +x job-application-agent.sh
./job-application-agent.sh
```

All launchers create `.venv`, install dependencies when needed, build the React
app when source files are newer than the current build, start FastAPI, and open
the browser.

## Manual Installation

From the repository root:

```bash
python run.py --install
```

This performs:

1. Creates `.venv` with the current Python interpreter.
2. Installs `backend/requirements.txt` into `.venv`.
3. Runs `npm install` in `frontend/`.
4. Runs `bun install` for the LinkedIn CLI when Bun is available.

Then run diagnostics and start production mode:

```bash
# Windows
.venv\Scripts\python run.py --doctor
.venv\Scripts\python run.py

# macOS/Linux
.venv/bin/python run.py --doctor
.venv/bin/python run.py
```

The app opens at [http://localhost:8000](http://localhost:8000).

## Development Mode

```bash
.venv/bin/python run.py --dev
```

On Windows, use `.venv\Scripts\python run.py --dev`. FastAPI runs on port 8000
with reload enabled and Vite runs on port 5173 with API proxying.

## Runner Options

```text
--doctor       print dependency and capability diagnostics
--install      create .venv and install all available dependencies
--dev          run FastAPI and Vite development servers
--host HOST    bind address; default 127.0.0.1
--port PORT    production/API port; default 8000
--no-browser   do not open a browser automatically
--skip-build   serve the existing frontend/dist build
--version      print the application version
```

Production rebuilds `frontend/dist` only when frontend source or package files
are newer. A current prebuilt `dist` can be served without Node.js by using
`--skip-build`.

## Local Data and Security

Runtime data is stored under `backend/data/` and excluded from Git. This includes
profile facts, scoring rules, tracker data, uploaded templates, and plaintext API
keys. Set `JOB_AGENT_DATA_DIR` before launch to use another directory.

The server binds to `127.0.0.1` by default. Binding to `0.0.0.0` exposes the app to
the local network and should only be done on a trusted network.

## Troubleshooting

### Diagnose the installation

```bash
.venv/bin/python run.py --doctor
```

The report distinguishes required failures from optional capabilities.

### Port 8000 is already in use

```bash
.venv/bin/python run.py --port 8010
```

### Frontend dependencies or build are missing

Install Node.js 18+, then run:

```bash
python run.py --install
```

On Windows, the runner selects `npm.cmd` directly and does not depend on the
PowerShell script execution policy.

### LinkedIn search reports an error

Install Bun, then rerun `python run.py --install`. Confirm that `--doctor` reports
both Bun and LinkedIn packages as available. Paste JD remains usable without Bun.

### PDF was not created

The DOCX remains available. Install LibreOffice and ensure `soffice` is on PATH.
On Windows, a local Microsoft Word installation can be used instead.

### Backend offline or setup cannot load

Keep the launcher terminal open and read the startup error. Run `--doctor`, then
confirm the selected port is not occupied. The UI provides a retry action after
the backend becomes available.

### Force a clean frontend rebuild

Delete `frontend/dist` and run the launcher again, or run:

```bash
cd frontend
npm run build
```
