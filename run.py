#!/usr/bin/env python3
"""
Cross-platform runner for the Job Application Agent (V2).

    python run.py          # production mode: build the UI (if needed) and serve
                           # everything from the backend on http://localhost:8000
    python run.py --dev    # dev mode: FastAPI (reload) + Vite dev server, with
                           # hot-reload, on http://localhost:5173

Works on Windows, macOS, and Linux. Uses the project's .venv Python if present.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def python_exe() -> str:
    return str(VENV_PY) if VENV_PY.exists() else sys.executable


def npm_exe() -> str:
    npm = shutil.which("npm")
    if not npm:
        sys.exit("npm not found on PATH. Install Node.js (https://nodejs.org).")
    return npm


def build_frontend() -> None:
    print("Building the front end…")
    subprocess.run([npm_exe(), "run", "build"], cwd=str(FRONTEND), check=True)


def run_prod() -> None:
    if not (FRONTEND / "dist").exists():
        build_frontend()
    url = "http://localhost:8000"
    print(f"Starting on {url}  (Ctrl+C to stop)")
    threading.Timer(2.0, lambda: webbrowser.open(url)).start()
    subprocess.run([python_exe(), "-m", "uvicorn", "main:app", "--port", "8000"],
                   cwd=str(BACKEND))


def run_dev() -> None:
    print("Dev mode: FastAPI (reload) + Vite. Ctrl+C to stop both.")
    backend = subprocess.Popen(
        [python_exe(), "-m", "uvicorn", "main:app", "--reload", "--port", "8000"],
        cwd=str(BACKEND))
    frontend = subprocess.Popen([npm_exe(), "run", "dev"], cwd=str(FRONTEND))
    threading.Timer(3.5, lambda: webbrowser.open("http://localhost:5173")).start()
    try:
        backend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in (frontend, backend):
            p.terminate()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run the Job Application Agent (V2).")
    ap.add_argument("--dev", action="store_true", help="dev mode with hot-reload")
    args = ap.parse_args()
    run_dev() if args.dev else run_prod()
