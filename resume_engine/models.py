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
    phone: str = "(951)-347-5278"
    email: str = "shrujalag.gms@gmail.com"
    linkedin_url: str = "https://www.linkedin.com/in/shrujalagarwal/"
    linkedin_text: str = "LinkedIn"

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
