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

from fit import (detect_family, extract_min_years, MAX_YEARS,
                 analyze_sponsorship)
from resume_engine import tailor_for_family, generate

ROOT = Path(__file__).parent
CLI_ROOTS = {
    "LinkedIn":  ROOT / ".agents/skills/linkedin-search/cli",
    "Indeed":    ROOT / ".agents/skills/indeed-search/cli",
    "Glassdoor": ROOT / ".agents/skills/glassdoor-search/cli",
}

# Tailored resumes are written here as: <Company>/<Role>/<Role>.docx + "Shrujal Agarwal.pdf"
TAILORED_ROOT = Path(r"C:\Users\shruj\Downloads\2026")
CANDIDATE_NAME = "Shrujal Agarwal"

# Characters not allowed in Windows file/folder names (spaces & commas are fine).
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe(name: str, maxlen: int = 120) -> str:
    """Sanitize a company/role into a valid Windows file/folder name, keeping it readable."""
    name = _INVALID_CHARS.sub("", name or "").strip()
    name = re.sub(r"\s+", " ", name)          # collapse whitespace
    name = name.rstrip(". ")                    # Windows dislikes trailing dot/space
    return name[:maxlen].strip() or "Untitled"


def _slug(text: str, maxlen: int = 60) -> str:
    text = re.sub(r"[^\w\s-]", "", text or "").strip()
    text = re.sub(r"[\s]+", "_", text)
    return text[:maxlen] or "untitled"


def build_output_dir(company: str, role: str) -> Path:
    """<Downloads>/2026/<Company>/<Role>/"""
    return TAILORED_ROOT / _safe(company) / _safe(role)


def docx_to_pdf(docx_path: Path, pdf_path: Path) -> None:
    """
    Convert a .docx to .pdf using Microsoft Word (exact visual fidelity).
    Safe to call from a Streamlit worker thread (initializes COM for the thread).
    """
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(docx_path), ReadOnly=1)
        doc.SaveAs(str(pdf_path), FileFormat=17)  # 17 = wdFormatPDF
    finally:
        if doc is not None:
            doc.Close(False)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()


def fetch_jd(board: str, job_id_or_url: str, timeout: int = 30) -> str:
    """Fetch full JD description text via the board's detail command."""
    cli_dir = CLI_ROOTS.get(board)
    if not cli_dir or not job_id_or_url:
        return ""
    cmd = ["bun", "run", "src/cli.ts", "detail", str(job_id_or_url), "--format", "json"]
    try:
        result = subprocess.run(
            cmd, cwd=str(cli_dir), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout
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
        # Reuse the JD fetched during search if present; otherwise fetch now.
        jd_text = job.get("jd_text") or fetch_jd(board, job_id)

        # Sponsorship guard: F1 student needs sponsorship — skip roles that
        # block it (no sponsorship / citizenship / ITAR / clearance).
        blocked, sp_matched = analyze_sponsorship(jd_text)
        if blocked:
            return {
                "company": company, "role": title, "family": "",
                "resume_path": "", "pdf_path": "", "jd_path": "", "out_dir": "",
                "warnings": [], "exp_warning": "", "pdf_error": "",
                "blocked": True,
                "block_reason": ", ".join(sp_matched),
                "ok": True, "error": "",
            }

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

        # DOCX named after the role.
        role_name = _safe(title)
        resume_path = out_dir / f"{role_name}.docx"
        try:
            _, warnings = generate(data, str(resume_path))
        except PermissionError:
            import time
            resume_path = out_dir / f"{role_name}_{int(time.time())}.docx"
            _, warnings = generate(data, str(resume_path))

        # PDF named after the candidate.
        pdf_path = out_dir / f"{CANDIDATE_NAME}.pdf"
        pdf_error = ""
        try:
            docx_to_pdf(resume_path, pdf_path)
        except Exception as e:
            pdf_error = f"PDF conversion failed: {e}"
            pdf_path = None

        # Save the JD alongside for reference.
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
            "resume_path": str(resume_path),
            "pdf_path": str(pdf_path) if pdf_path else "",
            "jd_path": str(jd_path), "out_dir": str(out_dir),
            "warnings": warnings, "exp_warning": exp_warning,
            "pdf_error": pdf_error, "blocked": False, "ok": True, "error": "",
        }
    except Exception as e:
        return {
            "company": company, "role": title, "family": "",
            "resume_path": "", "pdf_path": "", "jd_path": "", "out_dir": "",
            "warnings": [], "exp_warning": "", "pdf_error": "",
            "blocked": False, "ok": False, "error": str(e),
        }
