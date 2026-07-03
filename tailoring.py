"""
Resume tailoring orchestration.

For each queued job:
  1. Fetch the full JD via the board's `detail` CLI command.
  2. Detect the role family (from title + JD).
  3. Generate a role-tailored .docx via the resume engine.
  4. Save the resume + JD into the output folder structure.

NOTE: the output folder layout in `build_output_dir()` is a PLACEHOLDER.
It will be replaced once the desired folder structure is specified.
"""

import json
import re
import subprocess
from pathlib import Path

from fit import detect_family, extract_min_years, MAX_YEARS
from resume_engine import tailor_for_family, generate

ROOT = Path(__file__).parent
CLI_ROOTS = {
    "LinkedIn":  ROOT / ".agents/skills/linkedin-search/cli",
    "Indeed":    ROOT / ".agents/skills/indeed-search/cli",
    "Glassdoor": ROOT / ".agents/skills/glassdoor-search/cli",
}
TAILORED_ROOT = ROOT / "output" / "tailored"


def _slug(text: str, maxlen: int = 60) -> str:
    text = re.sub(r"[^\w\s-]", "", text or "").strip()
    text = re.sub(r"[\s]+", "_", text)
    return text[:maxlen] or "untitled"


def build_output_dir(company: str, role: str) -> Path:
    """
    PLACEHOLDER folder structure — to be replaced with the user's spec.
    Currently: output/tailored/<Company>/<Role>/
    """
    return TAILORED_ROOT / _slug(company) / _slug(role)


def fetch_jd(board: str, job_id_or_url: str, timeout: int = 30) -> str:
    """Fetch full JD description text via the board's detail command."""
    cli_dir = CLI_ROOTS.get(board)
    if not cli_dir or not job_id_or_url:
        return ""
    cmd = ["bun", "run", "src/cli.ts", "detail", str(job_id_or_url), "--format", "json"]
    try:
        result = subprocess.run(
            cmd, cwd=str(cli_dir), capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            return ""
        data = json.loads(result.stdout.strip() or "{}")
        return data.get("description") or ""
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return ""


def tailor_job(job: dict) -> dict:
    """
    Tailor a resume for one queued job.

    `job` needs: title, company, location, board, id (or url).
    Returns dict with: company, role, family, resume_path, jd_path, warnings, ok, error.
    """
    title = job.get("title", "Untitled")
    company = job.get("company", "Unknown")
    board = job.get("board", "")
    job_id = job.get("id") or job.get("url") or ""

    try:
        jd_text = fetch_jd(board, job_id)
        family, _ = detect_family(title, jd_text)

        # Early-career guard: flag roles that ask for more than the target years.
        exp_warning = ""
        min_years = extract_min_years(jd_text)
        if min_years is not None and min_years > MAX_YEARS:
            exp_warning = (f"This role asks for {min_years}+ years of experience "
                           f"(above the ~{MAX_YEARS}-year early-career target).")

        data = tailor_for_family(family)

        out_dir = build_output_dir(company, title)
        out_dir.mkdir(parents=True, exist_ok=True)

        resume_path = out_dir / f"Resume_{_slug(company)}_{_slug(title)}.docx"
        try:
            _, warnings = generate(data, str(resume_path))
        except PermissionError:
            # File likely open in Word — write a timestamped copy instead.
            import time
            resume_path = out_dir / (
                f"Resume_{_slug(company)}_{_slug(title)}_{int(time.time())}.docx")
            _, warnings = generate(data, str(resume_path))

        # Save the JD alongside for reference
        jd_path = out_dir / "job_description.txt"
        jd_header = (
            f"{title}\n{company}\n{job.get('location', '')}\n"
            f"{job.get('url', '')}\nBoard: {board}\nRole family: {family}\n"
            + "=" * 60 + "\n\n"
        )
        jd_path.write_text(jd_header + (jd_text or "(description not available)"),
                           encoding="utf-8")

        return {
            "company": company, "role": title, "family": family,
            "resume_path": str(resume_path), "jd_path": str(jd_path),
            "warnings": warnings, "exp_warning": exp_warning,
            "ok": True, "error": "",
        }
    except Exception as e:
        return {
            "company": company, "role": title, "family": "",
            "resume_path": "", "jd_path": "", "warnings": [], "exp_warning": "",
            "ok": False, "error": str(e),
        }
