"""
Shrujal Agarwal's base resume data plus role-family tailoring.

`tailor_for_family(family)` returns a ResumeData with the summary, skills, and
projects adjusted for the detected role family, following the role playbook.
All facts (companies, dates, titles, bullets) stay constant — only emphasis,
summary, skills ordering, and project selection change.
"""

from copy import deepcopy
from .models import ResumeData, ExperienceEntry, ProjectEntry, SkillCategory


# ── Fixed experience (facts never change) ────────────────────────────────────
def _experiences() -> list[ExperienceEntry]:
    return [
        ExperienceEntry(
            company="BB Wellness", role="Analyst Intern",
            date="Feb 2025 – Sep 2025",
            bullets=[
                "Defined go-to-market problem scope through market segmentation and "
                "competitive benchmarking across 6 competitors, translating research into "
                "fact-based product positioning recommendations for leadership.",
                "Built SQL-driven KPI dashboards spanning 4 channels, establishing a "
                "centralized reporting framework that surfaced performance gaps and enabled "
                "leadership to prioritize strategic initiatives.",
                "Developed hypothesis-driven business cases and strategic roadmaps, partnering "
                "with marketing, content, and operations stakeholders to align 10+ "
                "cross-functional initiatives against weekly OKRs.",
            ],
        ),
        ExperienceEntry(
            company="Thomson Reuters", role="Analyst – Global Operations",
            date="Oct 2023 – Jun 2024",
            bullets=[
                "Built 15+ SQL and Excel reporting frameworks adopted across 3 global "
                "business units, reducing manual reporting effort ~30% and improving "
                "executive visibility into business performance.",
                "Partnered with finance, procurement, and operations stakeholders across "
                "4 regions to standardize KPIs and support Quarterly Business Reviews, "
                "budgeting, and annual business planning.",
                "Prepared executive summaries translating complex, multi-source analyses "
                "into structured business recommendations for senior leadership.",
            ],
        ),
        ExperienceEntry(
            company="Goldman Sachs", role="STEM Intern – Asset & Wealth Management",
            date="Feb 2023 – Jun 2023",
            bullets=[
                "Built Qlik Sense dashboards consolidating 5+ operational data sources, "
                "improving executive visibility into business performance across AWM.",
                "Identified process gaps through workflow analysis using Excel, JIRA, and "
                "Qlik Sense, strengthening compliance reporting and operational controls.",
                "Developed operational trackers monitoring hundreds of client commitments, "
                "improving workflow transparency and cross-team reporting consistency.",
            ],
        ),
        ExperienceEntry(
            company="Beyond Key", role="Data Analyst Intern",
            date="Jun 2022 – Aug 2022",
            bullets=[
                "Analyzed business datasets using SQL, Python, and Excel; built Tableau "
                "dashboards enabling real-time performance monitoring for healthcare clients.",
            ],
        ),
    ]


# ── Projects ─────────────────────────────────────────────────────────────────
HYUNDAI = ProjectEntry(
    title="Hyundai Rotem Operations Consulting Project",
    bullets=[
        "Led a strategy consulting engagement analyzing manufacturing operations, "
        "inventory flows, and capacity constraints through process mapping and "
        "stakeholder interviews.",
        "Developed phased operational roadmaps, KPI frameworks, and executive "
        "recommendations improving scalability and operational efficiency.",
    ],
)
MARKETING_PROJECT = ProjectEntry(
    title="LinkedIn Ads & Value Proposition Strategy (MBA)",
    bullets=[
        "Developed a B2B LinkedIn advertising strategy through customer segmentation and "
        "persona development, defining audience targeting and campaign success metrics.",
        "Applied the Value Proposition Canvas to map customer jobs, pains, and gains, "
        "translating research into product positioning recommendations.",
    ],
)

LEADERSHIP = [
    "Launched the school's first newsletter and podcast, designing editorial strategy, "
    "distribution workflows, and performance dashboards that improved audience engagement.",
]


# ── Skill category sets ──────────────────────────────────────────────────────
def _skills_business() -> list[SkillCategory]:
    return [
        SkillCategory("Business Strategy",
            "Business Strategy, Strategic Planning, Annual Business Planning, "
            "Business Case Development, Market Research, Stakeholder Management"),
        SkillCategory("Analytics & Reporting",
            "SQL, Python, Advanced Excel (Pivot Tables, XLOOKUP, Power Query), "
            "Tableau, Qlik Sense, KPI Reporting, Data Visualization"),
        SkillCategory("Operations & Execution",
            "Cross-Functional Leadership, Program Management, Process Improvement, "
            "Operational Excellence, OKR Design & Tracking, Change Management"),
        SkillCategory("Tools & AI",
            "ChatGPT, Claude, Gemini, Excel Copilot, n8n, Salesforce, "
            "SAP Ariba, JIRA, HubSpot, PowerPoint"),
    ]


def _skills_marketing() -> list[SkillCategory]:
    return [
        SkillCategory("Marketing & GTM",
            "Product Positioning, Messaging, Go-to-Market, Campaign Reporting, "
            "Competitive Analysis, Market Research, Customer Insights, Content Planning"),
        SkillCategory("Analytics & Reporting",
            "SQL, Advanced Excel, Tableau, Qlik Sense, KPI Reporting, "
            "Engagement Analysis, Data Visualization"),
        SkillCategory("Strategy & Execution",
            "Business Strategy, Cross-Functional Leadership, Program Management, "
            "Stakeholder Management, Process Improvement"),
        SkillCategory("Tools & AI",
            "ChatGPT, Claude, Gemini, Excel Copilot, Buffer, Canva, "
            "HubSpot, Salesforce, PowerPoint"),
    ]


# ── Per-family summary + config ──────────────────────────────────────────────
_STRAT_OPS = (
    "MBA graduate from UC Riverside (GPA 3.8) with 3+ years across strategy, "
    "operations, and analytics within Fortune 500 organizations and startup "
    "environments. Skilled at translating ambiguous business problems into fact-based "
    "analysis, SQL-driven reporting, and executive-ready recommendations. Proven track "
    "record partnering cross-functionally to standardize KPIs, land business plans, and "
    "drive measurable performance."
)
_BUSINESS_ANALYST = (
    "MBA graduate from UC Riverside (GPA 3.8) with experience analyzing operational and "
    "business data across Fortune 500 organizations and startups. Proficient in SQL, "
    "Advanced Excel, Tableau, and Qlik Sense to build dashboards, surface trends, and "
    "support data-driven decisions. Skilled at translating complex analyses into clear, "
    "executive-ready business recommendations."
)
_PROGRAM_MGMT = (
    "MBA graduate from UC Riverside (GPA 3.8) with experience coordinating "
    "cross-functional initiatives across enterprise, startup, and consulting "
    "environments. Skilled in stakeholder management, project coordination, reporting, "
    "and implementation planning, with a strong analytical foundation for delivering "
    "business objectives in fast-moving environments."
)
_CONSULTING = (
    "MBA graduate from UC Riverside (GPA 3.8) with consulting, enterprise operations, "
    "and startup experience solving business problems through structured analysis, "
    "stakeholder engagement, and process improvement. Experienced in evaluating "
    "operations, building implementation roadmaps, and presenting executive-level "
    "recommendations."
)
_MARKETING = (
    "MBA graduate from UC Riverside (GPA 3.8) combining startup marketing and operations "
    "experience with a strong analytical foundation. Skilled in campaign reporting, "
    "competitive analysis, customer insights, and go-to-market planning to support "
    "product positioning and business growth across cross-functional teams."
)
_GENERAL = (
    "MBA graduate from UC Riverside (GPA 3.8) with 3+ years across strategy, analytics, "
    "and operations within Fortune 500 organizations and startup environments. Skilled "
    "at translating ambiguous business problems into fact-based analysis, reporting, and "
    "executive-ready recommendations while partnering across finance, operations, and "
    "marketing teams."
)

# family -> (summary, project, skills_fn, coursework)
_FAMILY_CONFIG = {
    "Strategy & Operations": (_STRAT_OPS, HYUNDAI, _skills_business,
        "Business Strategy, Operations Management, Business Analytics & Reporting"),
    "Operations Analyst": (_STRAT_OPS, HYUNDAI, _skills_business,
        "Operations Management, Business Analytics & Reporting, Process Improvement"),
    "Strategy Analyst": (_STRAT_OPS, HYUNDAI, _skills_business,
        "Business Strategy, Corporate Strategy, Business Analytics & Reporting"),
    "Business Analyst": (_BUSINESS_ANALYST, HYUNDAI, _skills_business,
        "Business Analytics & Reporting, Quantitative Analysis, Data Visualization"),
    "Program Management": (_PROGRAM_MGMT, HYUNDAI, _skills_business,
        "Project Management, Operations Management, Business Analytics & Reporting"),
    "Revenue / Sales Operations": (_STRAT_OPS, HYUNDAI, _skills_business,
        "Operations Management, Business Analytics & Reporting, Business Strategy"),
    "Product Operations": (_STRAT_OPS, HYUNDAI, _skills_business,
        "Operations Management, Business Analytics & Reporting, Business Strategy"),
    "Consulting": (_CONSULTING, HYUNDAI, _skills_business,
        "Business Strategy, Operations Management, Business Analytics & Reporting"),
    "Product Marketing": (_MARKETING, MARKETING_PROJECT, _skills_marketing,
        "Marketing Strategy, Business Analytics & Reporting, Market Research"),
    "Marketing Operations": (_MARKETING, MARKETING_PROJECT, _skills_marketing,
        "Marketing Strategy, Business Analytics & Reporting, Market Research"),
    "Finance / FP&A": (_GENERAL, HYUNDAI, _skills_business,
        "Corporate Finance, Business Analytics & Reporting, Quantitative Analysis"),
    "Customer Success": (_GENERAL, HYUNDAI, _skills_business,
        "Business Analytics & Reporting, Operations Management, Business Strategy"),
    "General Business": (_GENERAL, HYUNDAI, _skills_business,
        "Business Analytics & Reporting, Operations Management, Quantitative Analysis"),
}


def base_resume() -> ResumeData:
    return ResumeData(
        summary=_GENERAL,
        experiences=_experiences(),
        coursework="Business Analytics & Reporting, Operations Management, Quantitative Analysis",
        projects=[HYUNDAI],
        leadership_bullets=list(LEADERSHIP),
        skills=_skills_business(),
    )


def tailor_for_family(family: str) -> ResumeData:
    """Return a ResumeData tailored to the given role family."""
    summary, project, skills_fn, coursework = _FAMILY_CONFIG.get(
        family, _FAMILY_CONFIG["General Business"]
    )
    data = ResumeData(
        summary=summary,
        experiences=_experiences(),
        coursework=coursework,
        projects=[deepcopy(project)],
        leadership_bullets=list(LEADERSHIP),
        skills=skills_fn(),
    )

    # Marketing families: lead with BB Wellness (already first), keep order.
    # Business-analyst families: no reorder needed (Thomson Reuters + Beyond Key strong).
    return data
