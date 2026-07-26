"""
Job Search Assistant — local Streamlit UI.

Tabs:
  1. Dashboard       — job-search progress with filters and visuals.
  2. Tracker         — track application status.
  3. Target Companies — manage priority employers and exhaustive search history.
  4. Search & Tailor — scrape job boards, score each job against the profile,
     queue jobs, and generate tailored resumes.
  5. Paste JD        — tailor a resume from pasted JD text or a job URL.
"""

import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from fit import score_job
from tailoring import tailor_job, fetch_jd, jd_from_url
from target_companies import (
    canonicalize_url,
    company_matches,
    database_summary,
    delete_companies,
    fetch_career_jobs,
    finish_search_run,
    geography_matches,
    import_records,
    initialize_database,
    job_keys,
    list_companies,
    record_job,
    records_from_workbook,
    role_match_score,
    run_jobs,
    save_company,
    split_target_roles,
    start_search_run,
    update_company_search_status,
)

STATUSES = ["To Apply", "Applied", "Phone Screen", "Interview",
            "Final Round", "Offer", "Rejected"]

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
CLI_ROOTS = {
    "LinkedIn":  ROOT / ".agents/skills/linkedin-search/cli",
    "Indeed":    ROOT / ".agents/skills/indeed-search/cli",
    "Glassdoor": ROOT / ".agents/skills/glassdoor-search/cli",
}
ALL_BOARDS = list(CLI_ROOTS.keys())
TRACKER_FILE = ROOT / "output" / "tracker.json"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Curated target-role search terms (priority order from the candidate profile).
TARGET_ROLES = [
    "Strategy & Operations Analyst",
    "Business Operations Analyst",
    "Operations Analyst",
    "Business Analyst",
    "Strategy Analyst",
    "Program Manager",
    "Business Program Manager",
    "Product Marketing Manager",
    "Marketing Operations",
    "Marketing Strategy",
    "Revenue Operations",
    "Corporate Strategy",
    "Consultant",
    "Operational Excellence",
    "Chief of Staff",
]


# ── Tracker persistence ───────────────────────────────────────────────────────
def load_tracker() -> list[dict]:
    if TRACKER_FILE.exists():
        return json.loads(TRACKER_FILE.read_text())
    return []


def save_tracker(rows: list[dict]) -> None:
    TRACKER_FILE.write_text(json.dumps(rows, indent=2))


# ── Daily plan persistence ────────────────────────────────────────────────────
PLAN_FILE = ROOT / "output" / "daily_plan.json"


def load_plan() -> dict:
    if PLAN_FILE.exists():
        try:
            return json.loads(PLAN_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_plan(data: dict) -> None:
    PLAN_FILE.write_text(json.dumps(data, indent=2))


def tracker_entry(
    company: str,
    role: str,
    location: str = "",
    url: str = "",
    job_key: str = "",
) -> dict | None:
    """Find the same posting in the tracker, including legacy tracker rows."""
    canonical_url = canonicalize_url(url)
    company_key = company.casefold().strip()
    role_key = role.casefold().strip()
    location_key = location.casefold().strip()
    for row in load_tracker():
        if job_key and row.get("job_key") == job_key:
            return row
        if (
            canonical_url
            and canonicalize_url(row.get("url", "")) == canonical_url
        ):
            return row
        if (
            row.get("company", "").casefold().strip() == company_key
            and row.get("role", "").casefold().strip() == role_key
            and (
                not location_key
                or not row.get("location", "").strip()
                or row.get("location", "").casefold().strip() == location_key
            )
        ):
            return row
    return None


def tracker_has(company: str, role: str) -> bool:
    return tracker_entry(company, role) is not None


def add_application(company: str, role: str, location: str = "", url: str = "",
                    status: str = "To Apply", notes: str = "",
                    job_key: str = "") -> bool:
    """Add a job to the tracker with status 'To Apply'. Returns False if a dup."""
    if tracker_entry(company, role, location, url, job_key):
        return False
    rows = load_tracker()
    rows.append({
        "company": company, "role": role, "location": location, "url": url,
        "job_key": job_key, "date_added": str(date.today()),
        "status": status, "notes": notes,
    })
    save_tracker(rows)
    return True


# ── Shared tailored-result renderer (used by Search and Paste tabs) ──────────
def render_result(r: dict, key_prefix: str) -> None:
    company = r.get("company", "")
    role = r.get("role", "")

    if r.get("blocked"):
        st.error(f"⛔ **{company} — {role}**: skipped — no sponsorship for F1 "
                 f"({r.get('block_reason', '')}). Verify in the posting before ruling it out.")
        return
    if not r.get("ok"):
        st.error(f"❌ {company} — {role}: {r.get('error', 'unknown error')}")
        return

    out_dir = r.get("out_dir") or (str(Path(r["resume_path"]).parent)
                                   if r.get("resume_path") else "")
    with st.expander(f"✅ {company} — {role}  ·  {r.get('family', '')}", expanded=True):
        st.write(f"**Role family detected:** {r.get('family', '')}")
        if out_dir:
            st.write(f"**Saved to:** `{out_dir}`")
        if r.get("sponsorship_warning"):
            st.warning("⚠️ " + r["sponsorship_warning"])
        if r.get("exp_warning"):
            st.warning("⚠️ " + r["exp_warning"])
        if r.get("warnings"):
            st.caption("Content trimmed to fit 1 page: " + "; ".join(r["warnings"]))
        report = r.get("tailoring_report") or {}
        if report:
            with st.expander("Tailoring details", expanded=False):
                themes = report.get("matched_themes", [])
                if themes:
                    st.write("**Matched themes:** " + ", ".join(themes))
                titles = report.get("selected_titles", {})
                if titles:
                    st.write("**Selected experience titles:**")
                    for employer, selected_title in titles.items():
                        st.write(f"- {employer}: {selected_title}")
                skills = report.get("matched_skills", [])
                if skills:
                    st.write("**Approved JD-matched skills:** " + ", ".join(skills))
                gaps = report.get("unapproved_jd_terms", [])
                if gaps:
                    st.warning(
                        "JD terms not added because they are not in the approved "
                        "candidate catalog: " + ", ".join(gaps)
                    )
        if r.get("pdf_error"):
            st.warning("PDF not created — " + r["pdf_error"] + " (the DOCX is still saved).")

        dl1, dl2 = st.columns(2)
        with dl1:
            if r.get("resume_path"):
                with open(r["resume_path"], "rb") as f:
                    st.download_button(
                        "⬇️ DOCX", data=f, file_name=Path(r["resume_path"]).name,
                        mime="application/vnd.openxmlformats-officedocument."
                             "wordprocessingml.document",
                        key=f"{key_prefix}_docx")
        with dl2:
            if r.get("pdf_path"):
                with open(r["pdf_path"], "rb") as f:
                    st.download_button(
                        "⬇️ PDF", data=f, file_name=Path(r["pdf_path"]).name,
                        mime="application/pdf", key=f"{key_prefix}_pdf")

        if tracker_entry(
            company, role, r.get("location", ""), r.get("url", "")
        ):
            st.success("✓ In tracker")
        elif st.button("➕ Add to Tracker", key=f"{key_prefix}_trk"):
            add_application(company, role, r.get("location", ""), r.get("url", ""),
                            status="To Apply", notes=f"Resume tailored ({r.get('family', '')})")
            st.rerun()


# ── Scraper ───────────────────────────────────────────────────────────────────
def _is_blocked(stderr: str, stdout: str) -> bool:
    blob = (stderr + stdout).lower()
    return any(s in blob for s in ("403", "401", "cloudflare", "access denied",
                                   "blocking this request"))


def _process_error_detail(
    stdout: str = "", stderr: str = "", fallback: str = ""
) -> str:
    """Return a compact, useful subprocess failure message."""
    detail = (stderr or stdout or fallback).strip()
    return " ".join(detail.split())[:320]


def validate_scraper_runtime(boards: list[str]) -> list[str]:
    """Verify that Bun can load each selected board CLI before a large run."""
    if not boards:
        return []
    bun = shutil.which("bun")
    if not bun:
        return [
            "Bun was not found. Run setup.ps1 or install Bun, then restart "
            "the app so the updated PATH is available."
        ]

    errors = []
    for board in boards:
        cli_dir = CLI_ROOTS[board]
        cli_file = cli_dir / "src" / "cli.ts"
        if not cli_file.exists():
            errors.append(f"{board}: missing scraper file {cli_file}")
            continue
        try:
            result = subprocess.run(
                [bun, "run", "src/cli.ts", "--help"],
                cwd=str(cli_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            errors.append(f"{board}: {error}")
            continue
        if result.returncode != 0:
            detail = _process_error_detail(
                result.stdout,
                result.stderr,
                f"scraper exited with code {result.returncode}",
            )
            errors.append(f"{board}: {detail}")
    return errors


def scrape_board(board: str, query: str, location: str, date_posted: str,
                 job_type: str, pages: int) -> tuple[list[dict], str, str]:
    """
    Scrape one board across N pages.
    Returns (jobs, status, detail) where status is 'ok', 'blocked', 'empty',
    or 'error'.
    """
    cli_dir = CLI_ROOTS[board]
    jobs: list[dict] = []
    status = "empty"
    detail = ""
    for page in range(1, pages + 1):
        cmd = ["bun", "run", "src/cli.ts", "search",
               "--query", query, "--format", "json", "--page", str(page)]
        if location:
            cmd += ["--location", location]
        if date_posted != "any":
            cmd += ["--datePosted", date_posted]
        if job_type != "any":
            cmd += ["--jobType", job_type]
        try:
            result = subprocess.run(
                cmd, cwd=str(cli_dir), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=40
            )
            if result.returncode != 0:
                status = "blocked" if _is_blocked(result.stderr, result.stdout) else "error"
                detail = _process_error_detail(
                    result.stdout,
                    result.stderr,
                    f"scraper exited with code {result.returncode}",
                )
                break
            raw = result.stdout.strip()
            if not raw:
                break
            data = json.loads(raw)
            results = data.get("results") if isinstance(data, dict) else data
            if not results:
                break
            for j in results:
                j["board"] = board
            jobs += results
            status = "ok"
        except subprocess.TimeoutExpired:
            status = "error"
            detail = "Scraper timed out after 40 seconds."
            break
        except json.JSONDecodeError as error:
            status = "error"
            detail = f"Scraper returned invalid JSON: {error}"
            break
        except OSError as error:
            status = "error"
            detail = str(error)
            break
    return jobs, status, detail


def _fetch_one_jd(job: dict) -> None:
    """Fetch and cache the full JD text on a job dict (in place)."""
    job["jd_text"] = fetch_jd(job.get("board", ""),
                              job.get("id") or job.get("url") or "")


def run_search(boards: list[str], queries: list[str], location: str,
               date_posted: str, job_type: str, pages: int) -> tuple[list[dict], dict]:
    """
    Scrape each (board, query), fetch each JD, score on the full JD, dedupe, sort.
    Returns (jobs, board_status).
    """
    # 1. Scrape every board for every selected role; dedupe globally.
    unique_jobs = []
    seen = set()
    board_status = {}
    n_tasks = max(1, len(boards) * len(queries))
    progress = st.progress(0.0, text="Searching boards…")
    task = 0
    for board in boards:
        statuses = []
        details = []
        kept = 0
        for q in queries:
            task += 1
            progress.progress(task / (n_tasks + 1),
                              text=f"Searching {board}: {q}…")
            board_jobs, status, detail = scrape_board(
                board, q, location, date_posted, job_type, pages
            )
            statuses.append(status)
            if detail and detail not in details:
                details.append(detail)
            for job in board_jobs:
                job["query"] = q
                title = job.get("title", "")
                company = job.get("company", "")
                key = (title.lower().strip(), company.lower().strip())
                if key in seen or not title:
                    continue
                seen.add(key)
                unique_jobs.append(job)
                kept += 1
        # Board status: prefer ok > blocked > error > empty across queries.
        if "ok" in statuses:
            bs = "ok"
        elif "blocked" in statuses:
            bs = "blocked"
        elif "error" in statuses:
            bs = "error"
        else:
            bs = "empty"
        board_status[board] = {
            "status": bs,
            "count": kept,
            "detail": details[0] if details else "",
        }

    # 2. Fetch every JD in parallel (this is what makes the score realistic).
    total = len(unique_jobs)
    if total:
        done = 0
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = [ex.submit(_fetch_one_jd, j) for j in unique_jobs]
            for _ in as_completed(futures):
                done += 1
                progress.progress(
                    (len(boards) + done / total) / (len(boards) + 1),
                    text=f"Reading job descriptions… {done}/{total}")

    # 3. Score on the full JD text.
    for job in unique_jobs:
        fit = score_job(job.get("title", ""), job.get("company", ""),
                        job.get("location", ""), job.get("jd_text", ""))
        job.update({
            "score": fit["score"], "tier": fit["tier"], "family": fit["family"],
            "reason": fit["reason"], "blocked": fit["blocked"],
            "scored_on_jd": fit["scored_on_jd"],
        })

    progress.progress(1.0, text="Done.")
    progress.empty()
    unique_jobs.sort(key=lambda j: j["score"], reverse=True)
    return unique_jobs, board_status


def _search_one_target_company(
    company: dict,
    boards: list[str],
    location: str,
    date_posted: str,
    job_type: str,
    pages: int,
    use_career_sites: bool,
    workers: int,
    run_id: int,
) -> dict:
    """Search one company's direct site and every saved target-role query."""
    candidates = []
    source_statuses = []

    if use_career_sites and company.get("career_url"):
        direct_jobs, status, detail = fetch_career_jobs(
            company["company_name"], company["career_url"]
        )
        candidates.extend(direct_jobs)
        source_statuses.append({
            "source": "Career site", "status": status, "detail": detail,
        })

    tasks = []
    for board in boards:
        for role in company.get("roles", []):
            tasks.append((board, role))

    if tasks:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            future_map = {
                executor.submit(
                    scrape_board,
                    board,
                    f"{company['company_name']} {role}",
                    location,
                    date_posted,
                    job_type,
                    pages,
                ): (board, role)
                for board, role in tasks
            }
            for future in as_completed(future_map):
                board, role = future_map[future]
                try:
                    board_jobs, status, detail = future.result()
                except Exception as error:
                    board_jobs, status, detail = [], "error", str(error)[:320]
                source_statuses.append({
                    "source": f"{board}: {role}",
                    "status": status,
                    "detail": detail,
                })
                for job in board_jobs:
                    job["query"] = role
                    candidates.append(job)

    kept = []
    seen_fingerprints = set()
    new_count = 0
    for job in candidates:
        is_direct = job.get("board") == "Career site"
        if not is_direct and not company_matches(job.get("company", ""), company):
            continue
        if is_direct:
            job["company"] = company["company_name"]
        score, matched_role = role_match_score(
            job.get("title", ""), company.get("roles", [])
        )
        if score < 45:
            continue
        if not geography_matches(job.get("location", ""), location):
            continue
        job["target_role_score"] = score
        job["matched_role"] = matched_role
        job["target_company"] = company["company_name"]
        _, fingerprint = job_keys(job)
        if fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)
        _, is_new = record_job(run_id, job, company, matched_role)
        new_count += int(is_new)
        kept.append(job)

    statuses = {item["status"] for item in source_statuses}
    if statuses & {"ok", "empty"}:
        company_status = "ok"
    elif "blocked" in statuses:
        company_status = "blocked"
    elif "unsupported" in statuses:
        company_status = "unsupported"
    elif not source_statuses:
        company_status = "not_configured"
    else:
        company_status = "error"
    update_company_search_status(company["id"], company_status, len(kept))
    return {
        "company": company["company_name"],
        "status": company_status,
        "jobs_found": len(kept),
        "jobs_new": new_count,
        "sources": source_statuses,
    }


def run_target_company_search(
    companies: list[dict],
    boards: list[str],
    location: str,
    date_posted: str,
    job_type: str,
    pages: int,
    use_career_sites: bool,
    workers: int,
) -> tuple[int, list[dict]]:
    """Run the exhaustive target-company search with persistent history."""
    sources = (["Career sites"] if use_career_sites else []) + boards
    run_id = start_search_run(
        location, date_posted, sources, len(companies)
    )
    reports = []
    progress = st.progress(0.0, text="Preparing target-company search...")
    for index, company in enumerate(companies, start=1):
        progress.progress(
            (index - 1) / max(1, len(companies)),
            text=(
                f"Searching {index}/{len(companies)}: "
                f"{company['company_name']}"
            ),
        )
        reports.append(_search_one_target_company(
            company, boards, location, date_posted, job_type, pages,
            use_career_sites, workers, run_id,
        ))
    progress.progress(1.0, text="Target-company search complete.")
    progress.empty()

    succeeded = sum(report["status"] == "ok" for report in reports)
    failed = len(reports) - succeeded
    jobs_found = sum(report["jobs_found"] for report in reports)
    jobs_new = sum(report["jobs_new"] for report in reports)
    finish_search_run(
        run_id, succeeded, failed, jobs_found, jobs_new
    )
    return run_id, reports


def render_target_companies_tab() -> None:
    """Render catalog management, Excel import, brute-force search, and history."""
    initialize_database()
    st.header("Target Companies")

    summary = database_summary()
    metrics = st.columns(4)
    metrics[0].metric(
        "Companies",
        summary["companies"],
        f"{summary['active_companies']} active",
    )
    metrics[1].metric("Target roles", summary["roles"])
    metrics[2].metric("Career URLs", summary["career_urls"])
    metrics[3].metric("Jobs remembered", summary["seen_jobs"])

    with st.expander("Import or update from Excel"):
        uploaded = st.file_uploader(
            "Target-company workbook",
            type=["xlsx"],
            key="target_company_upload",
            help=(
                "Every sheet is read. Existing companies and roles are merged; "
                "reimporting the same workbook does not create duplicates."
            ),
        )
        if st.button(
            "Import workbook",
            disabled=uploaded is None,
            key="import_target_workbook",
        ):
            try:
                records = records_from_workbook(uploaded.getvalue())
                result = import_records(records)
                st.session_state["target_import_result"] = result
                st.success(
                    f"Read {len(records)} rows. Added "
                    f"{result['companies_added']} companies and "
                    f"{result['roles_added']} roles; merged "
                    f"{result['duplicates_merged']} existing company rows."
                )
            except Exception as error:
                st.error(f"Import failed: {error}")
        result = st.session_state.get("target_import_result") or {}
        conflicts = result.get("career_url_conflicts") or []
        if conflicts:
            st.warning(
                "Some imported career URLs differed from saved URLs. Existing "
                "URLs were preserved so they can be reviewed before replacement."
            )
            st.dataframe(pd.DataFrame(conflicts), hide_index=True)

    with st.expander("Add a target company"):
        left, right = st.columns(2)
        with left:
            new_company = st.text_input(
                "Company name", key="new_target_company"
            )
            new_roles = st.text_area(
                "Target roles",
                key="new_target_roles",
                placeholder="Business Analyst, Strategy & Operations Analyst",
            )
            new_location = st.text_input(
                "Preferred location", key="new_target_location"
            )
        with right:
            new_career_url = st.text_input(
                "Career website URL", key="new_target_career_url"
            )
            new_category = st.text_input(
                "Category", key="new_target_category"
            )
            new_notes = st.text_area("Notes", key="new_target_notes")
        if st.button("Add company", key="add_target_company"):
            if not new_company.strip():
                st.warning("Enter a company name.")
            elif not split_target_roles(new_roles):
                st.warning("Enter at least one target role.")
            else:
                save_company(
                    new_company,
                    split_target_roles(new_roles),
                    location=new_location,
                    career_url=new_career_url,
                    category=new_category,
                    notes=new_notes,
                )
                st.success("Target company saved.")
                st.rerun()

    companies = list_companies()
    st.subheader("Company List")
    st.caption(
        "Edit values directly, then save. Deactivating a company keeps its "
        "history but excludes it from brute-force searches."
    )
    company_df = pd.DataFrame([{
        "_ID": company["id"],
        "Active": company["active"],
        "Company": company["company_name"],
        "Target Roles": ", ".join(company["roles"]),
        "Location": company["location"],
        "Career URL": company["career_url"],
        "Category": company["category"],
        "Notes": company["notes"],
        "Source Tabs": ", ".join(company["source_tabs"]),
        "Last Search": company["last_searched_at"],
        "Search Status": company["last_search_status"],
        "Delete": False,
    } for company in companies])
    edited = st.data_editor(
        company_df,
        hide_index=True,
        use_container_width=True,
        height=480,
        column_config={
            "_ID": None,
            "Active": st.column_config.CheckboxColumn("Active", width="small"),
            "Company": st.column_config.TextColumn("Company", width="medium"),
            "Target Roles": st.column_config.TextColumn(
                "Target Roles", width="large"
            ),
            "Location": st.column_config.TextColumn("Location", width="medium"),
            "Career URL": st.column_config.LinkColumn(
                "Career URL", width="large"
            ),
            "Category": st.column_config.TextColumn("Category", width="medium"),
            "Notes": st.column_config.TextColumn("Notes", width="large"),
            "Source Tabs": st.column_config.TextColumn(
                "Imported From", width="small"
            ),
            "Last Search": st.column_config.TextColumn(
                "Last Search", width="small"
            ),
            "Search Status": st.column_config.TextColumn(
                "Status", width="small"
            ),
            "Delete": st.column_config.CheckboxColumn(
                "Delete", width="small"
            ),
        },
        disabled=["Source Tabs", "Last Search", "Search Status"],
        key="target_company_editor",
    )

    def cell_text(value) -> str:
        return "" if pd.isna(value) else str(value).strip()

    if st.button("Save company changes", type="primary"):
        delete_ids = []
        errors = []
        for _, row in edited.iterrows():
            company_id = int(row["_ID"])
            if bool(row["Delete"]):
                delete_ids.append(company_id)
                continue
            try:
                save_company(
                    cell_text(row["Company"]),
                    split_target_roles(cell_text(row["Target Roles"])),
                    location=cell_text(row["Location"]),
                    career_url=cell_text(row["Career URL"]),
                    category=cell_text(row["Category"]),
                    notes=cell_text(row["Notes"]),
                    active=bool(row["Active"]),
                    company_id=company_id,
                )
            except Exception as error:
                errors.append(f"{row['Company']}: {error}")
        delete_companies(delete_ids)
        if errors:
            st.error("Some rows could not be saved: " + "; ".join(errors))
        else:
            st.success("Company list updated.")
            st.rerun()

    st.divider()
    st.subheader("Brute-Force Search")
    st.caption(
        "Searches every active target company and every saved role. Career "
        "sites are checked when a URL is available; selected job boards provide "
        "coverage for the rest."
    )
    st.caption(
        "Status meanings: ok = search executed; empty = executed with no "
        "results; blocked = the website denied access; error = the scraper "
        "could not run; unsupported = the career-site format is not supported."
    )
    left, right = st.columns(2)
    with left:
        location = st.text_input(
            "Geographic scope",
            value="California, USA",
            key="target_location",
            help="Leave blank to include every location.",
        )
        date_posted = st.selectbox(
            "Date posted",
            ["any", "day", "week", "month"],
            format_func=lambda value: {
                "any": "Any time",
                "day": "Past 24h",
                "week": "Past week",
                "month": "Past month",
            }[value],
            key="target_date_posted",
        )
        job_type = st.selectbox(
            "Job type",
            ["any", "fulltime", "internship", "contract"],
            format_func=lambda value: (
                value.title() if value != "any" else "Any"
            ),
            key="target_job_type",
        )
    with right:
        boards = st.multiselect(
            "Supplementary job boards",
            ALL_BOARDS,
            default=ALL_BOARDS,
            key="target_boards",
        )
        pages = st.number_input(
            "Pages per role and board",
            min_value=1,
            max_value=5,
            value=1,
            key="target_pages",
        )
        workers = st.number_input(
            "Concurrent searches",
            min_value=1,
            max_value=6,
            value=3,
            key="target_workers",
            help="Lower this if a job board begins rate-limiting searches.",
        )
        use_career_sites = st.checkbox(
            "Search saved career websites",
            value=True,
            key="use_target_career_sites",
        )

    active_companies = [
        company for company in companies if company["active"]
    ]
    test_column, search_column = st.columns([1, 3])
    with test_column:
        test_runtime = st.button(
            "Test search setup",
            disabled=not boards,
            key="test_target_search_runtime",
        )
    with search_column:
        start_search = st.button(
            f"Search All {len(active_companies)} Active Companies",
            type="primary",
            disabled=not active_companies or (
                not boards and not use_career_sites
            ),
            key="run_target_search",
        )

    if test_runtime:
        runtime_errors = validate_scraper_runtime(boards)
        if runtime_errors:
            st.error("One or more selected job-board scrapers cannot run.")
            st.code("\n".join(runtime_errors), language=None)
        else:
            st.success("Bun and all selected job-board scrapers are ready.")

    if start_search:
        runtime_errors = validate_scraper_runtime(boards)
        if runtime_errors:
            st.error(
                "Search did not start because the selected scraper runtime "
                "failed its preflight check."
            )
            st.code("\n".join(runtime_errors), language=None)
        else:
            run_id, reports = run_target_company_search(
                active_companies,
                boards,
                location,
                date_posted,
                job_type,
                int(pages),
                use_career_sites,
                int(workers),
            )
            st.session_state["target_run_id"] = run_id
            st.session_state["target_search_reports"] = reports

    reports = st.session_state.get("target_search_reports") or []
    if reports:
        jobs_found = sum(report["jobs_found"] for report in reports)
        jobs_new = sum(report["jobs_new"] for report in reports)
        searched_ok = sum(report["status"] == "ok" for report in reports)
        summary_message = (
            f"Search complete: {jobs_new} new jobs, {jobs_found} matching "
            f"jobs found, {searched_ok}/{len(reports)} companies searched "
            "successfully."
        )
        if searched_ok == len(reports):
            st.success(summary_message)
        elif searched_ok:
            st.warning(summary_message)
        else:
            st.error(summary_message)
        with st.expander("Company-by-company search coverage"):
            def coverage_detail(report: dict) -> str:
                details = []
                for source in report["sources"]:
                    if source["status"] in {"ok", "empty"}:
                        continue
                    board = source["source"].split(":", 1)[0]
                    detail = source.get("detail") or source["status"]
                    item = f"{board}: {detail}"
                    if item not in details:
                        details.append(item)
                return "; ".join(details[:3])

            st.dataframe(pd.DataFrame([{
                "Company": report["company"],
                "Status": report["status"],
                "Matching Jobs": report["jobs_found"],
                "New Jobs": report["jobs_new"],
                "Details": coverage_detail(report),
            } for report in reports]), hide_index=True, use_container_width=True)

    run_id = st.session_state.get("target_run_id")
    if not run_id:
        return
    new_only = st.checkbox(
        "Show only jobs discovered for the first time in this search",
        value=True,
        key="target_new_only",
    )
    jobs = run_jobs(run_id, new_only=new_only)
    if not jobs:
        st.info(
            "No jobs match this view. Untick the new-only filter to review "
            "previously seen jobs found again in this search."
        )
        return

    result_rows = []
    for job in jobs:
        tracker_row = tracker_entry(
            job["company_name"],
            job["title"],
            job["location"],
            job["canonical_url"],
            job["job_key"],
        )
        result_rows.append({
            "Add": False,
            "Company": job["company_name"],
            "Title": job["title"],
            "Location": job["location"],
            "Matched Target Role": job["matched_role"],
            "Application": (
                tracker_row.get("status", "In tracker")
                if tracker_row else "Not tracked"
            ),
            "Source": ", ".join(json.loads(job["sources_json"] or "[]")),
            "First Seen": job["first_seen"],
            "URL": job["canonical_url"],
        })
    results_df = pd.DataFrame(result_rows)
    edited_results = st.data_editor(
        results_df,
        hide_index=True,
        use_container_width=True,
        height=460,
        column_config={
            "Add": st.column_config.CheckboxColumn(
                "Add to Tracker", width="small"
            ),
            "Company": st.column_config.TextColumn("Company", width="small"),
            "Title": st.column_config.TextColumn("Title", width="medium"),
            "Location": st.column_config.TextColumn("Location", width="small"),
            "Matched Target Role": st.column_config.TextColumn(
                "Matched Role", width="medium"
            ),
            "Application": st.column_config.TextColumn(
                "Application", width="small"
            ),
            "Source": st.column_config.TextColumn("Source", width="small"),
            "First Seen": st.column_config.TextColumn(
                "First Seen", width="small"
            ),
            "URL": st.column_config.LinkColumn(
                "Job Posting", width="large", display_text="Open"
            ),
        },
        disabled=[
            "Company", "Title", "Location", "Matched Target Role",
            "Application", "Source", "First Seen", "URL",
        ],
        key="target_job_results",
    )
    selected = edited_results.index[edited_results["Add"]].tolist()
    if st.button(
        f"Add Selected to Tracker ({len(selected)})",
        disabled=not selected,
        key="add_target_jobs_to_tracker",
    ):
        added = 0
        for index in selected:
            job = jobs[index]
            added += int(add_application(
                job["company_name"],
                job["title"],
                job["location"],
                job["canonical_url"],
                status="To Apply",
                notes=(
                    "Target-company search; matched "
                    f"{job['matched_role']}"
                ),
                job_key=job["job_key"],
            ))
        st.success(f"Added {added} new job(s) to the tracker.")
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Job Search Assistant", page_icon="💼", layout="wide")
st.title("💼 Job Search Assistant")
st.caption("Shrujal Agarwal — local workflow tool")

tab_dashboard, tab_tracker, tab_targets, tab_search, tab_paste = st.tabs(
    [
        "📊 Dashboard",
        "🗂️ Tracker",
        "🎯 Target Companies",
        "🔍 Search & Tailor",
        "📝 Paste JD",
    ]
)

with tab_targets:
    render_target_companies_tab()

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — SEARCH & TAILOR
# ════════════════════════════════════════════════════════════════════════════
with tab_search:
    st.header("Job Board Search")

    c1, c2 = st.columns(2)
    with c1:
        queries = st.multiselect(
            "Role / Keywords", options=TARGET_ROLES, default=[],
            accept_new_options=True,
            placeholder="Pick your target roles (or type a custom one)",
            help="Select one or more of your target roles — each is searched and "
                 "the results are combined and de-duplicated. You can also type a "
                 "custom keyword and press Enter.")
        location = st.text_input("Location", placeholder="California, USA")
    with c2:
        board_choice = st.selectbox("Job Board", ["All Boards"] + ALL_BOARDS)
        date_posted = st.selectbox(
            "Date Posted", ["any", "day", "week", "month"],
            format_func=lambda x: {"any": "Any time", "day": "Past 24h",
                                   "week": "Past week", "month": "Past month"}[x])

    c3, c4 = st.columns(2)
    with c3:
        job_type = st.selectbox(
            "Job Type", ["any", "fulltime", "internship", "contract"],
            format_func=lambda x: x.title() if x != "any" else "Any")
    with c4:
        pages = st.number_input("Pages per board", min_value=1, max_value=5, value=1,
                                help="Each job's full description is fetched and parsed "
                                     "for the fit score, so more pages = noticeably slower. "
                                     "LinkedIn ~25/pg.")

    if st.button("Search Jobs", type="primary"):
        if not queries:
            st.warning("Pick at least one role (or type a custom keyword) to search.")
        else:
            boards = ALL_BOARDS if board_choice == "All Boards" else [board_choice]
            with st.spinner("Scraping, reading job descriptions, and scoring…"):
                jobs, board_status = run_search(boards, queries, location,
                                                date_posted, job_type, int(pages))
            st.session_state["jobs"] = jobs
            st.session_state["tailor_results"] = []  # clear stale tailored results

            # Per-board status line (honest about Cloudflare-blocked boards)
            icons = {"ok": "✅", "blocked": "🚫", "error": "⚠️", "empty": "∅"}
            labels = {"ok": lambda c: f"{c} jobs", "blocked": lambda c: "blocked (Cloudflare)",
                      "error": lambda c: "error", "empty": lambda c: "no results"}
            parts = [f"{icons[s['status']]} **{b}**: {labels[s['status']](s['count'])}"
                     for b, s in board_status.items()]
            st.caption("  ·  ".join(parts))
            scraper_errors = [
                f"{board}: {status['detail']}"
                for board, status in board_status.items()
                if status["status"] == "error" and status.get("detail")
            ]
            if scraper_errors:
                st.error("One or more job-board scrapers could not run.")
                st.code("\n".join(scraper_errors), language=None)

            if jobs:
                n_jd = sum(1 for j in jobs if j.get("scored_on_jd"))
                n_blocked = sum(1 for j in jobs if j.get("blocked"))
                msg = (f"Found {len(jobs)} unique jobs · scored on full JD: {n_jd}/"
                       f"{len(jobs)}")
                if n_blocked:
                    msg += f" · {n_blocked} sponsorship-blocked"
                st.success(msg + ".")
                if n_jd < len(jobs):
                    st.caption("Some descriptions couldn't be fetched — those were "
                               "scored on title/company/location only.")
                if any(s["status"] == "blocked" for s in board_status.values()):
                    st.info("Indeed and Glassdoor sit behind Cloudflare and often block "
                            "automated requests. LinkedIn is the reliable source.")
            else:
                st.info("No results. LinkedIn is the most reliable board; "
                        "try different keywords.")

    # ── Results table with fit scores + queue checkboxes ─────────────────────
    if "jobs" in st.session_state and st.session_state["jobs"]:
        all_jobs_state = st.session_state["jobs"]
        st.subheader("Results")

        hide_blocked = st.checkbox(
            "Hide sponsorship-blocked roles", value=True,
            help="Roles whose JD requires citizenship / ITAR / no sponsorship, "
                 "which an F1 student can't apply to.")
        jobs = [j for j in all_jobs_state if not (hide_blocked and j.get("blocked"))]
        if hide_blocked and not jobs:
            st.info("Every result was sponsorship-blocked — showing them all so you "
                    "can review. Untick the box to keep them visible.")
            jobs = all_jobs_state

        n_hidden = len(all_jobs_state) - len(jobs)
        caption = ("Tick **Queue** for jobs you want tailored resumes for, then click "
                   "**Tailor Selected Resumes**. Sorted by fit score (best first).")
        if n_hidden:
            caption += f"  ({n_hidden} sponsorship-blocked role(s) hidden.)"
        st.caption(caption)

        df = pd.DataFrame([{
            "Queue": False,
            "Score": j["score"],
            "Tier": j["tier"],
            "Title": j.get("title", ""),
            "Company": j.get("company", ""),
            "Location": j.get("location", ""),
            "Why this score": j["reason"],
            "Board": j.get("board", ""),
        } for j in jobs])

        edited = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            height=480,
            column_config={
                "Queue": st.column_config.CheckboxColumn("Queue", width="small"),
                "Score": st.column_config.ProgressColumn(
                    "Fit", min_value=0, max_value=100, format="%d"),
                "Tier": st.column_config.TextColumn("Tier", width="small"),
                "Title": st.column_config.TextColumn("Title", width="medium"),
                "Company": st.column_config.TextColumn("Company", width="small"),
                "Location": st.column_config.TextColumn("Location", width="small"),
                "Why this score": st.column_config.TextColumn(
                    "Why this score", width="large"),
                "Board": st.column_config.TextColumn("Board", width="small"),
            },
            disabled=["Score", "Tier", "Title", "Company", "Location",
                      "Why this score", "Board"],
            key="results_editor",
        )

        # Real (clickable) job links — data_editor renders on a canvas so its
        # LinkColumn isn't a true anchor; HTML anchors below always work and
        # open in a new tab. NOTE: open the app in a real browser
        # (http://localhost:8501) — the embedded preview blocks external URLs.
        with st.expander("📎 Open job postings (opens in a new tab)"):
            rows_html = []
            for j in jobs:
                url = j.get("url", "")
                title = j.get("title", "")
                company = j.get("company", "")
                score = j["score"]
                if url:
                    rows_html.append(
                        f'<div style="margin:4px 0;"><b>[{score}]</b> '
                        f'<a href="{url}" target="_blank" rel="noopener noreferrer">'
                        f'{title} — {company}</a></div>')
                else:
                    rows_html.append(
                        f'<div style="margin:4px 0;"><b>[{score}]</b> '
                        f'{title} — {company} <i>(no link)</i></div>')
            st.markdown("\n".join(rows_html), unsafe_allow_html=True)

        queued_idx = edited.index[edited["Queue"]].tolist()
        n_queued = len(queued_idx)

        col_a, col_b = st.columns([1, 3])
        with col_a:
            tailor_clicked = st.button(
                f"🎯 Tailor Selected Resumes ({n_queued})",
                type="primary", disabled=(n_queued == 0))
        with col_b:
            if n_queued:
                st.caption(f"{n_queued} job(s) queued for tailoring.")

        if tailor_clicked and n_queued:
            results = []
            prog = st.progress(0.0, text="Tailoring…")
            for k, idx in enumerate(queued_idx):
                job = jobs[idx]
                prog.progress(k / n_queued,
                              text=f"Tailoring: {job.get('title', '')[:40]}…")
                results.append(tailor_job(job))
            prog.empty()
            # Persist so the Add-to-Tracker buttons survive reruns.
            st.session_state["tailor_results"] = results

        # Render tailored results (persisted) — outside the click guard so the
        # Add-to-Tracker buttons keep working after a rerun.
        if st.session_state.get("tailor_results"):
            st.subheader("Tailored Resumes")
            for i, r in enumerate(st.session_state["tailor_results"]):
                render_result(r, key_prefix=f"search_{i}")

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — PASTE JD
# ════════════════════════════════════════════════════════════════════════════
with tab_paste:
    st.header("Tailor from a Pasted JD or Link")
    st.caption("For a role you found elsewhere. Paste the description (or a link), "
               "add the company and title, and generate a tailored resume.")

    pc1, pc2 = st.columns(2)
    with pc1:
        p_company = st.text_input("Company", key="paste_company",
                                  placeholder="e.g. Stripe")
    with pc2:
        p_role = st.text_input("Role / Job Title", key="paste_role",
                               placeholder="e.g. Strategy & Operations Manager")

    source = st.radio("Job description source", ["Paste text", "From URL"],
                      horizontal=True, key="paste_source")
    p_jd, p_url = "", ""
    if source == "Paste text":
        p_jd = st.text_area("Paste the full job description", height=220,
                            key="paste_jd_text")
    else:
        p_url = st.text_input("Job posting URL", key="paste_url",
                              placeholder="https://…")
        st.caption("LinkedIn links work best. Some sites (Indeed/Glassdoor and "
                   "Cloudflare-protected pages) may block reading — paste the text instead.")

    if st.button("🎯 Generate Tailored Resume", type="primary", key="paste_generate"):
        if not p_company.strip() or not p_role.strip():
            st.warning("Enter both the company and the role/title.")
        elif source == "Paste text" and not p_jd.strip():
            st.warning("Paste the job description text.")
        elif source == "From URL" and not p_url.strip():
            st.warning("Enter the job posting URL.")
        else:
            with st.spinner("Reading the JD and tailoring…"):
                jd_text = p_jd
                if source == "From URL":
                    jd_text = jd_from_url(p_url)
                if not jd_text or not jd_text.strip():
                    st.session_state["paste_result"] = None
                    st.error("Couldn't read a job description from that URL. "
                             "Please switch to 'Paste text' and paste it directly.")
                else:
                    job = {"title": p_role.strip(), "company": p_company.strip(),
                           "location": "", "board": "", "id": "",
                           "url": p_url.strip(), "jd_text": jd_text}
                    # Don't hard-skip on sponsorship here — warn but still generate.
                    st.session_state["paste_result"] = tailor_job(
                        job, enforce_sponsorship=False)

    if st.session_state.get("paste_result"):
        st.subheader("Tailored Resume")
        render_result(st.session_state["paste_result"], key_prefix="paste")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
with tab_dashboard:
    st.header("Your Job Search Dashboard")

    # Motivational slide-roll (self-contained CSS animation).
    MESSAGES = [
        "The light is just around the corner, Shrujal — keep going. 💡",
        "Every application is a step closer. You've got this, Shrujal! 💪",
        "Rejection is redirection. The right role is coming, Shrujal. 🌟",
        "Your breakthrough is one 'yes' away. Keep showing up, Shrujal. 🚀",
        "Progress over perfection — you're doing great, Shrujal. 🌱",
        "Someone out there needs exactly what you bring, Shrujal. ✨",
        "Consistency beats luck. Keep the momentum, Shrujal. 🔥",
        "You are the best, Shrujal — believe it and keep pushing. 🏆",
    ]
    n = len(MESSAGES)
    dur = n * 3.6  # seconds per full cycle
    slide_pct = 100 / n
    slides = "".join(
        f'<div class="slide" style="animation-delay:{i * dur / n:.2f}s">{m}</div>'
        for i, m in enumerate(MESSAGES))
    carousel = f"""
    <style>
      .roll-wrap {{
        position: relative; height: 64px; border-radius: 12px;
        background: linear-gradient(90deg,#2F5496,#3a63ad);
        overflow: hidden; font-family: 'Segoe UI',system-ui,sans-serif;
      }}
      .slide {{
        position: absolute; inset: 0; display: flex; align-items: center;
        justify-content: center; text-align: center; padding: 0 18px;
        color: #fff; font-size: 18px; font-weight: 600; opacity: 0;
        animation: roll {dur}s infinite;
      }}
      @keyframes roll {{
        0% {{ opacity: 0; transform: translateY(10px); }}
        3% {{ opacity: 1; transform: translateY(0); }}
        {slide_pct - 3:.1f}% {{ opacity: 1; transform: translateY(0); }}
        {slide_pct:.1f}% {{ opacity: 0; transform: translateY(-10px); }}
        100% {{ opacity: 0; }}
      }}
    </style>
    <div class="roll-wrap">{slides}</div>
    """
    components.html(carousel, height=76)

    # ── Today's plan ─────────────────────────────────────────────────────────
    today = str(date.today())
    plan = load_plan()
    todays = plan if plan.get("date") == today else {}

    st.subheader("📋 Today's Plan")
    if not todays.get("plan"):
        st.write("**What's your plan for today, Shrujal?** Set a clear, achievable "
                 "target and go after it.")
        plan_text = st.text_area(
            "Today's plan", key="plan_input", height=90, label_visibility="collapsed",
            placeholder="e.g. Apply to 5 target roles, follow up with 2 recruiters, "
                        "tailor 3 resumes.")
        if st.button("💪 Set my plan", type="primary"):
            if plan_text.strip():
                save_plan({"date": today, "plan": plan_text.strip(), "done": False})
                st.rerun()
            else:
                st.warning("Write a quick plan first, Shrujal — even one line counts.")
    elif todays.get("done"):
        st.success(f"🎉 **You did it, Shrujal!** Today's plan: _{todays['plan']}_")
        st.markdown("You showed up and followed through. That's how momentum is "
                    "built — one focused day at a time. So proud of you, Shrujal. "
                    "Rest up and go again tomorrow. 🌟")
        if st.button("Edit today's plan"):
            save_plan({"date": today, "plan": todays["plan"], "done": False})
            st.rerun()
    else:
        st.info(f"**Today's focus:** {todays['plan']}")
        st.markdown("You've set your intention, Shrujal — now break it into small "
                    "steps and knock them out one by one. Every action moves you "
                    "closer. **You can do this, Shrujal!** 💪🚀")
        pc1, pc2 = st.columns([1, 1])
        with pc1:
            if st.button("✅ Mark today's plan complete"):
                save_plan({"date": today, "plan": todays["plan"], "done": True})
                st.rerun()
        with pc2:
            if st.button("✏️ Change plan"):
                save_plan({})
                st.rerun()

    st.divider()

    rows = load_tracker()
    if not rows:
        st.info("No applications tracked yet. Tailor a resume and click "
                "**Add to Tracker**, or add entries in the Tracker tab.")
    else:
        df = pd.DataFrame(rows)

        # Filters
        f1, f2 = st.columns(2)
        with f1:
            companies = sorted(df["company"].dropna().unique().tolist())
            pick_co = st.multiselect("Filter by company", companies, default=[])
        with f2:
            pick_st = st.multiselect("Filter by status", STATUSES, default=[])
        view = df.copy()
        if pick_co:
            view = view[view["company"].isin(pick_co)]
        if pick_st:
            view = view[view["status"].isin(pick_st)]

        # Metrics
        total = len(view)
        applied = int((view["status"] != "To Apply").sum())
        interviewing = int(view["status"].isin(
            ["Phone Screen", "Interview", "Final Round"]).sum())
        offers = int((view["status"] == "Offer").sum())
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total tracked", total)
        m2.metric("Applied", applied)
        m3.metric("Interviewing", interviewing)
        m4.metric("Offers", offers)

        # Status breakdown (ordered by pipeline stage)
        st.subheader("Pipeline by status")
        counts = (view["status"].value_counts()
                  .reindex(STATUSES).fillna(0).astype(int))
        st.bar_chart(counts, horizontal=True, color="#2F5496")

        # Applications over time
        if "date_added" in view.columns and view["date_added"].notna().any():
            st.subheader("Applications added over time")
            ts = view.copy()
            ts["date_added"] = pd.to_datetime(ts["date_added"], errors="coerce")
            daily = (ts.dropna(subset=["date_added"])
                     .groupby(ts["date_added"].dt.date).size().cumsum())
            if len(daily):
                st.area_chart(daily, color="#2F5496")

        with st.expander("View filtered applications table"):
            st.dataframe(
                view[["company", "role", "status", "date_added", "location"]],
                hide_index=True, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — TRACKER
# ════════════════════════════════════════════════════════════════════════════
with tab_tracker:
    st.header("Application Tracker")
    rows = load_tracker()

    with st.expander("+ Add Application"):
        nc1, nc2 = st.columns(2)
        with nc1:
            t_company = st.text_input("Company", key="t_company")
            t_role = st.text_input("Role", key="t_role")
            t_location = st.text_input("Location", key="t_location")
        with nc2:
            t_url = st.text_input("Job URL", key="t_url")
            t_status = st.selectbox("Status", STATUSES, key="t_status")
            t_notes = st.text_input("Notes", key="t_notes")
        if st.button("Add Entry"):
            if t_company and t_role:
                added = add_application(
                    t_company, t_role, t_location, t_url,
                    status=t_status, notes=t_notes,
                )
                if added:
                    st.success("Added.")
                else:
                    st.info("That job is already in the tracker.")
                st.rerun()

    if not rows:
        st.info("No applications tracked yet.")
    else:
        st.caption("Edit **Status** or **Notes** right in the table, tick **🗑** to "
                   "delete a row, then click **Save changes**.")

        tdf = pd.DataFrame([{
            "Company": r.get("company", ""),
            "Role": r.get("role", ""),
            "Status": r.get("status", "To Apply"),
            "Location": r.get("location", ""),
            "Added": r.get("date_added", ""),
            "Notes": r.get("notes", ""),
            "🗑": False,
        } for r in rows])

        edited = st.data_editor(
            tdf, hide_index=True, use_container_width=True, height=430,
            column_config={
                "Company": st.column_config.TextColumn("Company", width="small"),
                "Role": st.column_config.TextColumn("Role", width="medium"),
                "Status": st.column_config.SelectboxColumn(
                    "Status", options=STATUSES, width="small", required=True),
                "Location": st.column_config.TextColumn("Location", width="small"),
                "Added": st.column_config.TextColumn("Added", width="small"),
                "Notes": st.column_config.TextColumn("Notes", width="large"),
                "🗑": st.column_config.CheckboxColumn(
                    "🗑", width="small", help="Tick to delete this row on Save"),
            },
            disabled=["Company", "Role", "Location", "Added"],
            key="tracker_editor",
        )

        b1, b2, _ = st.columns([1, 1, 3])
        with b1:
            if st.button("💾 Save changes", type="primary"):
                new_rows = []
                for idx, r in enumerate(rows):
                    e = edited.iloc[idx]
                    if bool(e["🗑"]):
                        continue
                    r["status"] = e["Status"]
                    r["notes"] = e["Notes"]
                    new_rows.append(r)
                save_tracker(new_rows)
                st.success("Saved.")
                st.rerun()
        with b2:
            export_df = pd.DataFrame(rows)
            st.download_button(
                "⬇️ Export CSV", data=export_df.to_csv(index=False),
                file_name="applications.csv", mime="text/csv")
