"""Quick smoke test — generates a sample resume and saves it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_engine import (
    ResumeData, ExperienceEntry, ProjectEntry, SkillCategory, generate
)

data = ResumeData(
    summary=(
        "MBA graduate from UC Riverside (GPA 3.8) with 3+ years of experience across "
        "strategy, analytics, and operations within Fortune 500 organizations and startup "
        "environments. Skilled at translating ambiguous business problems into fact-based "
        "analysis, SQL-driven reporting, and executive-ready recommendations. Proven track "
        "record partnering cross-functionally with finance, operations, and marketing "
        "stakeholders to land annual business plans, standardize KPIs, and drive measurable "
        "business performance."
    ),
    experiences=[
        ExperienceEntry(
            company="BB Wellness",
            role="Analyst Intern",
            date="Feb 2025 – Sep 2025",
            bullets=[
                "Defined go-to-market problem scope through market segmentation and competitive "
                "benchmarking across 6 competitors, translating market research into fact-based "
                "product positioning recommendations for leadership.",
                "Built SQL-driven KPI dashboards spanning 4 channels, establishing a centralized "
                "reporting framework that surfaced performance gaps and enabled leadership to "
                "prioritize strategic initiatives.",
                "Developed hypothesis-driven business cases and strategic roadmaps, partnering "
                "with marketing, content, and operations stakeholders to align 10+ cross-functional "
                "initiatives against weekly OKRs.",
            ],
        ),
        ExperienceEntry(
            company="Thomson Reuters",
            role="Analyst – Global Operations",
            date="Oct 2023 – Jun 2024",
            bullets=[
                "Built 15+ SQL and Excel reporting frameworks adopted across 3 global business "
                "units, reducing manual reporting effort by approximately 30% and improving "
                "executive visibility into business performance.",
                "Partnered with finance, procurement, and operations stakeholders across 4 regions "
                "to standardize KPIs and support Quarterly Business Reviews, budgeting, and annual "
                "business planning.",
                "Prepared executive summaries translating complex, multi-source analyses into "
                "structured, compelling business recommendations for senior leadership.",
            ],
        ),
        ExperienceEntry(
            company="Goldman Sachs",
            role="STEM Intern – Asset & Wealth Management",
            date="Feb 2023 – Jun 2023",
            bullets=[
                "Built Qlik Sense dashboards consolidating 5+ operational data sources, improving "
                "executive visibility into business performance and reporting cadence across AWM.",
                "Identified process gaps through structured workflow analysis using Excel, JIRA, "
                "and Qlik Sense, strengthening compliance reporting, operational controls, and governance.",
                "Developed operational trackers monitoring hundreds of client commitments, improving "
                "workflow transparency and cross-team reporting consistency.",
            ],
        ),
        ExperienceEntry(
            company="Beyond Key",
            role="Data Analyst Intern",
            date="Jun 2022 – Aug 2022",
            bullets=[
                "Analyzed business datasets using SQL, Python, and Excel, and built Tableau "
                "dashboards enabling real-time performance monitoring for healthcare clients.",
            ],
        ),
    ],
    coursework="Business Analytics & Reporting, Operations Management, Quantitative Analysis",
    projects=[
        ProjectEntry(
            title="Hyundai Rotem Operations Consulting Project",
            bullets=[
                "Led a strategy consulting engagement analyzing manufacturing operations, inventory "
                "flows, and capacity constraints through process mapping and stakeholder interviews.",
                "Developed phased operational roadmaps, KPI frameworks, and executive recommendations "
                "that improved scalability, operational efficiency, and stakeholder alignment.",
            ],
        )
    ],
    leadership_bullets=[
        "Launched the school's first newsletter and podcast, designing editorial strategy, "
        "distribution workflows, and performance dashboards that improved audience engagement.",
    ],
    skills=[
        SkillCategory(
            "Business Strategy",
            "Business Strategy, Strategic Planning, Annual Business Planning, Strategic Initiatives, "
            "Business Case Development, Market Research, Strategic Roadmapping, Stakeholder Management",
        ),
        SkillCategory(
            "Analytics & Reporting",
            "SQL, Python, Advanced Excel (Pivot Tables, XLOOKUP, Power Query), Dashboard Development "
            "(Tableau, Qlik Sense), KPI Reporting, Business Performance Analysis, Statistical Analysis",
        ),
        SkillCategory(
            "Operations & Execution",
            "Cross-Functional Leadership, Program Management, Process Improvement, Operational "
            "Excellence, OKR Design & Tracking, Change Management, Resource Planning",
        ),
        SkillCategory(
            "Tools & AI",
            "ChatGPT, Claude, Gemini, Excel Copilot, n8n Automation, Salesforce, SAP Ariba, "
            "JIRA, HubSpot, PowerPoint",
        ),
    ],
)

out = Path(__file__).parent.parent / "output" / "test_resume.docx"
out.parent.mkdir(exist_ok=True)

path, warnings = generate(data, str(out))
print(f"Generated: {path}")
if warnings:
    print("Warnings:")
    for w in warnings:
        print(f"  • {w}")
else:
    print("No content warnings — all within limits.")
