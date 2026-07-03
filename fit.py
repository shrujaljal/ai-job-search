"""
Fit scoring for job postings, based on Shrujal Agarwal's candidate profile.

Scores a job from its title + company + location (fast, no JD fetch needed) and
returns a 0-100 score, a tier label, a detected role family, and a plain-English
reason string explaining the score against the profile.
"""

import re

# ── Role families (priority tiers from the candidate profile) ────────────────
# tier 1 = highest interest, tier 3 = acceptable
ROLE_FAMILIES = {
    # family name: (tier, [keywords])
    "Strategy & Operations": (1, [
        "strategy and operations", "strategy & operations", "s&o", "biz ops",
        "business operations", "business operations", "strategy and planning",
        "planning and intelligence", "operations strategy", "chief of staff",
    ]),
    "Operations Analyst": (1, [
        "operations analyst", "operations associate", "operations manager",
        "operational excellence", "process improvement",
    ]),
    "Business Analyst": (1, [
        "business analyst", "business intelligence", "data analyst",
        "reporting analyst", "insights analyst",
    ]),
    "Strategy Analyst": (1, [
        "strategy analyst", "strategy associate", "corporate strategy",
        "strategic planning", "strategy manager",
    ]),
    "Program Management": (1, [
        "program manager", "program management", "project manager",
        "project management", "pmo", "technical program",
    ]),
    "Revenue / Sales Operations": (1, [
        "revenue operations", "revops", "sales operations", "sales strategy",
        "gtm operations", "go-to-market operations",
    ]),
    "Product Operations": (1, [
        "product operations", "product ops",
    ]),
    "Product Marketing": (2, [
        "product marketing", "pmm", "positioning", "go-to-market", "gtm",
    ]),
    "Marketing Operations": (2, [
        "marketing operations", "marketing ops", "campaign operations",
        "growth strategy", "marketing analyst", "marketing strategy",
    ]),
    "Consulting": (2, [
        "consultant", "consulting", "advisory", "business transformation",
    ]),
    "Finance / FP&A": (3, [
        "financial analyst", "fp&a", "finance analyst", "procurement",
    ]),
    "Customer Success": (3, [
        "customer success", "customer operations", "client operations",
    ]),
}

# ── Target companies (from the application strategy) ─────────────────────────
TARGET_COMPANIES = {
    "google", "microsoft", "salesforce", "adobe", "uber", "doordash", "atlassian",
    "servicenow", "hubspot", "linkedin", "amazon", "intuit", "nvidia", "apple",
    "cisco", "zscaler", "visa", "mastercard", "american express", "amex",
    "jpmorgan", "jp morgan", "morgan stanley", "goldman sachs", "thomson reuters",
    "mckinsey", "bcg", "bain", "deloitte", "pwc", "ey", "kpmg", "accenture",
    "workday", "asana", "notion", "canva", "figma", "openai", "anthropic",
    "datadog", "snowflake", "palantir", "pinterest", "spotify", "airbnb",
    "robinhood", "rivian", "stripe", "block", "capital one", "abbott",
    "johnson & johnson", "medtronic", "roche", "illumina", "amgen", "tiktok",
}

# ── Locations ────────────────────────────────────────────────────────────────
PREFERRED_LOCATIONS = {
    "ca", "california", "ny", "new york", "wa", "washington", "seattle",
    "tx", "texas", "ma", "massachusetts", "boston", "san francisco", "sf",
    "los angeles", "san jose", "san diego", "bay area", "sunnyvale",
    "mountain view", "palo alto", "santa clara", "cupertino", "san bruno",
    "austin", "dallas", "houston", "manhattan", "brooklyn", "redmond",
}
ACCEPTABLE_LOCATIONS = {
    "il", "illinois", "chicago", "co", "colorado", "denver", "va", "virginia",
    "nc", "north carolina", "ga", "georgia", "atlanta", "az", "arizona", "phoenix",
}
REMOTE_HINTS = {"remote", "anywhere", "us remote", "hybrid"}

# ── Red flags (deal-breakers / low priority from the profile) ────────────────
HARD_RED_FLAGS = [
    "software engineer", "software developer", "backend", "frontend", "full stack",
    "full-stack", "machine learning engineer", "ml engineer", "data scientist",
    "data engineer", "devops", "site reliability", "sre", "research scientist",
    "clinical research", "ui designer", "ux designer", "ux researcher",
    "account executive", "sales representative", "sales rep", "quota",
    "cloud architect", "security engineer", "android", "ios developer",
]
SENIOR_FLAGS = ["director", "vice president", "vp,", "vp ", "head of", "chief",
                "principal", "senior manager", "sr. manager", "sr manager"]


def _norm(text: str) -> str:
    return (text or "").lower().strip()


def detect_family(title: str, jd_text: str = "") -> tuple[str, int]:
    """
    Return (family_name, tier). The title dominates: a keyword in the title is
    worth much more than one in the JD body, so a "Strategy & Operations" title
    isn't overridden by a JD that merely mentions "consulting" as a nice-to-have.
    """
    title_l = _norm(title)
    jd_l = _norm(jd_text)
    TITLE_WEIGHT = 5
    best = ("General Business", 4)
    best_score = 0
    for family, (tier, kws) in ROLE_FAMILIES.items():
        score = (sum(TITLE_WEIGHT for kw in kws if kw in title_l)
                 + sum(1 for kw in kws if kw in jd_l))
        if score == 0:
            continue
        # prefer higher weighted score, then better (lower) tier
        if score > best_score or (score == best_score and tier < best[1]):
            best = (family, tier)
            best_score = score
    return best


def score_job(title: str, company: str, location: str,
              jd_text: str = "") -> dict:
    """
    Score a job 0-100 against the candidate profile.

    Returns dict with: score, tier, family, reason (str).
    """
    title_l = _norm(title)
    company_l = _norm(company)
    loc_l = _norm(location)

    reasons_plus = []
    reasons_minus = []

    # ── Role family (base score) ─────────────────────────────────────────────
    family, tier = detect_family(title, jd_text)
    tier_base = {1: 55, 2: 45, 3: 36, 4: 18}[tier]
    score = tier_base
    if tier == 1:
        reasons_plus.append(f"strong role match ({family})")
    elif tier == 2:
        reasons_plus.append(f"good role match ({family})")
    elif tier == 3:
        reasons_plus.append(f"acceptable role match ({family})")
    else:
        reasons_minus.append("role family unclear from title")

    # ── Company ──────────────────────────────────────────────────────────────
    if any(tc in company_l for tc in TARGET_COMPANIES):
        score += 16
        reasons_plus.append(f"{company.strip()} is a target company")

    # ── Location ─────────────────────────────────────────────────────────────
    if any(h in loc_l for h in REMOTE_HINTS):
        score += 12
        reasons_plus.append("remote/hybrid friendly")
    elif any(re.search(rf"\b{re.escape(p)}\b", loc_l) for p in PREFERRED_LOCATIONS):
        score += 12
        reasons_plus.append("preferred location")
    elif any(re.search(rf"\b{re.escape(a)}\b", loc_l) for a in ACCEPTABLE_LOCATIONS):
        score += 6
        reasons_plus.append("acceptable location")
    elif loc_l:
        reasons_minus.append("location outside target states")

    # ── Seniority penalty (too senior for early career) ──────────────────────
    if any(sf in title_l for sf in SENIOR_FLAGS):
        score -= 22
        reasons_minus.append("likely too senior")

    # ── Hard red flags (technical / sales roles the profile excludes) ────────
    hit_flag = next((rf for rf in HARD_RED_FLAGS if rf in title_l), None)
    if hit_flag:
        score -= 32
        reasons_minus.append(f"off-target role type ({hit_flag})")

    # ── Clamp + tier ─────────────────────────────────────────────────────────
    score = max(0, min(100, score))
    if score >= 75:
        label = "Strong"
    elif score >= 60:
        label = "Good"
    elif score >= 45:
        label = "Moderate"
    else:
        label = "Weak"

    # ── Build reason string ──────────────────────────────────────────────────
    parts = []
    if reasons_plus:
        parts.append("+ " + "; ".join(reasons_plus))
    if reasons_minus:
        parts.append("- " + "; ".join(reasons_minus))
    reason = "   ".join(parts) if parts else "no strong signals"

    return {"score": score, "tier": label, "family": family, "reason": reason}
