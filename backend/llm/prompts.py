from __future__ import annotations

import json
import re
from copy import deepcopy


def build_system_prompt(strictness: int) -> str:
    level = _strictness(strictness)
    if level >= 80:
        latitude = (
            "Stay very close to the source wording. Prefer one source bullet per rewrite "
            "and retain its concrete nouns, tools, and outcomes."
        )
    elif level >= 50:
        latitude = (
            "You may substantially rephrase and combine related source bullets from the "
            "same experience, while preserving every factual claim."
        )
    else:
        latitude = (
            "You may use flexible wording and transferable positioning, but every factual "
            "claim must still be supported by the cited profile evidence."
        )
    return f"""You tailor resumes using only supplied Profile facts.

Hard rules:
- Never invent employers, roles, dates, education, skills, tools, metrics, scope, or outcomes.
- A rewritten experience bullet must cite one or more source bullet indexes from the same experience.
- Preserve the meaning of every cited source bullet. Do not turn duties into measured outcomes.
- Any number in rewritten text must occur in its cited source text.
- skill_names must contain only exact strings from allowed_skill_names.
- Return JSON only. Do not use Markdown or add fields.

Grounding strictness: {level}/100.
{latitude}
"""


def build_grounding_sources(profile: dict, context: dict, jd_text: str) -> list[dict]:
    """Retrieve the most relevant Profile bullets for each rendered experience."""
    profile_experiences = profile.get("experience", [])
    query_tokens = _tokens(jd_text)
    result = []
    for index, exp in enumerate(context.get("experiences", [])):
        matched = next(
            (
                item for item in profile_experiences
                if _same_entry(item, exp)
            ),
            exp,
        )
        bullets = [text for text in matched.get("bullets", []) if str(text).strip()]
        ranked = sorted(
            enumerate(bullets),
            key=lambda item: (
                len(_tokens(item[1]) & query_tokens),
                -item[0],
            ),
            reverse=True,
        )
        selected = [text for _, text in ranked[:24]]
        result.append({
            "index": index,
            "company": exp.get("company", ""),
            "role": exp.get("role", ""),
            "bullets": [
                {"index": bullet_index, "text": text}
                for bullet_index, text in enumerate(selected)
            ],
        })
    return result


def build_user_prompt(
    profile: dict,
    context: dict,
    jd_text: str,
    role: str,
    company: str,
    strictness: int = 85,
    source_experiences: list[dict] | None = None,
) -> str:
    sources = source_experiences or build_grounding_sources(profile, context, jd_text)
    allowed_skills = []
    for category in context.get("skills", []):
        items = category.get("items", "")
        values = items if isinstance(items, list) else items.split(",")
        allowed_skills.extend(item.strip() for item in values if item.strip())

    payload = {
        "target": {"company": company, "role": role, "job_description": jd_text},
        "candidate_profile": _candidate_facts(profile),
        "grounding_strictness": _strictness(strictness),
        "current_summary": context.get("summary", ""),
        "source_experiences": sources,
        "allowed_skill_names": list(dict.fromkeys(allowed_skills)),
        "output_schema": {
            "summary": "string, maximum 530 characters",
            "summary_source_evidence": [
                "one or more exact, non-empty strings copied from candidate_profile"
            ],
            "experiences": [{
                "index": "integer source experience index",
                "bullets": [{
                    "text": "rewritten bullet, maximum 220 characters",
                    "source_indices": ["one or more integer source bullet indexes"],
                }],
            }],
            "skill_names": ["exact strings from allowed_skill_names"],
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def _candidate_facts(profile: dict) -> dict:
    facts = deepcopy(profile)
    facts.pop("identity", None)
    facts.pop("experience", None)
    facts.pop("resume_blueprint", None)
    return facts


def _same_entry(left: dict, right: dict) -> bool:
    left_company = _normalized(left.get("company", ""))
    right_company = _normalized(right.get("company", ""))
    left_role = _normalized(left.get("role", ""))
    right_role = _normalized(right.get("role", ""))
    return bool(left_company and left_company == right_company and (
        not left_role or not right_role or left_role == right_role
    ))


def _normalized(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _tokens(value: object) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9+#.]+", str(value).lower())
        if len(token) > 2
    }


def _strictness(value: object) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 85
