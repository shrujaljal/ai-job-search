from __future__ import annotations

import json
import re
from copy import deepcopy

import resume_builder
from llm import LLMProvider, ProviderError, create_provider
from llm.prompts import SYSTEM_PROMPT, build_user_prompt


NUMBER_RE = re.compile(r"(?<!\w)\d+(?:\.\d+)?%?\+?")


class TailoringValidationError(ValueError):
    """AI output could not be proven against supplied candidate facts."""


def build_tailored_context(
    profile: dict,
    content: dict,
    family: str,
    jd_text: str,
    role: str,
    company: str,
    settings: dict,
    use_llm: bool | None = None,
    provider: LLMProvider | None = None,
) -> tuple[dict, dict]:
    base = resume_builder.build_context(profile, content, family)
    llm_settings = settings.get("llm", {})
    enabled = bool(llm_settings.get("enabled")) if use_llm is None else use_llm
    if not enabled:
        return base, {"engine": "rules", "ai_requested": False}
    if not jd_text.strip():
        return base, _fallback("No job description was available for AI tailoring.")

    try:
        active_provider = provider or create_provider(llm_settings)
        raw = active_provider.complete_json(
            SYSTEM_PROMPT,
            build_user_prompt(profile, base, jd_text, role, company),
        )
        proposal = parse_provider_json(raw)
        tailored = _apply_validated(base, profile, proposal, content)
        return tailored, {
            "engine": "ai",
            "ai_requested": True,
            "provider": active_provider.name,
            "model": active_provider.model,
        }
    except (ProviderError, TailoringValidationError, json.JSONDecodeError,
            TypeError, KeyError, AttributeError, IndexError) as exc:
        return base, _fallback(str(exc))


def _fallback(reason: str) -> dict:
    return {
        "engine": "rules",
        "ai_requested": True,
        "ai_fallback": True,
        "ai_warning": reason,
    }


def parse_provider_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    value = json.loads(text)
    if not isinstance(value, dict):
        raise TailoringValidationError("AI response must be a JSON object.")
    return value


def _apply_validated(base: dict, profile: dict, proposal: dict, content: dict) -> dict:
    result = deepcopy(base)
    limits = {**resume_builder.DEFAULT_LIMITS, **content.get("limits", {})}

    summary = proposal.get("summary", "")
    if not isinstance(summary, str) or not summary.strip():
        raise TailoringValidationError("AI response did not include a summary.")
    if len(summary) > limits["max_summary_chars"]:
        raise TailoringValidationError("AI summary exceeds the configured length limit.")
    profile_text = json.dumps(profile, ensure_ascii=False)
    summary_evidence = proposal.get("summary_source_evidence", [])
    if (not isinstance(summary_evidence, list) or not summary_evidence
            or any(not isinstance(item, str) or not item.strip() or item not in profile_text
                   for item in summary_evidence)):
        raise TailoringValidationError("AI summary has invalid profile evidence.")
    _validate_numbers(summary, " ".join(summary_evidence), "summary")
    result["summary"] = summary.strip()

    source_experiences = base.get("experiences", [])
    proposed_experiences = proposal.get("experiences", [])
    if not isinstance(proposed_experiences, list):
        raise TailoringValidationError("AI experiences must be a list.")
    seen_experiences: set[int] = set()
    for exp in proposed_experiences:
        exp_index = exp.get("index")
        if not isinstance(exp_index, int) or not 0 <= exp_index < len(source_experiences):
            raise TailoringValidationError("AI cited an unknown experience.")
        if exp_index in seen_experiences:
            raise TailoringValidationError("AI returned a duplicate experience.")
        seen_experiences.add(exp_index)
        source_bullets = source_experiences[exp_index].get("bullets", [])
        proposed_bullets = exp.get("bullets", [])
        if not isinstance(proposed_bullets, list):
            raise TailoringValidationError("AI bullets must be a list.")
        validated_bullets = []
        for bullet in proposed_bullets:
            text = bullet.get("text", "")
            indices = bullet.get("source_indices", [])
            if not isinstance(text, str) or not text.strip() or len(text) > limits["max_chars_per_bullet"]:
                raise TailoringValidationError("AI returned an empty or overlong bullet.")
            if (not isinstance(indices, list) or not indices
                    or any(not isinstance(i, int) or not 0 <= i < len(source_bullets) for i in indices)):
                raise TailoringValidationError("AI bullet has invalid source evidence.")
            evidence = " ".join(source_bullets[i] for i in indices)
            _validate_numbers(text, evidence, "experience bullet")
            validated_bullets.append(text.strip())
        if validated_bullets:
            result["experiences"][exp_index]["bullets"] = validated_bullets

    skill_names = proposal.get("skill_names", [])
    if not isinstance(skill_names, list) or any(not isinstance(item, str) for item in skill_names):
        raise TailoringValidationError("AI skill_names must be a list of strings.")
    result["skills"] = _select_skills(base.get("skills", []), skill_names)
    result.setdefault("warnings", []).append("AI wording validated against profile source facts.")
    return result


def _validate_numbers(output: str, evidence: str, label: str) -> None:
    allowed = set(NUMBER_RE.findall(evidence.replace(",", "")))
    invented = sorted(set(NUMBER_RE.findall(output.replace(",", ""))) - allowed)
    if invented:
        raise TailoringValidationError(
            f"AI introduced unsupported numbers in {label}: {', '.join(invented)}")


def _select_skills(categories: list[dict], selected: list[str]) -> list[dict]:
    if not selected:
        return categories
    remaining = set(selected)
    available = set()
    parsed: list[tuple[str, list[str]]] = []
    for category in categories:
        items = category.get("items", "")
        values = items if isinstance(items, list) else items.split(",")
        clean = [item.strip() for item in values if item.strip()]
        parsed.append((category.get("name", ""), clean))
        available.update(clean)
    if not remaining <= available:
        unknown = ", ".join(sorted(remaining - available))
        raise TailoringValidationError(f"AI selected unknown skills: {unknown}")
    result = []
    for name, values in parsed:
        kept = [item for item in values if item in remaining]
        if kept:
            result.append({"name": name, "items": ", ".join(kept)})
    return result or categories
