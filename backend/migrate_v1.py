"""
One-off migration: port Shrujal's V1 résumé data (resume_engine/profile.py) into
the V2 config store (data/profile.json + data/resume_content.json).

Run once:  python backend/migrate_v1.py
Writes personal data into data/ (git-ignored). The shipped defaults stay generic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

V2_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2_ROOT))

from resume_engine.profile import (  # noqa: E402  (V1 data source)
    _experiences, _FAMILY_CONFIG, LEADERSHIP,
)

DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(exist_ok=True)


def build_profile() -> dict:
    experience = [
        {"company": e.company, "role": e.role, "date": e.date, "bullets": list(e.bullets)}
        for e in _experiences()
    ]

    # Which project each family uses -> tag projects with the families they suit.
    proj_families: dict[str, list[str]] = {}
    for family, (_summary, project, _skills, _course) in _FAMILY_CONFIG.items():
        proj_families.setdefault(project.title, [])
        if family not in proj_families[project.title]:
            proj_families[project.title].append(family)

    projects = []
    seen = set()
    for _f, (_s, project, _sk, _c) in _FAMILY_CONFIG.items():
        if project.title in seen:
            continue
        seen.add(project.title)
        projects.append({
            "title": project.title,
            "bullets": list(project.bullets),
            "families": proj_families.get(project.title, []),
        })

    return {
        "identity": {
            "name": "Shrujal Agarwal",
            "email": "shrujalag.gms@gmail.com",
            "phone": "(951)-347-5278",
            "location": "California, USA",
            "links": [{"label": "LinkedIn",
                       "url": "https://www.linkedin.com/in/shrujalagarwal/"}],
            "work_authorization": "Requires H-1B sponsorship",
            "needs_sponsorship": True,
        },
        "summary": _FAMILY_CONFIG["General Business"][0],
        "education": [
            {"degree": "Master of Business Administration (MBA)", "field": "",
             "institution": "University of California, Riverside", "location": "",
             "graduation": "June 2026", "gpa": "3.8",
             "honors": ["Beta Gamma Sigma Award", "2024 Case Competition Winner"]},
            {"degree": "Bachelor of Technology", "field": "Biotechnology",
             "institution": "Vellore Institute of Technology", "location": "Vellore, India",
             "graduation": "Aug 2023", "gpa": "", "honors": []},
        ],
        "experience": experience,
        "projects": projects,
        "leadership": [
            {"organization": "UCR GSM Student Association", "role": "Marketing Lead",
             "bullets": list(LEADERSHIP)},
        ],
        "skills": [
            {"name": cat.name, "items": cat.skills}
            for cat in _FAMILY_CONFIG["General Business"][2]()
        ],
    }


def build_resume_content() -> dict:
    families = {}
    for family, (summary, project, skills_fn, coursework) in _FAMILY_CONFIG.items():
        families[family] = {
            "summary": summary,
            "coursework": coursework,
            "skill_categories": [{"name": c.name, "items": c.skills} for c in skills_fn()],
            "projects": [project.title],
        }
    return {"default_family": "General Business", "families": families}


if __name__ == "__main__":
    (DATA / "profile.json").write_text(
        json.dumps(build_profile(), indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA / "resume_content.json").write_text(
        json.dumps(build_resume_content(), indent=2, ensure_ascii=False), encoding="utf-8")
    print("Wrote data/profile.json and data/resume_content.json")
