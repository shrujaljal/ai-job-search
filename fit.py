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
        "sales strategy and operations", "sales strategy & operations",
        "gtm operations", "gtm strategy", "go-to-market operations",
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
    "Category / Market Insights": (2, [
        "category insights", "category manager", "category management",
        "market insights", "consumer insights", "shopper insights",
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
# Management-level titles — too senior for an early-career (2-3 yr) candidate.
VERY_SENIOR_FLAGS = [
    "director", "vice president", "vp,", "vp ", " vp", "head of", "chief",
    "principal", "senior manager", "sr. manager", "sr manager", "distinguished",
]
# Titles that usually imply 5+ years — down-rank but don't exclude.
MID_SENIOR_RE = re.compile(
    r"\b(senior|sr\.?|staff|lead|expert)\b|\b(ii|iii|iv|v)\b|level\s*[3-9]", re.I)

# Max years of experience the candidate targets (early career).
MAX_YEARS = 4


# ── Sponsorship / work-authorization blockers (F1 student needs sponsorship) ─
# Each entry: (regex, human-readable label). Windowed with [^.]{0,N} so the
# trigger words must appear close together (within a sentence), not anywhere.
SPONSORSHIP_BLOCKERS = [
    (r"\bno\b[^.]{0,25}\bsponsorship\b", "no visa sponsorship"),
    (r"\bwithout\b[^.]{0,30}\bsponsorship\b", "must work without sponsorship"),
    (r"\b(not|unable|cannot|can'?t|won'?t|does\s+not|do\s+not|will\s+not)\b"
     r"[^.]{0,35}\bsponsor(ship)?\b", "does not sponsor visas"),
    (r"\bsponsorship\b[^.]{0,25}\bnot\b[^.]{0,20}\b(available|offered|provided)\b",
     "sponsorship not available"),
    (r"\bauthorized\s+to\s+work\b[^.]{0,50}\bwithout\b[^.]{0,20}\bsponsorship\b",
     "must be work-authorized without sponsorship"),
    (r"\bmust\b[^.]{0,25}\b(u\.?s\.?|united\s+states)\s+citizen", "U.S. citizenship required"),
    (r"\b(u\.?s\.?|united\s+states)\s+citizen(ship)?\b[^.]{0,25}\b(required|only|must)\b",
     "U.S. citizenship required"),
    (r"\bcitizenship\b[^.]{0,15}\b(is\s+)?required\b", "U.S. citizenship required"),
    (r"\bitar\b", "ITAR / export control"),
    (r"\bexport[\s-]control(led|s)?\b", "export-controlled role"),
    (r"\bsecurity\s+clearance\b", "requires security clearance"),
    (r"\b(ts/sci|top\s+secret|secret\s+clearance)\b", "requires security clearance"),
    (r"\b(u\.?s\.?|united\s+states)\s+person\b", "must be a U.S. person (ITAR)"),
    (r"\b(green\s+card|permanent\s+resident)\b[^.]{0,25}\b(required|only|holder)\b",
     "green card / permanent resident required"),
]
_SPONSOR_RE = [(re.compile(p, re.I), label) for p, label in SPONSORSHIP_BLOCKERS]


def analyze_sponsorship(jd_text: str) -> tuple[bool, list[str]]:
    """
    Scan a JD for work-authorization blockers that disqualify an F1 student
    needing sponsorship. Returns (blocked, [matched labels]).
    """
    if not jd_text:
        return False, []
    matched = []
    for rx, label in _SPONSOR_RE:
        if rx.search(jd_text) and label not in matched:
            matched.append(label)
    return (len(matched) > 0), matched


def extract_min_years(jd_text: str) -> int | None:
    """
    Pull the minimum years-of-experience requirement from a JD.
    Handles '5+ years', '3-5 years', 'minimum of 4 years', 'at least 3 years'.
    For compound hard requirements, returns the highest stated minimum so
    "5 years overall, including 2 years in analytics" remains a 5-year role.
    Explicitly preferred/ideal/nice-to-have statements are ignored.
    """
    if not jd_text:
        return None
    text = jd_text.lower()
    requirements = []
    masked = list(text)
    optional_context = re.compile(
        r"\b(preferred|ideally|ideal|nice to have|bonus|a plus)\b", re.I
    )

    def is_optional(match: re.Match) -> bool:
        before = text[max(0, match.start() - 35):match.start()]
        after = text[match.end():min(len(text), match.end() + 24)]
        return bool(
            optional_context.search(before)
            or re.match(
                r"^\W*(?:is\s+)?"
                r"(?:preferred|ideal|nice to have|a plus|bonus)\b",
                after,
                re.I,
            )
        )

    range_pattern = re.compile(
        r"(\d{1,2})\s*(?:-|to|–)\s*(\d{1,2})\s*\+?\s*years?"
        r"(?:['’]|\s)*(?:of\s+)?(?:\w+\s+){0,3}"
        r"(?:experience|exp|professional|relevant|industry)"
    )
    for match in range_pattern.finditer(text):
        if not is_optional(match):
            requirements.append(int(match.group(1)))
        for index in range(match.start(), match.end()):
            masked[index] = " "

    standalone_pattern = re.compile(
        r"(?:minimum(?:\s+of)?|at least|min\.?|must have|required)?\s*"
        r"(\d{1,2})\s*(?:\+|or more)?\s*years?"
        r"(?:['’]|\s)*(?:of\s+)?(?:\w+\s+){0,3}"
        r"(?:experience|exp|professional|relevant|industry)"
    )
    masked_text = "".join(masked)
    for match in standalone_pattern.finditer(masked_text):
        if not is_optional(match):
            requirements.append(int(match.group(1)))

    # Common qualification phrasing omits the word "experience":
    # "5+ years in strategy" or "at least 4 years working with SQL".
    domain_pattern = re.compile(
        r"(?:(?:minimum(?:\s+of)?|at least|min\.?|must have|required|"
        r"you (?:have|bring)|possess(?:ing)?)\s*)?"
        r"(\d{1,2})\s*(\+|or more)?\s*years?"
        r"\s+(?:working\s+)?(?:in|with|as)\b"
    )
    for match in domain_pattern.finditer(masked_text):
        has_requirement_prefix = bool(
            re.search(
                r"(?:minimum|at least|min\.?|must have|required|"
                r"you (?:have|bring)|possess(?:ing)?)",
                match.group(0),
                re.I,
            )
        )
        if (
            (match.group(2) or has_requirement_prefix)
            and not is_optional(match)
        ):
            requirements.append(int(match.group(1)))

    reasonable = [years for years in requirements if 0 < years <= 20]
    return max(reasonable) if reasonable else None


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
    if any(sf in title_l for sf in VERY_SENIOR_FLAGS):
        score -= 24
        reasons_minus.append("management-level, likely too senior")
    elif MID_SENIOR_RE.search(title_l):
        score -= 12
        reasons_minus.append("senior/leveled title, may want 5+ yrs")

    # ── Sponsorship / work-authorization blockers (from JD) ──────────────────
    blocked, sp_matched = analyze_sponsorship(jd_text)
    if blocked:
        score -= 45
        reasons_minus.append("no sponsorship: " + ", ".join(sp_matched))

    # ── Years of experience from JD (early-career target: <=4 yrs) ───────────
    min_years = extract_min_years(jd_text)
    if min_years is not None:
        if min_years > MAX_YEARS:
            score -= 26
            reasons_minus.append(f"requires {min_years}+ yrs experience")
        else:
            reasons_plus.append(f"experience bar fits ({min_years} yrs)")

    # ── Hard red flags (technical / sales roles the profile excludes) ────────
    hit_flag = next((rf for rf in HARD_RED_FLAGS if rf in title_l), None)
    if hit_flag:
        score -= 32
        reasons_minus.append(f"off-target role type ({hit_flag})")

    # ── Clamp + tier ─────────────────────────────────────────────────────────
    score = max(0, min(100, score))
    if blocked:
        label = "Blocked"          # sponsorship/citizenship/ITAR — not eligible
    elif score >= 75:
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

    return {"score": score, "tier": label, "family": family,
            "reason": reason, "blocked": blocked, "min_years": min_years,
            "scored_on_jd": bool(jd_text)}
