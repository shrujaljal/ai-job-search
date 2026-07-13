from dataclasses import dataclass, field
from typing import List


@dataclass
class ExperienceEntry:
    company: str
    role: str
    date: str
    bullets: List[str] = field(default_factory=list)


@dataclass
class ProjectEntry:
    title: str
    bullets: List[str] = field(default_factory=list)


@dataclass
class SkillCategory:
    name: str   # e.g. "Business Strategy"
    skills: str  # e.g. "Strategic Planning, Market Research, ..."


@dataclass
class ResumeData:
    # Header
    name: str = "SHRUJAL AGARWAL"
    location: str = "California, USA"
    phone: str = "+1 (951)-347-5278"
    email: str = "sagar035@ucr.edu"
    linkedin_url: str = "https://www.linkedin.com/in/shrujalagarwal/"
    linkedin_text: str = "LinkedIn"
    portfolio_url: str = "https://shrujal-portfolio-gzvd.vercel.app/"
    portfolio_text: str = "Portfolio"
    github_url: str = "https://github.com/shrujaljal"
    github_text: str = "GitHub"

    # Sections
    summary: str = ""
    experiences: List[ExperienceEntry] = field(default_factory=list)

    # Education (fixed facts, only coursework changes per role)
    coursework: str = "Business Analytics & Reporting, Operations Management, Quantitative Analysis"

    # Projects & Leadership
    projects: List[ProjectEntry] = field(default_factory=list)
    leadership_bullets: List[str] = field(default_factory=list)

    # Skills
    skills: List[SkillCategory] = field(default_factory=list)

    # Honors & awards
    honors_awards: List[str] = field(default_factory=lambda: [
        "Beta Gamma Sigma Honor Society (Top 20% of MBA Class)",
        "2024 UCR Case Competition Winner",
        "Award for Best Graduate Teaching Assistant, Statistics",
        "Make A Difference Volunteer Educator, 150+ teaching hours",
    ])
