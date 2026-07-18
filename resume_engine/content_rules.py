"""
Content rules to keep the resume at exactly 1 page.
All limits are derived from the base template layout (A4, 0.5" margins, 10pt Calibri).
"""

from dataclasses import replace
from .models import ResumeData

# Hard limits (calibrated against the base_template.docx which fits exactly 1 page)
MAX_SUMMARY_CHARS = 530        # ~3–4 sentences; original is ~500 chars
MAX_EXPERIENCES = 5
MAX_BULLETS_PER_EXP = {0: 4, 1: 3, 2: 4, 3: 4, 4: 1}
MAX_CHARS_PER_BULLET = 250     # longest approved template bullet is 242 chars
MAX_PROJECT_ENTRIES = 1
MAX_PROJECT_BULLETS = 2
MAX_LEADERSHIP_BULLETS = 1
MAX_SKILL_CATEGORIES = 4
MAX_CHARS_PER_SKILL_LINE = 160
MAX_COURSEWORK_CHARS = 100


def enforce(data: ResumeData) -> tuple[ResumeData, list[str]]:
    """
    Enforce 1-page content limits. Returns (cleaned_data, list_of_warnings).
    Mutates data in place and also returns it.
    """
    warnings = []

    # Summary
    if len(data.summary) > MAX_SUMMARY_CHARS:
        data.summary = _truncate(data.summary, MAX_SUMMARY_CHARS)
        warnings.append(f"Summary truncated to {MAX_SUMMARY_CHARS} chars.")

    # Experiences
    if len(data.experiences) > MAX_EXPERIENCES:
        warnings.append(f"Trimmed experiences from {len(data.experiences)} to {MAX_EXPERIENCES}.")
        data.experiences = data.experiences[:MAX_EXPERIENCES]

    for i, exp in enumerate(data.experiences):
        max_b = MAX_BULLETS_PER_EXP.get(i, 2)
        if len(exp.bullets) > max_b:
            warnings.append(f"{exp.company}: trimmed bullets from {len(exp.bullets)} to {max_b}.")
            exp.bullets = exp.bullets[:max_b]
        for j, b in enumerate(exp.bullets):
            if len(b) > MAX_CHARS_PER_BULLET:
                exp.bullets[j] = _truncate(b, MAX_CHARS_PER_BULLET)
                warnings.append(f"Bullet in {exp.company} truncated.")

    # Projects
    if len(data.projects) > MAX_PROJECT_ENTRIES:
        data.projects = data.projects[:MAX_PROJECT_ENTRIES]
        warnings.append(f"Trimmed to {MAX_PROJECT_ENTRIES} project entry.")
    for proj in data.projects:
        if len(proj.bullets) > MAX_PROJECT_BULLETS:
            proj.bullets = proj.bullets[:MAX_PROJECT_BULLETS]

    # Leadership
    if len(data.leadership_bullets) > MAX_LEADERSHIP_BULLETS:
        data.leadership_bullets = data.leadership_bullets[:MAX_LEADERSHIP_BULLETS]
        warnings.append(f"Trimmed leadership to {MAX_LEADERSHIP_BULLETS} bullet.")

    # Skills
    if len(data.skills) > MAX_SKILL_CATEGORIES:
        data.skills = data.skills[:MAX_SKILL_CATEGORIES]
        warnings.append(f"Trimmed skill categories to {MAX_SKILL_CATEGORIES}.")
    for cat in data.skills:
        if len(cat.skills) > MAX_CHARS_PER_SKILL_LINE:
            cat.skills = _truncate(cat.skills, MAX_CHARS_PER_SKILL_LINE)

    # Coursework
    if len(data.coursework) > MAX_COURSEWORK_CHARS:
        data.coursework = _truncate(data.coursework, MAX_COURSEWORK_CHARS)

    return data, warnings


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(",;")
