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
from resume_engine import tailor_for_job, generate

ROOT = Path(__file__).parent
CLI_ROOTS = {
    "LinkedIn":  ROOT / ".agents/skills/linkedin-search/cli",
    "Indeed":    ROOT / ".agents/skills/indeed-search/cli",
    "Glassdoor": ROOT / ".agents/skills/glassdoor-search/cli",
}

# Tailored resumes are written here as: <Company>/<Role>/<Role>.docx + "Shrujal Agarwal.pdf"
TAILORED_ROOT = Path(r"G:\My Drive\Job_Search")
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


def _html_to_text(html: str) -> str:
    """Very small HTML-to-text: drop scripts/styles/nav, strip tags, collapse space."""
    html = re.sub(r"(?is)<(script|style|nav|header|footer|noscript)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&(nbsp|amp|lt|gt|#\d+|[a-z]+);", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def jd_from_url(url: str, timeout: int = 30) -> str:
    """
    Best-effort JD text from a job URL. Known boards go through the detail CLI;
    other URLs are fetched and stripped to text. Returns "" if it can't read it.
    """
    import urllib.request

    url = (url or "").strip()
    if not url:
        return ""
    low = url.lower()
    if "linkedin.com" in low:
        return fetch_jd("LinkedIn", url, timeout)
    if "indeed.com" in low:
        return fetch_jd("Indeed", url, timeout)
    if "glassdoor." in low:
        return fetch_jd("Glassdoor", url, timeout)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/131.0.0.0 Safari/537.36"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return _html_to_text(raw)
    except Exception:
        return ""


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


def tailor_job(job: dict, enforce_sponsorship: bool = True) -> dict:
    """
    Tailor a resume for one job.

    `job` needs: title, company, location, board, id (or url). May include
    a pre-fetched `jd_text`.

    enforce_sponsorship=True  -> sponsorship-blocked roles are skipped (search flow).
    enforce_sponsorship=False -> generate anyway, surface a warning (manual paste flow).

    Returns dict with: company, role, family, resume_path, pdf_path, jd_path,
    out_dir, warnings, exp_warning, sponsorship_warning, pdf_error, url, location,
    blocked, ok, error.
    """
    title = job.get("title", "Untitled")
    company = job.get("company", "Unknown")
    board = job.get("board", "")
    job_id = job.get("id") or job.get("url") or ""

    try:
        # Reuse the JD fetched during search if present; otherwise fetch now.
        jd_text = job.get("jd_text") or fetch_jd(board, job_id)

        # Sponsorship guard: F1 student needs sponsorship.
        blocked, sp_matched = analyze_sponsorship(jd_text)
        if blocked and enforce_sponsorship:
            return {
                "company": company, "role": title, "family": "",
                "resume_path": "", "pdf_path": "", "jd_path": "", "out_dir": "",
                "warnings": [], "exp_warning": "", "sponsorship_warning": "",
                "pdf_error": "", "url": job.get("url", ""),
                "location": job.get("location", ""),
                "blocked": True, "block_reason": ", ".join(sp_matched),
                "ok": True, "error": "",
            }
        sponsorship_warning = ""
        if blocked:
            sponsorship_warning = ("This role appears to restrict sponsorship / "
                                   "require work authorization the candidate lacks: "
                                   + ", ".join(sp_matched))

        family, _ = detect_family(title, jd_text)

        # Early-career guard: flag roles that ask for more than the target years.
        exp_warning = ""
        min_years = extract_min_years(jd_text)
        if min_years is not None and min_years > MAX_YEARS:
            exp_warning = (f"This role asks for {min_years}+ years of experience "
                           f"(above the ~{MAX_YEARS}-year early-career target).")

        data, tailoring_report = tailor_for_job(family, title, jd_text)

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
            "sponsorship_warning": sponsorship_warning,
            "tailoring_report": tailoring_report,
            "pdf_error": pdf_error, "url": job.get("url", ""),
            "location": job.get("location", ""),
            "blocked": False, "ok": True, "error": "",
        }
    except Exception as e:
        return {
            "company": company, "role": title, "family": "",
            "resume_path": "", "pdf_path": "", "jd_path": "", "out_dir": "",
            "warnings": [], "exp_warning": "", "sponsorship_warning": "",
            "pdf_error": "", "url": job.get("url", ""),
            "location": job.get("location", ""),
            "blocked": False, "ok": False, "error": str(e),
        }
