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

`resume_engine/` generates Word resumes that match the table-based DOCX format
in `new_template.docx` (blue section headers, two-column job rows, 10pt
Calibri, 1 page). The section order is professional summary, skills,
experience, education, and honors & awards.

- `models.py` — data classes (`ResumeData`, `ExperienceEntry`, etc.)
- `content_rules.py` — 1-page limits (bullet counts, char caps) enforced before generation
- `generator.py` — builds the `.docx` from `new_template.docx`
- `approved_catalog.json` — approved title variants, bullet banks, skills, and JD tags
- `custom_catalog.json` — optional user-added approved titles and skills
- `catalog.py` — deterministic JD matching and factual-safety checks

Replacing the DOCX alone is not enough for a layout change: `generator.py`
clears and rebuilds the template table programmatically, so section order,
spacing, and row structure live in code.

To tweak how much fits on the page, edit the limits at the top of
`content_rules.py`.

## Adding approved titles or skills

Add personal extensions to `custom_catalog.json`; do not edit the selector.
Custom titles are grouped by the exact employer name. Custom skills must use one
of the category names in `approved_catalog.json`. The loader rejects titles with
senior, lead, manager, director, principal, head, chief, or VP seniority.

The tool never learns skills directly from a JD. JD terms that are not in the
approved or custom catalog are shown as gaps and are not added to the resume.

## Generated files

Everything lands in `output/` (git-ignored):
- `resume_<Company>_<Role>.docx`
- `tracker.json`
