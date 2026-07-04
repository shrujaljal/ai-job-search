"""
Config-driven fit scoring.

This is the V1 `fit.py` logic with every hardcoded constant (role families,
target companies, locations, red flags, seniority terms, sponsorship blockers,
weights, tier thresholds) moved out into `rules.json`, which the user edits in
the Settings UI. All functions take a `rules` dict.
"""

from __future__ import annotations

import re


def _norm(text: str) -> str:
    return (text or "").lower().strip()


# ── Sponsorship / work-authorization blockers ────────────────────────────────
def analyze_sponsorship(jd_text: str, rules: dict) -> tuple[bool, list[str]]:
    """Scan a JD for work-authorization blockers. Returns (blocked, [labels])."""
    if not jd_text:
        return False, []
    matched: list[str] = []
    for entry in rules.get("sponsorship_blockers", []):
        pattern, label = entry.get("pattern"), entry.get("label", "restricted")
        if not pattern:
            continue
        try:
            if re.search(pattern, jd_text, re.I) and label not in matched:
                matched.append(label)
        except re.error:
            continue  # a bad user-entered regex shouldn't crash scoring
    return (len(matched) > 0), matched


# ── Years of experience ──────────────────────────────────────────────────────
def extract_min_years(jd_text: str) -> int | None:
    """Smallest 'X years of experience' requirement stated in the JD, or None."""
    if not jd_text:
        return None
    text = jd_text.lower()
    mins: list[int] = []
    for m in re.finditer(r"(\d{1,2})\s*(?:-|to|–)\s*(\d{1,2})\s*\+?\s*years?", text):
        mins.append(int(m.group(1)))
    for m in re.finditer(
        r"(?:minimum(?:\s+of)?|at least|min\.?)?\s*(\d{1,2})\s*\+?\s*years?"
        r"(?:\s+of)?\s+(?:experience|exp|professional|relevant|industry)", text):
        mins.append(int(m.group(1)))
    reasonable = [y for y in mins if 0 < y <= 20]
    return min(reasonable) if reasonable else None


# ── Role family ──────────────────────────────────────────────────────────────
def detect_family(title: str, jd_text: str, rules: dict) -> tuple[str, int]:
    """
    Return (family_name, tier). The title dominates JD body matches, so a
    "Strategy & Operations" title isn't overridden by a JD that merely mentions
    "consulting" as a nice-to-have.
    """
    title_l = _norm(title)
    jd_l = _norm(jd_text)
    title_weight = int(rules.get("weights", {}).get("title_weight_multiplier", 5))
    best = ("General Business", 4)
    best_score = 0
    for fam in rules.get("role_families", []):
        name = fam.get("name", "")
        tier = int(fam.get("tier", 4))
        kws = fam.get("keywords", [])
        score = (sum(title_weight for kw in kws if kw in title_l)
                 + sum(1 for kw in kws if kw in jd_l))
        if score == 0:
            continue
        if score > best_score or (score == best_score and tier < best[1]):
            best = (name, tier)
            best_score = score
    return best


# ── Full score ───────────────────────────────────────────────────────────────
def score_job(title: str, company: str, location: str, jd_text: str,
              rules: dict) -> dict:
    """Score a job 0-100 against the rules. Returns score/tier/family/reason/…"""
    title_l = _norm(title)
    company_l = _norm(company)
    loc_l = _norm(location)
    w = rules.get("weights", {})
    reasons_plus: list[str] = []
    reasons_minus: list[str] = []

    # Role family (base score by tier)
    family, tier = detect_family(title, jd_text, rules)
    tier_base = w.get("tier_base", {})
    score = float(tier_base.get(str(tier), tier_base.get("unknown", 18)))
    if tier == 1:
        reasons_plus.append(f"strong role match ({family})")
    elif tier == 2:
        reasons_plus.append(f"good role match ({family})")
    elif tier == 3:
        reasons_plus.append(f"acceptable role match ({family})")
    else:
        reasons_minus.append("role family unclear from title")

    # Company
    if any(tc in company_l for tc in rules.get("target_companies", [])):
        score += w.get("target_company_bonus", 16)
        reasons_plus.append(f"{company.strip()} is a target company")

    # Location
    def _word(loc_list):
        return any(re.search(rf"\b{re.escape(p)}\b", loc_l) for p in loc_list)

    if any(h in loc_l for h in rules.get("remote_hints", [])):
        score += w.get("remote_bonus", 12)
        reasons_plus.append("remote/hybrid friendly")
    elif _word(rules.get("preferred_locations", [])):
        score += w.get("preferred_location_bonus", 12)
        reasons_plus.append("preferred location")
    elif _word(rules.get("acceptable_locations", [])):
        score += w.get("acceptable_location_bonus", 6)
        reasons_plus.append("acceptable location")
    elif loc_l:
        reasons_minus.append("location outside target areas")

    # Seniority
    if any(sf in title_l for sf in rules.get("very_senior_terms", [])):
        score += w.get("very_senior_penalty", -24)
        reasons_minus.append("management-level, likely too senior")
    elif any(sf in title_l for sf in rules.get("mid_senior_terms", [])):
        score += w.get("mid_senior_penalty", -12)
        reasons_minus.append("senior/leveled title, may want 5+ yrs")

    # Sponsorship blockers (from JD)
    blocked, sp_matched = analyze_sponsorship(jd_text, rules)
    if blocked:
        score += w.get("sponsorship_penalty", -45)
        reasons_minus.append("no sponsorship: " + ", ".join(sp_matched))

    # Years of experience (from JD)
    max_years = int(rules.get("max_years_experience", 4))
    min_years = extract_min_years(jd_text)
    if min_years is not None:
        if min_years > max_years:
            score += w.get("over_experience_penalty", -26)
            reasons_minus.append(f"requires {min_years}+ yrs experience")
        else:
            reasons_plus.append(f"experience bar fits ({min_years} yrs)")

    # Hard red flags (title)
    hit_flag = next((rf for rf in rules.get("hard_red_flags", []) if rf in title_l), None)
    if hit_flag:
        score += w.get("red_flag_penalty", -32)
        reasons_minus.append(f"off-target role type ({hit_flag})")

    # Clamp + tier label
    score = int(max(0, min(100, round(score))))
    t = rules.get("tiers", {"strong": 75, "good": 60, "moderate": 45})
    if blocked:
        label = "Blocked"
    elif score >= t.get("strong", 75):
        label = "Strong"
    elif score >= t.get("good", 60):
        label = "Good"
    elif score >= t.get("moderate", 45):
        label = "Moderate"
    else:
        label = "Weak"

    parts = []
    if reasons_plus:
        parts.append("+ " + "; ".join(reasons_plus))
    if reasons_minus:
        parts.append("- " + "; ".join(reasons_minus))
    reason = "   ".join(parts) if parts else "no strong signals"

    return {"score": score, "tier": label, "family": family, "reason": reason,
            "blocked": blocked, "min_years": min_years,
            "scored_on_jd": bool(jd_text)}
