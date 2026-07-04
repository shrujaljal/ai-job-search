# Job Application Agent

A local, single-user job-search assistant for **Shrujal Agarwal**. It finds relevant
roles, scores how well each one fits her profile, generates one-page tailored resumes
(DOCX + PDF), and tracks the whole application pipeline — all from one desktop app.

Everything runs **locally on your machine**. No accounts, no cloud, no data leaves
your computer.

> Built with [Claude Code](https://claude.com/claude-code). This repo began as a fork
> of a Claude Code job-application framework (see *Acknowledgements*) and grew into a
> standalone Streamlit app. Curious how it was built, prompt by prompt? Read
> **[BUILD_FROM_SCRATCH.md](BUILD_FROM_SCRATCH.md)**.

---

## What it does

- **📊 Dashboard** — the landing page. Personalized encouragement, a "Today's Plan"
  goal you can set and complete, and visuals of your progress (metrics, a pipeline
  chart, applications over time).
- **🗂️ Tracker** — an editable table of every application, with status, notes, and
  CSV export. Saved to disk so it persists across restarts.
- **🔍 Search & Tailor** — search LinkedIn (and Indeed/Glassdoor when reachable) for
  several target roles at once. Each posting's full description is read and scored
  against the candidate profile, then flagged for experience level and visa
  sponsorship. Queue the good ones and generate tailored resumes in one click.
- **📝 Paste JD** — found a role elsewhere? Paste the description (or a link) and it
  produces a tailored resume the same way.

Generated resumes are saved to:

```
C:\Users\shruj\Downloads\2026\<Company>\<Role>\
    <Role>.docx
    Shrujal Agarwal.pdf
    job_description.txt
```

---

## Quick start

### First time (one-time setup)

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

This creates an isolated Python environment (`.venv`), installs all dependencies,
installs the job-board scraper packages, generates the app icon, and puts a
**"Job application agent"** shortcut on your Desktop and in the Start Menu.

> Requires **Python 3** and **[Bun](https://bun.sh)** (for the scrapers) installed on
> the machine. Microsoft Word is used to produce the PDF.

### Every day after that

**Double-click the "Job application agent" icon** on your Desktop. A console window
opens (that's the server — keep it open) and your browser loads the app at
`http://localhost:8501`.

To stop the app, close that console window.

> ⚠️ Open the app in a **real browser** (Chrome/Edge/Firefox), not an embedded
> preview pane — sandboxed previews block the external job links.

---

## How it works (the moving parts)

| File / folder | Role |
|---------------|------|
| `app.py` | The Streamlit UI — all four tabs and the workflow glue. |
| `fit.py` | Scores a job 0–100 against the profile: role family, target companies, location, seniority, years-of-experience, and sponsorship / ITAR / citizenship blockers. |
| `tailoring.py` | Fetches a job's full description, detects the role family, and generates the tailored DOCX + PDF into the output folder. |
| `resume_engine/` | Builds the Word résumé from structured data. `profile.py` holds the base résumé and per-role-family variants; `generator.py` writes the DOCX; `content_rules.py` keeps it to one page. |
| `.agents/skills/*/cli` | The TypeScript (Bun) scrapers for LinkedIn, Indeed, Glassdoor. |
| `setup.ps1` | One-command environment setup + shortcut creation. |
| `Job Application Agent.bat` | The double-click launcher (runs the app from `.venv`). |
| `assets/` | Icon generator and desktop/Start-Menu shortcut script. |
| `CLAUDE.md` | The candidate profile and the rules the résumé tailoring follows. |

The tailoring is **rule-based**, not AI-generated: it selects the right pre-written
summary, skills, and project block for the detected role family. Every line stays
truthful to the candidate's real experience.

---

## Data & privacy

- **Application tracker:** `output/tracker.json`
- **Today's plan:** `output/daily_plan.json`
- **Generated resumes:** `Downloads/2026/…`

The entire `output/` folder is git-ignored, so personal data is never committed.

---

## Design choices worth knowing

- **Scoring reads the real JD**, not just the title — so "5+ years required" or
  "must be a U.S. citizen" roles are caught before you waste effort on them.
- **Sponsorship-aware:** roles that block visa sponsorship are flagged or skipped,
  because the candidate is an F1 student who needs sponsorship.
- **Indeed & Glassdoor** sit behind Cloudflare and often refuse automated requests;
  the app degrades gracefully and leans on LinkedIn (which exposes a guest API).
- **A virtual environment (`.venv`)** guarantees the launcher always uses the one
  Python that has the dependencies, avoiding "which Python?" errors on Windows.

---

## Acknowledgements

- Originally forked from a [Claude Code](https://claude.com/claude-code)
  job-application framework by [Mads Lorentzen](https://github.com/MadsLorentzen),
  which itself used job-search CLI skills by
  [Mikkel Krogholm](https://github.com/mikkelkrogsholm).
- The V1.0 Streamlit app, résumé engine, fit scoring, US job-board scrapers, and
  desktop launcher were built collaboratively with Claude Code.

## License

MIT

---

*Version 1.0*
