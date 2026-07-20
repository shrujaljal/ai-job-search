from __future__ import annotations

import json
from copy import deepcopy


SYSTEM_PROMPT = """You tailor resumes using only supplied candidate facts.

Hard rules:
- Never invent employers, roles, dates, education, skills, tools, metrics, scope, or outcomes.
- A rewritten experience bullet must cite one or more source bullet indexes from the same experience.
- Preserve the meaning of every cited source bullet. Do not turn duties into measured outcomes.
- Any number in rewritten text must occur in its cited source text.
- skill_names must contain only exact strings from allowed_skill_names.
- Return JSON only. Do not use Markdown or add fields.
"""


def build_user_prompt(profile: dict, context: dict, jd_text: str, role: str, company: str) -> str:
    source_experiences = []
    for index, exp in enumerate(context.get("experiences", [])):
        source_experiences.append({
            "index": index,
            "company": exp.get("company", ""),
            "role": exp.get("role", ""),
            "bullets": [
                {"index": bullet_index, "text": text}
                for bullet_index, text in enumerate(exp.get("bullets", []))
            ],
        })

    allowed_skills = []
    for category in context.get("skills", []):
        items = category.get("items", "")
        values = items if isinstance(items, list) else items.split(",")
        allowed_skills.extend(item.strip() for item in values if item.strip())

    payload = {
        "target": {"company": company, "role": role, "job_description": jd_text},
        "candidate_profile": _candidate_facts(profile),
        "current_summary": context.get("summary", ""),
        "source_experiences": source_experiences,
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
    return facts
