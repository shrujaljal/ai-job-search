"""
Job Search Assistant — local Streamlit UI.

Tabs:
  1. Search & Tailor — scrape all job boards, score each job against the profile,
     queue jobs, and generate tailored resumes.
  2. Tracker         — track application status.
"""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from fit import score_job
from tailoring import tailor_job, fetch_jd

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


# ── Tracker persistence ───────────────────────────────────────────────────────
def load_tracker() -> list[dict]:
    if TRACKER_FILE.exists():
        return json.loads(TRACKER_FILE.read_text())
    return []


def save_tracker(rows: list[dict]) -> None:
    TRACKER_FILE.write_text(json.dumps(rows, indent=2))


# ── Scraper ───────────────────────────────────────────────────────────────────
def _is_blocked(stderr: str, stdout: str) -> bool:
    blob = (stderr + stdout).lower()
    return any(s in blob for s in ("403", "401", "cloudflare", "access denied",
                                   "blocking this request"))


def scrape_board(board: str, query: str, location: str, date_posted: str,
                 job_type: str, pages: int) -> tuple[list[dict], str]:
    """
    Scrape one board across N pages.
    Returns (jobs, status) where status is 'ok', 'blocked', 'empty', or 'error'.
    """
    cli_dir = CLI_ROOTS[board]
    jobs: list[dict] = []
    status = "empty"
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
            break
        except json.JSONDecodeError:
            status = "error"
            break
    return jobs, status


def _fetch_one_jd(job: dict) -> None:
    """Fetch and cache the full JD text on a job dict (in place)."""
    job["jd_text"] = fetch_jd(job.get("board", ""),
                              job.get("id") or job.get("url") or "")


def run_search(boards: list[str], query: str, location: str, date_posted: str,
               job_type: str, pages: int) -> tuple[list[dict], dict]:
    """
    Scrape boards, fetch each JD, score on the full JD, dedupe, sort.
    Returns (jobs, board_status).
    """
    # 1. Scrape all boards and dedupe.
    unique_jobs = []
    seen = set()
    board_status = {}
    progress = st.progress(0.0, text="Searching boards…")
    for i, board in enumerate(boards):
        progress.progress(i / (len(boards) + 1), text=f"Searching {board}…")
        board_jobs, status = scrape_board(board, query, location, date_posted,
                                          job_type, pages)
        kept = 0
        for job in board_jobs:
            title = job.get("title", "")
            company = job.get("company", "")
            key = (title.lower().strip(), company.lower().strip())
            if key in seen or not title:
                continue
            seen.add(key)
            unique_jobs.append(job)
            kept += 1
        board_status[board] = {"status": status, "count": kept}

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


# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Job Search Assistant", page_icon="💼", layout="wide")
st.title("💼 Job Search Assistant")
st.caption("Shrujal Agarwal — local workflow tool")

tab_search, tab_tracker = st.tabs(["🔍 Search & Tailor", "📊 Tracker"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — SEARCH & TAILOR
# ════════════════════════════════════════════════════════════════════════════
with tab_search:
    st.header("Job Board Search")

    c1, c2 = st.columns(2)
    with c1:
        query = st.text_input("Role / Keywords", placeholder="Strategy & Operations Analyst")
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
        if not query:
            st.warning("Enter a role or keywords to search.")
        else:
            boards = ALL_BOARDS if board_choice == "All Boards" else [board_choice]
            with st.spinner("Scraping, reading job descriptions, and scoring…"):
                jobs, board_status = run_search(boards, query, location,
                                                date_posted, job_type, int(pages))
            st.session_state["jobs"] = jobs

            # Per-board status line (honest about Cloudflare-blocked boards)
            icons = {"ok": "✅", "blocked": "🚫", "error": "⚠️", "empty": "∅"}
            labels = {"ok": lambda c: f"{c} jobs", "blocked": lambda c: "blocked (Cloudflare)",
                      "error": lambda c: "error", "empty": lambda c: "no results"}
            parts = [f"{icons[s['status']]} **{b}**: {labels[s['status']](s['count'])}"
                     for b, s in board_status.items()]
            st.caption("  ·  ".join(parts))

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
            prog.progress(1.0, text="Done.")
            prog.empty()

            st.subheader("Tailored Resumes")
            for r in results:
                if r.get("blocked"):
                    st.error(f"⛔ **{r['company']} — {r['role']}**: skipped — "
                             f"no sponsorship for F1 ({r['block_reason']}). "
                             "Verify in the posting before ruling it out.")
                elif r["ok"]:
                    with st.expander(f"✅ {r['company']} — {r['role']}  ·  {r['family']}"):
                        st.write(f"**Role family detected:** {r['family']}")
                        st.write(f"**Saved to:** `{r['out_dir']}`")
                        if r.get("exp_warning"):
                            st.warning("⚠️ " + r["exp_warning"])
                        if r["warnings"]:
                            st.caption("Content trimmed to fit 1 page: "
                                       + "; ".join(r["warnings"]))
                        if r.get("pdf_error"):
                            st.warning("PDF not created — " + r["pdf_error"]
                                       + " (the DOCX is still saved).")

                        dl1, dl2 = st.columns(2)
                        with dl1:
                            with open(r["resume_path"], "rb") as f:
                                st.download_button(
                                    "⬇️ DOCX",
                                    data=f, file_name=Path(r["resume_path"]).name,
                                    mime="application/vnd.openxmlformats-officedocument."
                                         "wordprocessingml.document",
                                    key=f"dl_docx_{r['resume_path']}")
                        with dl2:
                            if r.get("pdf_path"):
                                with open(r["pdf_path"], "rb") as f:
                                    st.download_button(
                                        "⬇️ PDF",
                                        data=f, file_name=Path(r["pdf_path"]).name,
                                        mime="application/pdf",
                                        key=f"dl_pdf_{r['pdf_path']}")

                        if st.button("Add to Tracker", key=f"trk_{r['resume_path']}"):
                            rows = load_tracker()
                            rows.append({
                                "company": r["company"], "role": r["role"],
                                "location": "", "url": "",
                                "date_added": str(date.today()),
                                "status": "To Apply",
                                "notes": f"Resume tailored ({r['family']})",
                            })
                            save_tracker(rows)
                            st.success("Added to tracker.")
                else:
                    st.error(f"❌ {r['company']} — {r['role']}: {r['error']}")

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRACKER
# ════════════════════════════════════════════════════════════════════════════
with tab_tracker:
    st.header("Application Tracker")
    rows = load_tracker()
    STATUSES = ["To Apply", "Applied", "Phone Screen", "Interview",
                "Final Round", "Offer", "Rejected"]

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
                rows.append({
                    "company": t_company, "role": t_role, "location": t_location,
                    "url": t_url, "date_added": str(date.today()),
                    "status": t_status, "notes": t_notes,
                })
                save_tracker(rows)
                st.success("Added.")
                st.rerun()

    if not rows:
        st.info("No applications tracked yet.")
    else:
        icons = {"To Apply": "🔵", "Applied": "🟡", "Phone Screen": "🟠",
                 "Interview": "🟣", "Final Round": "🔴", "Offer": "🟢", "Rejected": "⚫"}
        for i, row in enumerate(rows):
            icon = icons.get(row.get("status", ""), "⚪")
            with st.expander(f"{icon} {row['company']} — {row['role']}"):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.write(f"**Location:** {row.get('location', '')}")
                    st.write(f"**Added:** {row.get('date_added', '')}")
                    if row.get("url"):
                        st.markdown(f"[Job Posting]({row['url']})")
                with c2:
                    new_status = st.selectbox(
                        "Status", STATUSES,
                        index=STATUSES.index(row.get("status", "To Apply")),
                        key=f"status_{i}")
                    new_notes = st.text_input("Notes", value=row.get("notes", ""),
                                              key=f"notes_{i}")
                with c3:
                    if st.button("Save", key=f"save_{i}"):
                        rows[i]["status"] = new_status
                        rows[i]["notes"] = new_notes
                        save_tracker(rows)
                        st.success("Saved.")
                    if st.button("Remove", key=f"remove_{i}"):
                        rows.pop(i)
                        save_tracker(rows)
                        st.rerun()
