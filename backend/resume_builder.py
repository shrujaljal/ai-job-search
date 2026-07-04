"""
Config-driven résumé assembly.

Turns the user's facts (`profile.json`) plus per-family tailoring
(`resume_content.json`) into a normalized render context for a detected role
family, applying one-page content limits. The context is template-agnostic —
it feeds the DOCX renderer (default template or a user-uploaded one).

This replaces V1's hardcoded `resume_engine/profile.py`: nothing here is
specific to any person; everything comes from config.
"""

from __future__ import annotations

# Default one-page limits (calibrated on the default template). Overridable via
# resume_content["limits"].
DEFAULT_LIMITS = {
    "max_summary_chars": 530,
    "max_experiences": 4,
    "max_bullets_per_exp": [3, 3, 3, 1],   # newest → oldest
    "max_bullets_per_exp_default": 2,
    "max_chars_per_bullet": 220,
    "max_projects": 1,
    "max_project_bullets": 2,
    "max_leadership": 1,
    "max_leadership_bullets": 1,
    "max_skill_categories": 4,
    "max_chars_per_skill_line": 160,
    "max_coursework_chars": 100,
}


def _truncate(text: str, max_chars: int) -> str:
    if not text or len(text) <= max_chars:
        return text or ""
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(",;")


def _family_cfg(content: dict, family: str) -> dict:
    fams = content.get("families", {})
    if family in fams:
        return fams[family]
    default = content.get("default_family", "General Business")
    return fams.get(default, {})


def build_context(profile: dict, content: dict, family: str) -> dict:
    """
    Assemble a tailored, one-page render context.

    Returns a dict with: identity, summary, coursework, experiences, education,
    projects, leadership, skills, family, warnings.
    """
    limits = {**DEFAULT_LIMITS, **content.get("limits", {})}
    fam = _family_cfg(content, family)
    warnings: list[str] = []

    # ── Summary (family-tailored, else profile default) ─────────────────────
    summary = fam.get("summary") or profile.get("summary", "")
    if len(summary) > limits["max_summary_chars"]:
        summary = _truncate(summary, limits["max_summary_chars"])
        warnings.append("Summary truncated to fit one page.")

    # ── Experience (all facts; trimmed for one page) ────────────────────────
    experiences = []
    exp_list = profile.get("experience", [])
    if len(exp_list) > limits["max_experiences"]:
        warnings.append(
            f"Showed {limits['max_experiences']} of {len(exp_list)} experiences.")
        exp_list = exp_list[: limits["max_experiences"]]
    per_exp = limits["max_bullets_per_exp"]
    for i, e in enumerate(exp_list):
        cap = per_exp[i] if i < len(per_exp) else limits["max_bullets_per_exp_default"]
        bullets = [b for b in e.get("bullets", []) if b.strip()][:cap]
        bullets = [_truncate(b, limits["max_chars_per_bullet"]) for b in bullets]
        experiences.append({
            "company": e.get("company", ""), "role": e.get("role", ""),
            "date": _date_range(e), "bullets": bullets,
        })

    # ── Education ───────────────────────────────────────────────────────────
    education = []
    for ed in profile.get("education", []):
        education.append({
            "degree": ed.get("degree", ""), "field": ed.get("field", ""),
            "institution": ed.get("institution", ""),
            "location": ed.get("location", ""),
            "graduation": ed.get("graduation", ""), "gpa": ed.get("gpa", ""),
            "honors": ed.get("honors", []),
        })
    coursework = _truncate(fam.get("coursework", ""), limits["max_coursework_chars"])

    # ── Projects (family selection) ─────────────────────────────────────────
    wanted_titles = fam.get("projects", [])
    all_projects = profile.get("projects", [])
    if wanted_titles:
        chosen = [p for p in all_projects if p.get("title") in wanted_titles]
    else:
        chosen = [p for p in all_projects if family in p.get("families", [])]
    chosen = chosen[: limits["max_projects"]]
    projects = [{
        "title": p.get("title", ""),
        "bullets": [b for b in p.get("bullets", []) if b.strip()][: limits["max_project_bullets"]],
    } for p in chosen]

    # ── Leadership ──────────────────────────────────────────────────────────
    leadership = []
    for ld in profile.get("leadership", [])[: limits["max_leadership"]]:
        leadership.append({
            "organization": ld.get("organization", ""), "role": ld.get("role", ""),
            "bullets": [b for b in ld.get("bullets", []) if b.strip()][: limits["max_leadership_bullets"]],
        })

    # ── Skills (per-family grouping, else profile master) ───────────────────
    skill_cats = fam.get("skill_categories") or profile.get("skills", [])
    skills = []
    for cat in skill_cats[: limits["max_skill_categories"]]:
        items = cat.get("items", "")
        if isinstance(items, list):
            items = ", ".join(items)
        skills.append({
            "name": cat.get("name") or cat.get("category", ""),
            "items": _truncate(items, limits["max_chars_per_skill_line"]),
        })

    return {
        "identity": profile.get("identity", {}),
        "summary": summary,
        "coursework": coursework,
        "experiences": experiences,
        "education": education,
        "projects": projects,
        "leadership": leadership,
        "skills": skills,
        "family": family,
        "warnings": warnings,
    }


def _date_range(exp: dict) -> str:
    if exp.get("date"):
        return exp["date"]
    start, end = exp.get("start", ""), exp.get("end", "")
    return f"{start} – {end}".strip(" –") if (start or end) else ""
