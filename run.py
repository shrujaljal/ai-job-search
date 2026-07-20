#!/usr/bin/env python3
"""Cross-platform launcher and diagnostics for Job Application Agent V2."""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = ROOT / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
VERSION = "2.0.0"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _command(name: str) -> str | None:
    candidates = [f"{name}.cmd", f"{name}.exe", name] if os.name == "nt" else [name]
    return next((path for candidate in candidates if (path := shutil.which(candidate))), None)


def python_exe() -> str:
    return str(VENV_PY) if VENV_PY.exists() else sys.executable


def npm_exe() -> str | None:
    return _command("npm")


def _version(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        return (result.stdout or result.stderr).strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "unavailable"


def _major(version: str) -> int:
    digits = "".join(character if character.isdigit() else " " for character in version)
    try:
        return int(digits.split()[0])
    except (ValueError, IndexError):
        return 0


def _python_dependencies_ok() -> tuple[bool, str]:
    result = subprocess.run(
        [python_exe(), "-c", "import fastapi,uvicorn,docx,httpx,multipart"],
        capture_output=True, text=True,
    )
    return result.returncode == 0, (result.stderr.strip() or "installed")


def frontend_needs_build() -> bool:
    index = FRONTEND / "dist" / "index.html"
    if not index.exists():
        return True
    inputs = [path for path in FRONTEND.iterdir() if path.is_file()]
    inputs.extend((FRONTEND / "src").rglob("*"))
    inputs.extend((FRONTEND / "public").rglob("*"))
    return any(path.is_file() and path.stat().st_mtime > index.stat().st_mtime for path in inputs)


def port_available(host: str, port: int) -> bool:
    bind_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    family = socket.AF_INET6 if ":" in bind_host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.bind((bind_host, port))
        return True
    except OSError:
        return False


def collect_checks(require_node: bool = False) -> list[Check]:
    py_ok = sys.version_info >= (3, 10)
    deps_ok, deps_detail = _python_dependencies_ok()
    node = _command("node")
    npm = npm_exe()
    bun = _command("bun")
    node_version = _version([node, "--version"]) if node else "not found"
    node_ok = bool(node) and _major(node_version) >= 18
    office = _command("soffice") or _command("libreoffice")
    word = None
    if os.name == "nt" and not office:
        for candidate in (
            Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
            Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
        ):
            if candidate.exists():
                office = str(candidate)
                break
        for candidate in (
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft Office/root/Office16/WINWORD.EXE",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft Office/root/Office16/WINWORD.EXE",
        ):
            if candidate.is_file():
                word = str(candidate)
                break
    linkedin_packages = ROOT / ".agents" / "skills" / "linkedin-search" / "cli" / "node_modules"
    return [
        Check("Python 3.10+", py_ok, sys.version.split()[0]),
        Check("Virtual environment", VENV_PY.exists(), str(VENV_PY) if VENV_PY.exists() else "run: python run.py --install"),
        Check("Backend packages", deps_ok, deps_detail or "installed"),
        Check("Node.js 18+", node_ok, node_version, require_node),
        Check("npm", bool(npm), _version([npm, "--version"]) if npm else "not found", require_node),
        Check("Frontend packages", (FRONTEND / "node_modules").is_dir(), "installed" if (FRONTEND / "node_modules").is_dir() else "run: python run.py --install", require_node),
        Check("Bun / LinkedIn search", bool(bun), _version([bun, "--version"]) if bun else "optional; Paste JD still works", False),
        Check("LinkedIn packages", linkedin_packages.is_dir(), "installed" if linkedin_packages.is_dir() else "run: bun install in the LinkedIn CLI", False),
        Check("PDF converter", bool(office or word), office or word or "install LibreOffice", False),
        Check("Built web app", (FRONTEND / "dist" / "index.html").exists(), "ready" if (FRONTEND / "dist" / "index.html").exists() else "will be built", False),
    ]


def print_checks(checks: list[Check]) -> bool:
    print(f"Job Application Agent {VERSION} diagnostics\n")
    for check in checks:
        marker = "OK" if check.ok else ("ERROR" if check.required else "WARN")
        print(f"[{marker:5}] {check.name}: {check.detail}")
    return all(check.ok or not check.required for check in checks)


def install() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required.")
    if not VENV_PY.exists():
        print("Creating .venv...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    print("Installing backend packages...")
    subprocess.run([str(VENV_PY), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")], check=True)
    node = _command("node")
    node_version = _version([node, "--version"]) if node else "not found"
    npm = npm_exe()
    if not npm or _major(node_version) < 18:
        raise SystemExit(f"Node.js 18+ with npm is required (found: {node_version}).")
    print("Installing frontend packages...")
    subprocess.run([npm, "install"], cwd=str(FRONTEND), check=True)
    bun = _command("bun")
    cli = ROOT / ".agents" / "skills" / "linkedin-search" / "cli"
    if bun and cli.exists():
        print("Installing LinkedIn search packages...")
        subprocess.run([bun, "install"], cwd=str(cli), check=True)
    else:
        print("Bun not found; LinkedIn search will be unavailable until Bun is installed.")
    print("\nInstallation complete. Run: python run.py")


def build_frontend() -> None:
    npm = npm_exe()
    node = _command("node")
    node_version = _version([node, "--version"]) if node else "not found"
    if not npm or _major(node_version) < 18 or not (FRONTEND / "node_modules").is_dir():
        raise SystemExit("The web app needs a build. Install Node.js, then run: python run.py --install")
    print("Building the web app...")
    subprocess.run([npm, "run", "build"], cwd=str(FRONTEND), check=True)


def _open_later(url: str, delay: float) -> None:
    timer = threading.Timer(delay, lambda: webbrowser.open(url))
    timer.daemon = True
    timer.start()


def run_prod(host: str, port: int, no_browser: bool, skip_build: bool) -> int:
    if not skip_build and frontend_needs_build():
        build_frontend()
    if not (FRONTEND / "dist" / "index.html").exists():
        raise SystemExit("Built web app not found. Run without --skip-build first.")
    checks = collect_checks(require_node=False)
    if not print_checks(checks):
        raise SystemExit("Required dependencies are missing. Run: python run.py --install")
    if not port_available(host, port):
        raise SystemExit(f"Port {port} is already in use. Try: python run.py --port {port + 1}")
    browser_host = "localhost" if host in {"0.0.0.0", "::"} else host
    url = f"http://{browser_host}:{port}"
    print(f"\nStarting {url}  (Ctrl+C to stop)")
    if not no_browser:
        _open_later(url, 1.5)
    try:
        return subprocess.run(
            [python_exe(), "-m", "uvicorn", "main:app", "--host", host, "--port", str(port)],
            cwd=str(BACKEND),
        ).returncode
    except KeyboardInterrupt:
        return 0


def _stop(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    deadline = time.time() + 5
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=max(0.1, deadline - time.time()))
            except subprocess.TimeoutExpired:
                process.kill()


def run_dev(host: str, api_port: int, no_browser: bool) -> int:
    checks = collect_checks(require_node=True)
    if not print_checks(checks):
        raise SystemExit("Development dependencies are missing. Run: python run.py --install")
    for port in (api_port, 5173):
        if not port_available(host, port):
            raise SystemExit(f"Port {port} is already in use.")
    npm = npm_exe()
    assert npm
    print("\nDev mode: FastAPI reload + Vite. Ctrl+C stops both.")
    backend = subprocess.Popen(
        [python_exe(), "-m", "uvicorn", "main:app", "--reload", "--host", host, "--port", str(api_port)],
        cwd=str(BACKEND),
    )
    frontend_env = {**os.environ, "VITE_API_TARGET": f"http://127.0.0.1:{api_port}"}
    frontend = subprocess.Popen(
        [npm, "run", "dev", "--", "--host", host],
        cwd=str(FRONTEND), env=frontend_env,
    )
    processes = [frontend, backend]
    if not no_browser:
        _open_later("http://localhost:5173", 2.5)
    try:
        while all(process.poll() is None for process in processes):
            time.sleep(0.25)
        return next((process.returncode for process in processes if process.returncode), 0) or 0
    except KeyboardInterrupt:
        return 0
    finally:
        _stop(processes)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"Job Application Agent V2 ({VERSION})")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dev", action="store_true", help="run FastAPI reload + Vite")
    mode.add_argument("--doctor", action="store_true", help="check local prerequisites and exit")
    mode.add_argument("--install", action="store_true", help="create .venv and install dependencies")
    parser.add_argument("--host", default="127.0.0.1", help="bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="API/production port (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    parser.add_argument("--skip-build", action="store_true", help="serve the existing frontend/dist build")
    parser.add_argument("--version", action="version", version=VERSION)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.install:
        install()
        return 0
    if args.doctor:
        return 0 if print_checks(collect_checks(require_node=False)) else 1
    if args.dev:
        return run_dev(args.host, args.port, args.no_browser)
    return run_prod(args.host, args.port, args.no_browser, args.skip_build)


if __name__ == "__main__":
    raise SystemExit(main())
