# Job Search Assistant — Local App

A local Streamlit UI + Word resume generator for the job application workflow.

## First-time setup

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

This installs the Python packages (streamlit, python-docx, lxml) and the scraper
dependencies (`bun install` in each `.agents/skills/*/cli`). Bun is only needed
for the job-board scrapers; the resume generator and UI work without it.

## Launch the app

```powershell
python -m streamlit run app.py
```

Opens at http://localhost:8501 with four tabs:

- **Search** — scrape LinkedIn / Indeed / Glassdoor by role + location
- **Analyze JD** — paste a job description for role-family detection, skills match, and tailoring notes
- **Resume** — edit summary/coursework/skills and download a tailored `.docx`
- **Tracker** — track application status (saved to `output/tracker.json`)

## Resume engine

`resume_engine/` generates Word resumes that match the exact table-based format
(blue section headers, two-column job rows, 10pt Calibri, 1 page).

- `models.py` — data classes (`ResumeData`, `ExperienceEntry`, etc.)
- `content_rules.py` — 1-page limits (bullet counts, char caps) enforced before generation
- `generator.py` — builds the `.docx` from `base_template.docx`

To tweak how much fits on the page, edit the limits at the top of
`content_rules.py`.

## Generated files

Everything lands in `output/` (git-ignored):
- `resume_<Company>_<Role>.docx`
- `tracker.json`
