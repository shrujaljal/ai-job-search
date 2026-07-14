"""
Resume generator that produces Word documents matching Shrujal's resume template.

Layout: single borderless table, A4 page, 0.5" margins, 10pt Calibri.
Two-column grid: 7678 twips (left) + 2788 twips (right).
Section order: summary, education, skills, experience, projects/leadership,
honors/awards. Section headers are bold blue (#2F5496) with a bottom rule.
"""

from pathlib import Path
from copy import deepcopy

from docx import Document
from docx.shared import Pt, RGBColor, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from lxml import etree

from .models import ResumeData
from .content_rules import enforce

# ── Layout constants (twips; 1440 twips = 1 inch) ───────────────────────────
COL1_W = 8647
COL2_W = 1819
TOTAL_W = COL1_W + COL2_W

# ── Style constants ──────────────────────────────────────────────────────────
BLUE = "2F5496"
FONT = "Calibri"
SZ = 20        # half-points → 10pt
SZ_NAME = 32   # half-points → 16pt

TEMPLATE = Path(__file__).parent / "new_template.docx"
if not TEMPLATE.exists():
    TEMPLATE = Path(__file__).parent / "base_template.docx"


# ════════════════════════════════════════════════════════════════════════════
# Low-level XML helpers
# ════════════════════════════════════════════════════════════════════════════

def _rpr(bold=False, italic=False, color=None, sz=SZ) -> OxmlElement:
    """Build a <w:rPr> element."""
    rPr = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:cstheme"), "minorHAnsi")
    rPr.append(fonts)
    if bold:
        rPr.append(OxmlElement("w:b"))
        rPr.append(OxmlElement("w:bCs"))
    if italic:
        rPr.append(OxmlElement("w:i"))
        rPr.append(OxmlElement("w:iCs"))
    if color:
        c = OxmlElement("w:color")
        c.set(qn("w:val"), color)
        if color == BLUE:
            c.set(qn("w:themeColor"), "accent1")
            c.set(qn("w:themeShade"), "BF")
        rPr.append(c)
    s = OxmlElement("w:sz")
    s.set(qn("w:val"), str(sz))
    rPr.append(s)
    sCs = OxmlElement("w:szCs")
    sCs.set(qn("w:val"), str(sz))
    rPr.append(sCs)
    return rPr


def _run(text: str, bold=False, italic=False, color=None, sz=SZ) -> OxmlElement:
    """Build a <w:r> element with text."""
    r = OxmlElement("w:r")
    r.append(_rpr(bold=bold, italic=italic, color=color, sz=sz))
    t = OxmlElement("w:t")
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    r.append(t)
    return r


def _hyperlink_run(rel_id: str, display: str) -> OxmlElement:
    """Build a <w:hyperlink> element."""
    hl = OxmlElement("w:hyperlink")
    hl.set(qn("r:id"), rel_id)
    hl.set(qn("w:history"), "1")
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    style = OxmlElement("w:rStyle")
    style.set(qn("w:val"), "Hyperlink")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:cstheme"), "minorHAnsi")
    rPr.append(style)
    rPr.append(fonts)
    s = OxmlElement("w:sz")
    s.set(qn("w:val"), str(SZ))
    rPr.append(s)
    sCs = OxmlElement("w:szCs")
    sCs.set(qn("w:val"), str(SZ))
    rPr.append(sCs)
    r.append(rPr)
    t = OxmlElement("w:t")
    t.text = display
    r.append(t)
    hl.append(r)
    return hl


def _line_break() -> OxmlElement:
    return OxmlElement("w:br")


def _external_rel_id(doc: Document, url: str) -> str:
    return doc.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)


def _para(align=None, space_before=None, space_after=None, justify=False) -> OxmlElement:
    """Build a <w:p> element with optional paragraph properties."""
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    if justify:
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), "both")
        pPr.append(jc)
    elif align:
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), align)
        pPr.append(jc)
    if space_before is not None or space_after is not None:
        sp = OxmlElement("w:spacing")
        if space_before is not None:
            sp.set(qn("w:before"), str(space_before))
        if space_after is not None:
            sp.set(qn("w:after"), str(space_after))
        pPr.append(sp)
    p.append(pPr)
    return p


def _bullet_para(num_id: str, text: str) -> OxmlElement:
    """Build a bullet-list paragraph."""
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    style = OxmlElement("w:pStyle")
    style.set(qn("w:val"), "ListParagraph")
    pPr.append(style)
    numPr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    numId_el = OxmlElement("w:numId")
    numId_el.set(qn("w:val"), num_id)
    numPr.append(ilvl)
    numPr.append(numId_el)
    pPr.append(numPr)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "both")
    pPr.append(jc)
    rpr_el = _rpr(sz=SZ)
    pPr.append(rpr_el)
    p.append(pPr)
    p.append(_run(text, sz=SZ))
    return p


def _new_row(table) -> OxmlElement:
    """Add a blank row to the table and return its <w:tr> element."""
    tr = OxmlElement("w:tr")
    table._tbl.append(tr)
    return tr


def _span_cell(tr, content_paras: list, bottom_border=False) -> None:
    """Add a single cell spanning both columns to a row."""
    tc = OxmlElement("w:tc")
    tcPr = OxmlElement("w:tcPr")
    tcW = OxmlElement("w:tcW")
    tcW.set(qn("w:w"), "0")
    tcW.set(qn("w:type"), "auto")
    tcPr.append(tcW)
    gridSpan = OxmlElement("w:gridSpan")
    gridSpan.set(qn("w:val"), "2")
    tcPr.append(gridSpan)
    if bottom_border:
        tcBorders = OxmlElement("w:tcBorders")
        bot = OxmlElement("w:bottom")
        bot.set(qn("w:val"), "single")
        bot.set(qn("w:sz"), "4")
        bot.set(qn("w:space"), "0")
        bot.set(qn("w:color"), "auto")
        tcBorders.append(bot)
        tcPr.append(tcBorders)
    tc.append(tcPr)
    for p in content_paras:
        tc.append(p)
    tr.append(tc)


def _two_cells(tr, left_paras: list, right_paras: list,
               left_w=COL1_W, right_w=COL2_W) -> None:
    """Add two cells to a row."""
    for w, paras in [(left_w, left_paras), (right_w, right_paras)]:
        tc = OxmlElement("w:tc")
        tcPr = OxmlElement("w:tcPr")
        tcW = OxmlElement("w:tcW")
        tcW.set(qn("w:w"), str(w))
        tcW.set(qn("w:type"), "dxa")
        tcPr.append(tcW)
        tc.append(tcPr)
        for p in paras:
            tc.append(p)
        tr.append(tc)


# ════════════════════════════════════════════════════════════════════════════
# Section builders
# ════════════════════════════════════════════════════════════════════════════

def _build_header_row(table, data: ResumeData, num_id: str) -> None:
    tr = _new_row(table)
    p = _para(align="center")
    p.append(_run(data.name, bold=False, color=BLUE, sz=SZ_NAME))
    _span_cell(tr, [p])


def _build_contact_row(table, data: ResumeData, rel_ids: dict[str, str]) -> None:
    tr = _new_row(table)
    p = _para(align="center", space_before=60, space_after=60)
    p.append(_run(f"{data.phone} | ", sz=SZ))
    p.append(_hyperlink_run(rel_ids["email"], data.email))
    p.append(_run(" | ", sz=SZ))
    p.append(_hyperlink_run(rel_ids["linkedin"], data.linkedin_text))
    if data.portfolio_url:
        p.append(_run(" | ", sz=SZ))
        p.append(_hyperlink_run(rel_ids["portfolio"], data.portfolio_text))
    if data.github_url:
        p.append(_run(" | ", sz=SZ))
        p.append(_hyperlink_run(rel_ids["github"], data.github_text))
    _span_cell(tr, [p])


def _build_section_header(table, label: str, space_before=60) -> None:
    tr = _new_row(table)
    p = _para(space_before=space_before)
    p.find(qn("w:pPr")).append(_rpr(bold=True, color=BLUE, sz=SZ))
    p.append(_run(label, bold=True, color=BLUE, sz=SZ))
    _span_cell(tr, [p], bottom_border=True)


def _build_summary_row(table, data: ResumeData) -> None:
    tr = _new_row(table)
    p = _para(justify=True)
    p.append(_run(data.summary, sz=SZ))
    _span_cell(tr, [p])


def _build_experience_header(table, company: str, role: str, date: str) -> None:
    tr = _new_row(table)
    # Left: "Company | Role"
    lp = _para(space_before=120)
    lp.append(_run(f"{company} | ", bold=True, sz=SZ))
    lp.append(_run(role, bold=True, sz=SZ))
    # Right: date, right-aligned
    rp = _para(align="right", space_before=120)
    rp.append(_run(date, bold=True, sz=SZ))
    _two_cells(tr, [lp], [rp])


def _build_bullets_row(table, bullets: list[str], num_id: str) -> None:
    tr = _new_row(table)
    paras = [_bullet_para(num_id, b) for b in bullets]
    _span_cell(tr, paras)


def _build_education_row(table, data: ResumeData) -> None:
    tr = _new_row(table)
    paras = []

    # MBA line
    p1 = _para()
    p1.append(_run("Master of Business Administration (MBA)", bold=True, sz=SZ))
    p1.append(_run(
        " - University of California, Riverside (GPA: 3.8) — June 2026", sz=SZ
    ))
    paras.append(p1)

    # Honors
    p2 = _para()
    p2.append(_run("Honors: Beta Gamma Sigma Award, 2024 Case Competition Winner",
                   italic=True, sz=SZ))
    paras.append(p2)

    # Coursework + B.Tech on same paragraph (line break between)
    p3 = _para()
    p3.append(_run("Relevant Coursework: ", italic=True, sz=SZ))
    p3.append(_run(data.coursework, italic=True, sz=SZ))
    br = OxmlElement("w:br")
    p3.append(br)
    p3.append(_run("Bachelor of Technology, Biotechnology ", bold=True, sz=SZ))
    p3.append(_run(
        "– Vellore Institute of Technology, Vellore, India – Aug 2023", sz=SZ
    ))
    paras.append(p3)

    _span_cell(tr, paras)


def _build_projects_row(table, data: ResumeData, num_id: str) -> None:
    tr = _new_row(table)
    paras = []

    for proj in data.projects:
        # Project title
        tp = _para()
        tp.append(_run(proj.title, bold=True, sz=SZ))
        paras.append(tp)
        for b in proj.bullets:
            paras.append(_bullet_para(num_id, b))

    # Leadership bullets (inline after projects)
    if data.leadership_bullets:
        # Leadership title line
        lp = _para()
        lp.append(_run("UCR GSM Student Association | Marketing Lead", bold=True, sz=SZ))
        paras.append(lp)
        for b in data.leadership_bullets:
            paras.append(_bullet_para(num_id, b))

    _span_cell(tr, paras)


def _build_skills_row(table, data: ResumeData, num_id: str) -> None:
    tr = _new_row(table)
    paras = []
    for cat in data.skills:
        p = _bullet_para(num_id, "")
        # Remove the plain text run and replace with bold label + normal text
        for child in list(p):
            if child.tag == qn("w:r"):
                p.remove(child)
        r_bold = _run(f"{cat.name}:", bold=True, sz=SZ)
        r_text = _run(f" {cat.skills}", sz=SZ)
        p.append(r_bold)
        p.append(r_text)
        paras.append(p)
    _span_cell(tr, paras)


# Replacement builders for the current DOCX template. They intentionally appear
# after the legacy builders above so these definitions are the ones generate()
# uses at runtime.
def _build_education_row(table, data: ResumeData) -> None:
    tr = _new_row(table)
    left = []
    right = []

    p1 = _para()
    p1.append(_run(
        "Master of Business Administration (STEM MBA) - University of California, Riverside",
        bold=True, sz=SZ,
    ))
    p1.append(_run(" GPA: 3.8", italic=True, sz=SZ))
    left.append(p1)

    p2 = _para()
    p2.append(_run(
        "Bachelor of Technology, Biotechnology - Vellore Institute of Technology, India",
        bold=True, sz=SZ,
    ))
    p2.append(_run(" GPA: 3.5", italic=True, sz=SZ))
    left.append(p2)

    d1 = _para(align="right")
    d1.append(_run("June 2026", bold=True, sz=SZ))
    right.append(d1)

    d2 = _para(align="right")
    d2.append(_run("Aug 2023", bold=True, sz=SZ))
    right.append(d2)

    _two_cells(tr, left, right)


def _build_projects_row(table, data: ResumeData, num_id: str) -> None:
    tr = _new_row(table)
    paras = []

    for proj in data.projects:
        tp = _para()
        tp.append(_run(proj.title, bold=True, sz=SZ))
        paras.append(tp)
        for b in proj.bullets:
            paras.append(_bullet_para(num_id, b))

    if data.leadership_bullets:
        lp = _para()
        lp.append(_run(
            "UCR GSM Student Association | Professional Development Lead",
            bold=True, sz=SZ,
        ))
        paras.append(lp)
        for b in data.leadership_bullets:
            paras.append(_bullet_para(num_id, b))

    _span_cell(tr, paras)


def _build_skills_row(table, data: ResumeData, num_id: str = "27") -> None:
    tr = _new_row(table)
    paras = []
    for cat in data.skills:
        p = _para(justify=True)
        p.append(_run(f"{cat.name}:", bold=True, sz=SZ))
        p.append(_run(f" {cat.skills}", sz=SZ))
        paras.append(p)
    _span_cell(tr, paras)


def _build_honors_row(table, data: ResumeData, num_id: str) -> None:
    tr = _new_row(table)
    paras = [_bullet_para(num_id, award) for award in data.honors_awards]
    _span_cell(tr, paras)


# ════════════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════════════

def generate(data: ResumeData, output_path: str) -> tuple[str, list[str]]:
    """
    Generate a .docx resume from ResumeData.

    Returns (output_path, warnings).
    Enforces 1-page content rules before generating.
    """
    data, warnings = enforce(data)

    doc = Document(str(TEMPLATE))

    # ── Grab existing relationship IDs for email + LinkedIn hyperlinks ───────
    # The template already has rId6 = email, rId7 = LinkedIn
    rel_ids = {
        "email": _external_rel_id(doc, f"mailto:{data.email}"),
        "linkedin": _external_rel_id(doc, data.linkedin_url),
    }
    if data.portfolio_url:
        rel_ids["portfolio"] = _external_rel_id(doc, data.portfolio_url)
    if data.github_url:
        rel_ids["github"] = _external_rel_id(doc, data.github_url)

    # ── Find the bullet numId used in the template ───────────────────────────
    # We reuse the existing numbering definition (numId=27 in the template)
    num_id = "27"

    # ── Clear all existing rows from the table ───────────────────────────────
    table = doc.tables[0]
    tbl = table._tbl
    for tr in list(tbl.findall(qn("w:tr"))):
        tbl.remove(tr)

    # ── Rebuild rows in order ────────────────────────────────────────────────
    _build_header_row(table, data, num_id)
    _build_contact_row(table, data, rel_ids)
    _build_section_header(table, "PROFESSIONAL SUMMARY")
    _build_summary_row(table, data)
    _build_section_header(table, "EDUCATION", space_before=120)
    _build_education_row(table, data)
    _build_section_header(table, "SKILLS", space_before=120)
    _build_skills_row(table, data, num_id)
    _build_section_header(table, "EXPERIENCE", space_before=120)
    for exp in data.experiences:
        _build_experience_header(table, exp.company, exp.role, exp.date)
        _build_bullets_row(table, exp.bullets, num_id)
    _build_section_header(table, "PROJECTS & LEADERSHIP", space_before=120)
    _build_projects_row(table, data, num_id)
    _build_section_header(table, "HONORS & AWARDS", space_before=120)
    _build_honors_row(table, data, num_id)

    doc.save(output_path)
    return output_path, warnings
