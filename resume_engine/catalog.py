"""Deterministic, evidence-constrained resume content selection."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import unicodedata

from .models import ExperienceEntry, SkillCategory


CATALOG_PATH = Path(__file__).with_name("approved_catalog.json")
CUSTOM_CATALOG_PATH = Path(__file__).with_name("custom_catalog.json")
MAX_SKILL_CATEGORIES = 4
MAX_SKILLS_PER_CATEGORY = 9
MAX_SKILL_LINE_CHARS = 160
MAX_INTERN_TITLES = 2

_SENIORITY_RE = re.compile(
    r"\b(senior|sr\.?|lead|manager|director|principal|head|chief|vice president|vp)\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = text.replace("&", " and ")
    return re.sub(r"[^a-z0-9+#.]+", " ", text).strip()


def _contains_phrase(normalized_text: str, phrase: str) -> bool:
    needle = _normalize(phrase)
    if not needle:
        return False
    return f" {needle} " in f" {normalized_text} "


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Catalog must contain a JSON object: {path}")
    return data


def load_catalog() -> dict:
    """Load the approved catalog and merge optional user-maintained additions."""
    catalog = _load_json(CATALOG_PATH)
    custom = _load_json(CUSTOM_CATALOG_PATH) if CUSTOM_CATALOG_PATH.exists() else {}

    title_options = custom.get("title_options", {})
    if not isinstance(title_options, dict):
        raise ValueError("custom_catalog.json title_options must be an object")

    experiences = {entry["company"]: entry for entry in catalog["experiences"]}
    for company, options in title_options.items():
        if company not in experiences:
            raise ValueError(f"Unknown company in custom title options: {company}")
        if not isinstance(options, list):
            raise ValueError(f"Custom title options for {company} must be a list")
        for option in options:
            title = option.get("text", "")
            if not title:
                raise ValueError(f"Custom title for {company} is missing text")
            if _SENIORITY_RE.search(title):
                raise ValueError(
                    f"Custom title for {company} uses unsupported seniority: {title}"
                )
            experiences[company]["titles"].append(option)

    valid_categories = {item["name"] for item in catalog["skill_categories"]}
    custom_skills = custom.get("skills", [])
    if not isinstance(custom_skills, list):
        raise ValueError("custom_catalog.json skills must be a list")
    for skill in custom_skills:
        if not skill.get("name") or not skill.get("category"):
            raise ValueError("Each custom skill needs name and category")
        if skill["category"] not in valid_categories:
            raise ValueError(f"Unknown custom skill category: {skill['category']}")
        skill.setdefault("aliases", [skill["name"]])
        skill.setdefault("tags", [])
        skill.setdefault("priority", 5)

    by_name = {skill["name"].casefold(): skill for skill in catalog["skills"]}
    for skill in custom_skills:
        by_name[skill["name"].casefold()] = skill
    catalog["skills"] = list(by_name.values())
    return catalog


def _matched_themes(catalog: dict, normalized_text: str) -> set[str]:
    return {
        theme
        for theme, phrases in catalog["keyword_groups"].items()
        if any(_contains_phrase(normalized_text, phrase) for phrase in phrases)
    }


def _select_title(
    experience: dict,
    themes: set[str],
    family_tags: set[str],
    has_job_context: bool,
) -> str:
    if not has_job_context:
        return next(
            (item["text"] for item in experience["titles"] if item.get("default")),
            experience["titles"][0]["text"],
        )

    scored = []
    for index, option in enumerate(experience["titles"]):
        tags = set(option.get("tags", []))
        score = (
            option.get("priority", 0)
            + 10 * len(tags & themes)
            + 5 * len(tags & family_tags)
        )
        scored.append((score, -index, option["text"]))
    return max(scored)[2]


def _select_bullets(
    experience: dict,
    themes: set[str],
    family_tags: set[str],
) -> list[str]:
    remaining = []
    for index, bullet in enumerate(experience["bullets"]):
        tags = set(bullet.get("tags", []))
        base_score = (
            bullet.get("priority", 0)
            + 9 * len(tags & themes)
            + 4 * len(tags & family_tags)
        )
        remaining.append({
            "index": index,
            "text": bullet["text"],
            "tags": tags,
            "score": base_score,
        })

    selected = []
    covered = set()
    limit = experience["bullet_limit"]
    while remaining and len(selected) < limit:
        best = max(
            remaining,
            key=lambda item: (
                item["score"] + 3 * len((item["tags"] & themes) - covered),
                -item["index"],
            ),
        )
        selected.append(best["text"])
        covered.update(best["tags"] & themes)
        remaining.remove(best)
    return selected


def _skill_score(
    skill: dict,
    normalized_text: str,
    themes: set[str],
    family_tags: set[str],
) -> tuple[int, bool]:
    exact = any(
        _contains_phrase(normalized_text, alias)
        for alias in skill.get("aliases", [skill["name"]])
    )
    tags = set(skill.get("tags", []))
    score = (
        skill.get("priority", 0)
        + (20 if exact else 0)
        + 7 * len(tags & themes)
        + 3 * len(tags & family_tags)
    )
    return score, exact


def _select_skills(
    catalog: dict,
    normalized_text: str,
    themes: set[str],
    family_tags: set[str],
) -> tuple[list[SkillCategory], list[str]]:
    category_defs = {item["name"]: item for item in catalog["skill_categories"]}
    candidates: dict[str, list[dict]] = {name: [] for name in category_defs}

    for index, skill in enumerate(catalog["skills"]):
        score, exact = _skill_score(skill, normalized_text, themes, family_tags)
        item = deepcopy(skill)
        item.update({"score": score, "exact": exact, "index": index})
        candidates[skill["category"]].append(item)

    category_scores = []
    for index, category in enumerate(catalog["skill_categories"]):
        items = sorted(
            candidates[category["name"]],
            key=lambda item: (item["score"], -item["index"]),
            reverse=True,
        )
        exact_count = sum(1 for item in items if item["exact"])
        category_tags = set(category.get("tags", []))
        score = (
            category.get("priority", 0)
            + sum(item["score"] for item in items[:5])
            + 18 * exact_count
            + 8 * len(category_tags & themes)
            + 4 * len(category_tags & family_tags)
        )
        category_scores.append((score, -index, category["name"]))

    chosen_names = ["Analytics & Reporting"]
    conditional_categories = [
        ("AI & Automation", {"ai", "automation"}),
        ("GTM & Sales Operations", {"gtm", "sales_ops"}),
        ("Market & Customer Insights", {"market_insights", "category_insights"}),
        ("Program Management", {"program"}),
    ]
    for category_name, trigger_tags in conditional_categories:
        if trigger_tags & themes and category_name not in chosen_names:
            chosen_names.append(category_name)
        if len(chosen_names) >= MAX_SKILL_CATEGORIES:
            break
    for _, _, category_name in sorted(category_scores, reverse=True):
        if category_name not in chosen_names:
            chosen_names.append(category_name)
        if len(chosen_names) >= MAX_SKILL_CATEGORIES:
            break
    chosen_names.sort(key=lambda name: list(category_defs).index(name))

    result = []
    exact_matches = []
    for category_name in chosen_names:
        items = sorted(
            candidates[category_name],
            key=lambda item: (item["score"], -item["index"]),
            reverse=True,
        )
        names = []
        for item in items:
            proposed = ", ".join(names + [item["name"]])
            if len(proposed) > MAX_SKILL_LINE_CHARS:
                continue
            names.append(item["name"])
            if item["exact"]:
                exact_matches.append(item["name"])
            if len(names) >= MAX_SKILLS_PER_CATEGORY:
                break
        result.append(SkillCategory(category_name, ", ".join(names)))
    return result, exact_matches


def _unsupported_terms(catalog: dict, normalized_text: str) -> list[str]:
    return [
        item["label"]
        for item in catalog.get("gap_terms", [])
        if any(_contains_phrase(normalized_text, alias) for alias in item["aliases"])
    ]


def select_catalog_content(
    family: str,
    job_title: str = "",
    jd_text: str = "",
) -> tuple[list[ExperienceEntry], list[SkillCategory], dict]:
    """Select approved titles, bullets, and skills for a job description."""
    catalog = load_catalog()
    normalized_text = _normalize(f"{job_title}\n{jd_text}")
    family_tags = set(
        catalog["families"].get(family, catalog["families"]["General Business"])
    )
    themes = _matched_themes(catalog, normalized_text)
    has_job_context = bool(_normalize(job_title) or _normalize(jd_text))

    experiences = []
    selected_titles = {}
    intern_count = 0
    for item in catalog["experiences"]:
        title = _select_title(item, themes, family_tags, has_job_context)
        if "intern" in title.casefold():
            intern_count += 1
            if intern_count > MAX_INTERN_TITLES:
                title = next(
                    (option["text"] for option in item["titles"] if "intern" not in option["text"].casefold()),
                    title,
                )
        selected_titles[item["company"]] = title
        experiences.append(ExperienceEntry(
            company=item["company"],
            role=title,
            date=item["date"],
            bullets=_select_bullets(item, themes, family_tags),
        ))

    skills, matched_skills = _select_skills(
        catalog, normalized_text, themes, family_tags
    )
    report = {
        "matched_themes": sorted(
            theme.replace("_", " ").title() for theme in (themes or family_tags)
        ),
        "selected_titles": selected_titles,
        "matched_skills": sorted(set(matched_skills)),
        "unapproved_jd_terms": _unsupported_terms(catalog, normalized_text),
        "catalog_version": catalog.get("version", 1),
    }
    return experiences, skills, report
