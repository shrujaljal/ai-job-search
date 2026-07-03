"""
Job Search Assistant — local Streamlit UI.

Tabs:
  1. Search    — scrape LinkedIn / Indeed / Glassdoor
  2. Analyze   — paste a JD, get fit score + tailoring notes
  3. Resume    — generate & download tailored .docx
  4. Tracker   — track application status
"""

import json
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

from resume_engine import (
    ResumeData, ExperienceEntry, ProjectEntry, SkillCategory, generate
)

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
CLI_ROOTS = {
    "LinkedIn":  ROOT / ".agents/skills/linkedin-search/cli",
    "Indeed":    ROOT / ".agents/skills/indeed-search/cli",
    "Glassdoor": ROOT / ".agents/skills/glassdoor-search/cli",
}
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

# ── Scraper helper ────────────────────────────────────────────────────────────
def run_scraper(board: str, query: str, location: str,
                date_posted: str, job_type: str, limit: int) -> list[dict]:
    cli_dir = CLI_ROOTS[board]
    cmd = ["bun", "run", "src/cli.ts", "search",
           "--query", query,
           "--format", "json",
           "--limit", str(limit)]
    if location:
        cmd += ["--location", location]
    if date_posted != "any":
        cmd += ["--datePosted", date_posted]
    if job_type != "any":
        cmd += ["--jobType", job_type]

    try:
        result = subprocess.run(
            cmd, cwd=str(cli_dir), capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            st.error(f"Scraper error: {result.stderr[:400]}")
            return []
        raw = result.stdout.strip()
        if not raw:
            return []
        data = json.loads(raw)
        # Normalise: some CLIs return {"jobs": [...]} others return [...]
        if isinstance(data, dict) and "jobs" in data:
            return data["jobs"]
        if isinstance(data, list):
            return data
        return []
    except subprocess.TimeoutExpired:
        st.error("Scraper timed out (30s). Try a narrower search.")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Could not parse scraper output: {e}")
        return []

# ── Default resume data (used as base for all tailoring) ─────────────────────
def default_resume() -> ResumeData:
    return ResumeData(
        summary=(
            "MBA graduate from UC Riverside (GPA 3.8) with 3+ years of experience across "
            "strategy, analytics, and operations within Fortune 500 organizations and startup "
            "environments. Skilled at translating ambiguous business problems into fact-based "
            "analysis, SQL-driven reporting, and executive-ready recommendations. Proven track "
            "record partnering cross-functionally with finance, operations, and marketing "
            "stakeholders to standardize KPIs and drive measurable business performance."
        ),
        experiences=[
            ExperienceEntry(
                company="BB Wellness", role="Analyst Intern",
                date="Feb 2025 – Sep 2025",
                bullets=[
                    "Defined go-to-market problem scope through market segmentation and "
                    "competitive benchmarking across 6 competitors, translating research into "
                    "fact-based product positioning recommendations for leadership.",
                    "Built SQL-driven KPI dashboards spanning 4 channels, establishing a "
                    "centralized reporting framework that surfaced performance gaps and enabled "
                    "leadership to prioritize strategic initiatives.",
                    "Developed hypothesis-driven business cases and strategic roadmaps, "
                    "partnering with marketing, content, and operations stakeholders to align "
                    "10+ cross-functional initiatives against weekly OKRs.",
                ],
            ),
            ExperienceEntry(
                company="Thomson Reuters", role="Analyst – Global Operations",
                date="Oct 2023 – Jun 2024",
                bullets=[
                    "Built 15+ SQL and Excel reporting frameworks adopted across 3 global "
                    "business units, reducing manual reporting effort ~30% and improving "
                    "executive visibility into business performance.",
                    "Partnered with finance, procurement, and operations stakeholders across "
                    "4 regions to standardize KPIs and support Quarterly Business Reviews, "
                    "budgeting, and annual business planning.",
                    "Prepared executive summaries translating complex, multi-source analyses "
                    "into structured business recommendations for senior leadership.",
                ],
            ),
            ExperienceEntry(
                company="Goldman Sachs", role="STEM Intern – Asset & Wealth Management",
                date="Feb 2023 – Jun 2023",
                bullets=[
                    "Built Qlik Sense dashboards consolidating 5+ operational data sources, "
                    "improving executive visibility into business performance across AWM.",
                    "Identified process gaps through workflow analysis using Excel, JIRA, and "
                    "Qlik Sense, strengthening compliance reporting and operational controls.",
                    "Developed operational trackers monitoring hundreds of client commitments, "
                    "improving workflow transparency and cross-team reporting consistency.",
                ],
            ),
            ExperienceEntry(
                company="Beyond Key", role="Data Analyst Intern",
                date="Jun 2022 – Aug 2022",
                bullets=[
                    "Analyzed business datasets using SQL, Python, and Excel; built Tableau "
                    "dashboards enabling real-time performance monitoring for healthcare clients.",
                ],
            ),
        ],
        coursework="Business Analytics & Reporting, Operations Management, Quantitative Analysis",
        projects=[
            ProjectEntry(
                title="Hyundai Rotem Operations Consulting Project",
                bullets=[
                    "Led a strategy consulting engagement analyzing manufacturing operations, "
                    "inventory flows, and capacity constraints through process mapping and "
                    "stakeholder interviews.",
                    "Developed phased operational roadmaps, KPI frameworks, and executive "
                    "recommendations improving scalability and operational efficiency.",
                ],
            )
        ],
        leadership_bullets=[
            "Launched the school's first newsletter and podcast, designing editorial strategy, "
            "distribution workflows, and performance dashboards that improved audience engagement.",
        ],
        skills=[
            SkillCategory("Business Strategy",
                "Business Strategy, Strategic Planning, Annual Business Planning, "
                "Business Case Development, Market Research, Stakeholder Management"),
            SkillCategory("Analytics & Reporting",
                "SQL, Python, Advanced Excel (Pivot Tables, XLOOKUP, Power Query), "
                "Tableau, Qlik Sense, KPI Reporting, Data Visualization"),
            SkillCategory("Operations & Execution",
                "Cross-Functional Leadership, Program Management, Process Improvement, "
                "Operational Excellence, OKR Design & Tracking, Change Management"),
            SkillCategory("Tools & AI",
                "ChatGPT, Claude, Gemini, Excel Copilot, n8n, Salesforce, "
                "SAP Ariba, JIRA, HubSpot, PowerPoint"),
        ],
    )

# ════════════════════════════════════════════════════════════════════════════
# Page config
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Job Search Assistant",
    page_icon="💼",
    layout="wide",
)

st.title("💼 Job Search Assistant")
st.caption("Shrujal Agarwal — local workflow tool")

tab_search, tab_analyze, tab_resume, tab_tracker = st.tabs(
    ["🔍 Search", "📋 Analyze JD", "📄 Resume", "📊 Tracker"]
)

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — SEARCH
# ════════════════════════════════════════════════════════════════════════════
with tab_search:
    st.header("Job Board Search")

    col1, col2 = st.columns(2)
    with col1:
        query = st.text_input("Role / Keywords", placeholder="Strategy & Operations Analyst")
        location = st.text_input("Location", placeholder="California, USA")
    with col2:
        board = st.selectbox("Job Board", ["LinkedIn", "Indeed", "Glassdoor"])
        date_posted = st.selectbox("Date Posted", ["any", "day", "week", "month"],
                                   format_func=lambda x: {"any": "Any time", "day": "Past 24h",
                                                           "week": "Past week",
                                                           "month": "Past month"}[x])
    col3, col4 = st.columns(2)
    with col3:
        job_type = st.selectbox("Job Type", ["any", "fulltime", "internship", "contract"],
                                format_func=lambda x: x.title() if x != "any" else "Any")
    with col4:
        limit = st.number_input("Max results", min_value=5, max_value=50, value=15)

    if st.button("Search Jobs", type="primary"):
        if not query:
            st.warning("Enter a role or keywords to search.")
        else:
            with st.spinner(f"Searching {board}…"):
                jobs = run_scraper(board, query, location, date_posted, job_type, int(limit))

            if jobs:
                st.success(f"Found {len(jobs)} results from {board}.")
                st.session_state["search_results"] = jobs
                st.session_state["search_board"] = board
            else:
                st.info("No results returned. Try different keywords or board.")

    if "search_results" in st.session_state:
        jobs = st.session_state["search_results"]
        board_label = st.session_state.get("search_board", "")
        st.subheader(f"Results — {board_label}")

        for i, job in enumerate(jobs):
            title = job.get("title") or job.get("jobTitle") or "Untitled"
            company = job.get("company") or job.get("companyName") or ""
            loc = job.get("location") or ""
            url = job.get("url") or job.get("jobUrl") or job.get("link") or "#"
            posted = job.get("postedAt") or job.get("datePosted") or ""

            with st.expander(f"{title} — {company}"):
                cols = st.columns([3, 1])
                with cols[0]:
                    st.write(f"**Location:** {loc}")
                    if posted:
                        st.write(f"**Posted:** {posted}")
                    if url and url != "#":
                        st.markdown(f"[Open Job Posting]({url})")
                with cols[1]:
                    if st.button("Add to Tracker", key=f"add_{i}"):
                        rows = load_tracker()
                        rows.append({
                            "company": company,
                            "role": title,
                            "location": loc,
                            "url": url,
                            "date_added": str(date.today()),
                            "status": "To Apply",
                            "notes": "",
                        })
                        save_tracker(rows)
                        st.success("Added to tracker.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANALYZE JD
# ════════════════════════════════════════════════════════════════════════════
with tab_analyze:
    st.header("Analyze a Job Description")
    st.caption("Paste the full JD. The tool will identify role family, fit, and tailoring notes.")

    jd_text = st.text_area("Job Description", height=300,
                            placeholder="Paste the full job description here…")

    if st.button("Analyze", type="primary"):
        if not jd_text.strip():
            st.warning("Paste a job description first.")
        else:
            # Rule-based analysis (no API call needed)
            jd_lower = jd_text.lower()

            # Role family detection
            role_keywords = {
                "Strategy & Operations": ["strategy", "operations", "s&o", "planning", "intelligence"],
                "Business Analyst":      ["business analyst", "data analyst", "reporting", "dashboards", "sql"],
                "Program Management":    ["program manager", "project manager", "pmo", "roadmap"],
                "Marketing Operations":  ["marketing operations", "campaign", "go-to-market", "gtm"],
                "Product Marketing":     ["product marketing", "positioning", "messaging", "pmm"],
                "Consulting":            ["consulting", "consultant", "advisory", "client engagement"],
            }
            scores = {family: sum(1 for kw in kws if kw in jd_lower)
                      for family, kws in role_keywords.items()}
            best_family = max(scores, key=scores.get)

            # Skills match
            candidate_skills = [
                "sql", "excel", "tableau", "python", "qlik", "sap ariba", "jira",
                "kpi", "reporting", "dashboard", "operations", "strategy", "stakeholder",
                "cross-functional", "process improvement", "market research",
                "competitive analysis", "program management", "business analytics",
                "forecasting", "budgeting", "okr", "powerpoint"
            ]
            matched = [s for s in candidate_skills if s in jd_lower]
            total_skills = len(candidate_skills)
            fit_pct = round(len(matched) / total_skills * 100)

            # Visa / sponsorship flag
            no_sponsor_phrases = ["must be authorized", "no sponsorship", "citizens only",
                                   "permanent resident", "green card", "us citizen"]
            visa_risk = any(p in jd_lower for p in no_sponsor_phrases)

            # Output
            st.subheader("Analysis")
            c1, c2, c3 = st.columns(3)
            c1.metric("Role Family", best_family)
            c2.metric("Skills Match", f"{fit_pct}%")
            c3.metric("Visa Risk", "⚠️ High" if visa_risk else "✅ Low")

            st.subheader("Matched Skills")
            if matched:
                st.write(", ".join(f"`{s}`" for s in matched))
            else:
                st.write("No direct skill matches found.")

            st.subheader("Tailoring Notes")
            family_notes = {
                "Strategy & Operations": (
                    "Lead with Thomson Reuters and Goldman Sachs. "
                    "Emphasize KPI reporting, cross-functional execution, and business planning. "
                    "Include Hyundai Rotem project. Summary: strategy + analytics + operations."
                ),
                "Business Analyst": (
                    "Lead with Thomson Reuters + Beyond Key. "
                    "Emphasize SQL, Tableau, dashboards, trend analysis. "
                    "Include Hyundai project for consulting/BA framing."
                ),
                "Program Management": (
                    "Lead with BB Wellness + Thomson Reuters. "
                    "Emphasize stakeholder coordination, timelines, deliverables, OKRs. "
                    "Include Professional Development Lead in leadership section."
                ),
                "Marketing Operations": (
                    "Lead with BB Wellness. "
                    "Emphasize campaign reporting, competitive analysis, content planning. "
                    "Include LinkedIn Ads or Value Proposition Canvas project."
                ),
                "Product Marketing": (
                    "Lead with BB Wellness. "
                    "Emphasize customer insights, competitive analysis, go-to-market. "
                    "Include Value Proposition Canvas and LinkedIn Ads projects."
                ),
                "Consulting": (
                    "Lead with Hyundai Rotem project upfront. "
                    "Emphasize structured problem solving, stakeholder interviews, executive presentations. "
                    "Include Thomson Reuters + Goldman for operational credibility."
                ),
            }
            st.info(family_notes.get(best_family, "Review the role requirements and align with closest experience."))

            if visa_risk:
                st.warning(
                    "This JD may not sponsor visas. Verify before applying — "
                    "look for 'H-1B' or 'work authorization' language."
                )

            st.session_state["last_jd"] = jd_text
            st.session_state["last_family"] = best_family

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — RESUME
# ════════════════════════════════════════════════════════════════════════════
with tab_resume:
    st.header("Generate Resume")

    company_name = st.text_input("Target Company (used in filename)",
                                 placeholder="Google")
    role_name = st.text_input("Target Role (used in filename)",
                               placeholder="Strategy and Operations Associate")

    st.subheader("Professional Summary")
    summary_text = st.text_area(
        "Summary (aim for 3–4 sentences, ~430–530 chars)",
        value=default_resume().summary,
        height=120,
    )
    st.caption(f"{len(summary_text)} chars")

    st.subheader("Relevant Coursework")
    coursework = st.text_input(
        "Coursework (comma-separated, change per role)",
        value="Business Analytics & Reporting, Operations Management, Quantitative Analysis",
    )

    st.subheader("Skills")
    skill_defaults = default_resume().skills
    skill_rows = []
    for i, cat in enumerate(skill_defaults):
        c1, c2 = st.columns([1, 3])
        with c1:
            name = st.text_input(f"Category {i+1}", value=cat.name, key=f"sname_{i}")
        with c2:
            skills = st.text_input(f"Skills {i+1}", value=cat.skills, key=f"sskills_{i}")
        skill_rows.append(SkillCategory(name, skills))

    if st.button("Generate Resume", type="primary"):
        if not company_name or not role_name:
            st.warning("Enter company and role name first.")
        else:
            data = default_resume()
            data.summary = summary_text
            data.coursework = coursework
            data.skills = skill_rows

            slug = f"{company_name.replace(' ', '_')}_{role_name.replace(' ', '_')}"
            out_path = str(OUTPUT_DIR / f"resume_{slug}.docx")

            with st.spinner("Generating…"):
                path, warnings = generate(data, out_path)

            st.success(f"Resume generated: `{Path(path).name}`")

            if warnings:
                with st.expander("Content warnings (auto-trimmed to fit 1 page)"):
                    for w in warnings:
                        st.write(f"• {w}")

            with open(path, "rb") as f:
                st.download_button(
                    label="⬇️ Download .docx",
                    data=f,
                    file_name=Path(path).name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — TRACKER
# ════════════════════════════════════════════════════════════════════════════
with tab_tracker:
    st.header("Application Tracker")

    rows = load_tracker()

    # Add new entry manually
    with st.expander("+ Add Application"):
        nc1, nc2 = st.columns(2)
        with nc1:
            t_company = st.text_input("Company", key="t_company")
            t_role = st.text_input("Role", key="t_role")
            t_location = st.text_input("Location", key="t_location")
        with nc2:
            t_url = st.text_input("Job URL", key="t_url")
            t_status = st.selectbox("Status", ["To Apply", "Applied", "Phone Screen",
                                               "Interview", "Final Round", "Offer", "Rejected"],
                                    key="t_status")
            t_notes = st.text_input("Notes", key="t_notes")
        if st.button("Add Entry"):
            if t_company and t_role:
                rows.append({
                    "company": t_company,
                    "role": t_role,
                    "location": t_location,
                    "url": t_url,
                    "date_added": str(date.today()),
                    "status": t_status,
                    "notes": t_notes,
                })
                save_tracker(rows)
                st.success("Added.")
                st.rerun()

    if not rows:
        st.info("No applications tracked yet. Add them from the Search tab or manually above.")
    else:
        status_colors = {
            "To Apply": "🔵", "Applied": "🟡", "Phone Screen": "🟠",
            "Interview": "🟣", "Final Round": "🔴", "Offer": "🟢", "Rejected": "⚫",
        }
        for i, row in enumerate(rows):
            icon = status_colors.get(row.get("status", ""), "⚪")
            label = f"{icon} {row['company']} — {row['role']}"
            with st.expander(label):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.write(f"**Location:** {row.get('location', '')}")
                    st.write(f"**Added:** {row.get('date_added', '')}")
                    if row.get("url"):
                        st.markdown(f"[Job Posting]({row['url']})")
                with c2:
                    new_status = st.selectbox(
                        "Status", ["To Apply", "Applied", "Phone Screen",
                                   "Interview", "Final Round", "Offer", "Rejected"],
                        index=["To Apply", "Applied", "Phone Screen",
                               "Interview", "Final Round", "Offer", "Rejected"].index(
                                   row.get("status", "To Apply")),
                        key=f"status_{i}",
                    )
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
