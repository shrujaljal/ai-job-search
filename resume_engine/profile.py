"""Candidate profile summaries plus deterministic JD tailoring entry points."""

from .catalog import select_catalog_content
from .models import ResumeData


_STRAT_OPS = (
    "Strategy & Operations professional with an MBA and 3+ years of experience "
    "solving complex business and operational problems across Hyundai Rotem, Thomson "
    "Reuters, Goldman Sachs, and startup environments. Combines process analysis, SQL "
    "and Excel reporting, cross-functional coordination, and AI-assisted problem-solving "
    "to improve workflows and translate data into practical business recommendations."
)
_BUSINESS_ANALYST = (
    "MBA graduate from UC Riverside (GPA 3.8) with experience analyzing operational and "
    "business data across Fortune 500 organizations, consulting engagements, and startups. "
    "Uses SQL, Advanced Excel, Tableau, Power BI, and structured process analysis to build "
    "trusted reporting, surface trends, and translate complex findings into clear business "
    "recommendations."
)
_PROGRAM_MGMT = (
    "MBA graduate from UC Riverside (GPA 3.8) with experience coordinating cross-functional "
    "initiatives across enterprise, startup, and consulting environments. Brings structured "
    "project planning, stakeholder management, KPI reporting, and process-improvement skills "
    "to move complex workstreams from analysis through execution."
)
_CONSULTING = (
    "MBA graduate from UC Riverside (GPA 3.8) with consulting, enterprise operations, and "
    "startup experience solving ambiguous business problems through structured analysis, "
    "stakeholder engagement, and process improvement. Experienced in evaluating operations, "
    "building implementation roadmaps, and presenting executive-ready recommendations."
)
_MARKETING = (
    "MBA graduate from UC Riverside (GPA 3.8) combining marketing operations, market research, "
    "and analytics experience with a strong strategy foundation. Skilled in campaign reporting, "
    "competitive analysis, customer insights, and go-to-market planning to improve positioning "
    "and cross-functional execution."
)
_SALES_OPS = (
    "Strategy & Operations professional with an MBA and experience supporting performance "
    "reporting, planning, workflow improvement, and cross-functional execution across global "
    "enterprises and startups. Uses SQL, Advanced Excel, dashboards, and AI-assisted workflows "
    "to convert business data into actionable GTM and operational recommendations."
)
_CATEGORY_INSIGHTS = (
    "MBA graduate from UC Riverside (GPA 3.8) with experience translating market, campaign, "
    "sales, and operational data into clear insights and recommendations. Combines Advanced "
    "Excel, SQL, Tableau, Power BI, competitive research, and stakeholder communication to "
    "support performance reporting and insight-led business decisions."
)
_GENERAL = (
    "MBA graduate from UC Riverside (GPA 3.8) with 3+ years across strategy, analytics, and "
    "operations within Fortune 500 organizations, consulting engagements, and startups. "
    "Skilled at translating ambiguous business problems into structured analysis, reporting, "
    "and executive-ready recommendations while partnering across functions."
)


_FAMILY_CONFIG = {
    "Strategy & Operations": (_STRAT_OPS,
        "Business Strategy, Operations Management, Business Analytics & Reporting"),
    "Operations Analyst": (_STRAT_OPS,
        "Operations Management, Business Analytics & Reporting, Process Improvement"),
    "Strategy Analyst": (_STRAT_OPS,
        "Business Strategy, Corporate Strategy, Business Analytics & Reporting"),
    "Business Analyst": (_BUSINESS_ANALYST,
        "Business Analytics & Reporting, Quantitative Analysis, Data Visualization"),
    "Program Management": (_PROGRAM_MGMT,
        "Project Management, Operations Management, Business Analytics & Reporting"),
    "Revenue / Sales Operations": (_SALES_OPS,
        "Operations Management, Business Analytics & Reporting, Business Strategy"),
    "Product Operations": (_STRAT_OPS,
        "Operations Management, Business Analytics & Reporting, Business Strategy"),
    "Consulting": (_CONSULTING,
        "Business Strategy, Operations Management, Business Analytics & Reporting"),
    "Product Marketing": (_MARKETING,
        "Marketing Strategy, Business Analytics & Reporting, Market Research"),
    "Marketing Operations": (_MARKETING,
        "Marketing Strategy, Business Analytics & Reporting, Market Research"),
    "Finance / FP&A": (_GENERAL,
        "Corporate Finance, Business Analytics & Reporting, Quantitative Analysis"),
    "Customer Success": (_GENERAL,
        "Business Analytics & Reporting, Operations Management, Business Strategy"),
    "Category / Market Insights": (_CATEGORY_INSIGHTS,
        "Marketing Strategy, Business Analytics & Reporting, Market Research"),
    "General Business": (_GENERAL,
        "Business Analytics & Reporting, Operations Management, Quantitative Analysis"),
}


def tailor_for_job(
    family: str,
    job_title: str = "",
    jd_text: str = "",
) -> tuple[ResumeData, dict]:
    """Return resume data and a transparent selection report for one JD."""
    summary, coursework = _FAMILY_CONFIG.get(
        family, _FAMILY_CONFIG["General Business"]
    )
    experiences, skills, report = select_catalog_content(
        family, job_title=job_title, jd_text=jd_text
    )
    return ResumeData(
        summary=summary,
        experiences=experiences,
        coursework=coursework,
        skills=skills,
    ), report


def tailor_for_family(family: str) -> ResumeData:
    """Backward-compatible family-only tailoring."""
    data, _ = tailor_for_job(family)
    return data


def base_resume() -> ResumeData:
    return tailor_for_family("Strategy & Operations")
