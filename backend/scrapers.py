"""
Job scraping via the Bun LinkedIn CLI.

V2 supports LinkedIn only (Indeed/Glassdoor were Cloudflare-blocked and dropped).
Paste-JD covers everything else. Requires Bun on PATH and the CLI's deps installed
(`bun install` in .agents/skills/linkedin-search/cli).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINKEDIN_CLI = ROOT / ".agents/skills/linkedin-search/cli"


def _run_cli(args: list[str], timeout: int = 45) -> tuple[str, str, int]:
    try:
        r = subprocess.run(
            ["bun", "run", "src/cli.ts", *args],
            cwd=str(LINKEDIN_CLI), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        return r.stdout, r.stderr, r.returncode
    except FileNotFoundError:
        return "", "bun not found on PATH", 127
    except subprocess.TimeoutExpired:
        return "", "timed out", 124


def _is_blocked(text: str) -> bool:
    t = text.lower()
    return any(s in t for s in ("403", "401", "cloudflare", "access denied",
                                "blocking this request"))


def search_linkedin(query: str, location: str = "", date_posted: str = "any",
                    job_type: str = "any", pages: int = 1) -> tuple[list[dict], str]:
    """
    Search LinkedIn across N pages. Returns (jobs, status) where status is one of
    'ok', 'blocked', 'empty', 'error'. Each job is tagged with board='LinkedIn'.
    """
    jobs: list[dict] = []
    status = "empty"
    for page in range(1, pages + 1):
        args = ["search", "--query", query, "--format", "json", "--page", str(page)]
        if location:
            args += ["--location", location]
        if date_posted and date_posted != "any":
            args += ["--datePosted", date_posted]
        if job_type and job_type != "any":
            args += ["--jobType", job_type]
        out, err, code = _run_cli(args)
        if code != 0:
            status = "blocked" if _is_blocked(err + out) else "error"
            break
        raw = out.strip()
        if not raw:
            break
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            status = "error"
            break
        results = data.get("results") if isinstance(data, dict) else data
        if not results:
            break
        for j in results:
            j["board"] = "LinkedIn"
        jobs += results
        status = "ok"
    return jobs, status


def fetch_jd(job_id_or_url: str, timeout: int = 30) -> str:
    """Fetch the full JD description text for a LinkedIn job (id or URL)."""
    if not job_id_or_url:
        return ""
    out, _err, code = _run_cli(["detail", str(job_id_or_url), "--format", "json"],
                               timeout=timeout)
    if code != 0:
        return ""
    try:
        return json.loads(out.strip() or "{}").get("description") or ""
    except json.JSONDecodeError:
        return ""
