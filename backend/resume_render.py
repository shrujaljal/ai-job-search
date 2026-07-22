"""
Render a résumé context (from resume_builder) into DOCX, then PDF.

DOCX: the default template reuses V1's exact layout (borderless table, blue
section headers, two-column job rows) but is fully driven by the context —
identity, education, and leadership are generic, not hardcoded.

PDF: cross-platform. Prefers LibreOffice headless (Windows/macOS/Linux); on
Windows, falls back to Microsoft Word via pywin32 if LibreOffice isn't found.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from resume_engine.generator import (  # low-level, generic helpers
    _run, _para, _bullet_para, _new_row, _span_cell, _hyperlink_run,
    _build_section_header, _build_experience_header, _build_bullets_row,
    SZ,
)

NUM_ID = "27"  # bullet numbering defined in base_template.docx
EMAIL_REL, LINK_REL = "rId6", "rId7"


def _set_rel_target(doc, rel_id: str, target: str) -> None:
    try:
        doc.part.rels[rel_id]._target = target
    except Exception:
        pass


def render_docx(context: dict, output_path: str) -> str:
    """Build the default-template DOCX from a résumé context. Returns the path."""
    ident = context.get("identity", {})
    doc = Document(str(Path(__file__).parent / "resume_engine" / "base_template.docx"))

    # Point the template's two hyperlinks at this user's email + first link.
    email = ident.get("email", "")
    links = ident.get("links", []) or []
    link0 = links[0] if links else {"label": "", "url": ""}
    if email:
        _set_rel_target(doc, EMAIL_REL, f"mailto:{email}")
    if link0.get("url"):
        _set_rel_target(doc, LINK_REL, link0["url"])

    table = doc.tables[0]
    tbl = table._tbl
    for tr in list(tbl.findall(qn("w:tr"))):
        tbl.remove(tr)

    # Header
    tr = _new_row(table)
    from resume_engine.generator import BLUE, SZ_NAME
    p = _para(align="center")
    p.append(_run(ident.get("name", ""), color=BLUE, sz=SZ_NAME))
    _span_cell(tr, [p])

    # Contact line
    tr = _new_row(table)
    p = _para(align="center", space_before=60, space_after=60)
    bits = [b for b in [ident.get("location", ""), ident.get("phone", "")] if b]
    p.append(_run((" | ".join(bits) + " | ") if bits else "", sz=SZ))
    if email:
        p.append(_hyperlink_run(EMAIL_REL, email))
    if link0.get("url"):
        p.append(_run(" | ", sz=SZ))
        p.append(_hyperlink_run(LINK_REL, link0.get("label") or "Link"))
    _span_cell(tr, [p])

    blueprint = context.get("resume_blueprint", {})
    order = blueprint.get("section_order") or [
        "summary", "experience", "education", "projects_leadership", "skills"
    ]
    headings = blueprint.get("section_headings", {})
    rendered = 0
    for key in order:
        if not _has_section(context, key):
            continue
        title = headings.get(key) or _default_heading(key, context)
        _build_section_header(table, title, space_before=0 if rendered == 0 else 120)
        _render_section(table, context, key)
        rendered += 1

    doc.save(output_path)
    return output_path


def _has_section(context: dict, key: str) -> bool:
    if key == "summary":
        return bool(context.get("summary"))
    if key == "experience":
        return bool(context.get("experiences"))
    if key in {"education", "projects", "leadership", "skills", "honors"}:
        return bool(context.get(key))
    if key == "projects_leadership":
        return bool(context.get("projects") or context.get("leadership"))
    if key.startswith("custom:"):
        custom_id = key.split(":", 1)[1]
        return any(
            section.get("id") == custom_id and section.get("lines")
            for section in context.get("custom_sections", [])
        )
    return False


def _default_heading(key: str, context: dict) -> str:
    defaults = {
        "summary": "Professional Summary",
        "experience": "Experience",
        "education": "Education",
        "projects": "Projects",
        "leadership": "Leadership",
        "projects_leadership": "Projects & Leadership",
        "skills": "Skills",
        "honors": "Honors & Awards",
    }
    if key.startswith("custom:"):
        custom_id = key.split(":", 1)[1]
        match = next(
            (section for section in context.get("custom_sections", []) if section.get("id") == custom_id),
            {},
        )
        return match.get("title", "Additional Information")
    return defaults.get(key, key.replace("_", " ").title())


def _render_section(table, context: dict, key: str) -> None:
    if key == "summary":
        tr = _new_row(table)
        p = _para(justify=True)
        p.append(_run(context.get("summary", ""), sz=SZ))
        _span_cell(tr, [p])
    elif key == "experience":
        for experience in context.get("experiences", []):
            _build_experience_header(
                table,
                experience.get("company", ""),
                experience.get("role", ""),
                experience.get("date", ""),
            )
            _build_bullets_row(table, experience.get("bullets", []), NUM_ID)
    elif key == "education":
        _render_education(table, context)
    elif key in {"projects", "leadership", "projects_leadership"}:
        include_projects = key in {"projects", "projects_leadership"}
        include_leadership = key in {"leadership", "projects_leadership"}
        _render_projects_leadership(table, context, include_projects, include_leadership)
    elif key == "skills":
        _render_skills(table, context.get("skills", []))
    elif key == "honors":
        _build_bullets_row(table, context.get("honors", []), NUM_ID)
    elif key.startswith("custom:"):
        custom_id = key.split(":", 1)[1]
        section = next(
            (item for item in context.get("custom_sections", []) if item.get("id") == custom_id),
            {},
        )
        lines = [re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", "", line) for line in section.get("lines", [])]
        _build_bullets_row(table, lines, NUM_ID)


def _render_education(table, context: dict) -> None:
    tr = _new_row(table)
    paragraphs = []
    for index, education in enumerate(context.get("education", [])):
        degree = education.get("degree", "")
        if education.get("field"):
            degree = f"{degree}, {education['field']}" if degree else education["field"]
        tail = ""
        if education.get("institution"):
            tail += f" - {education['institution']}"
        if education.get("gpa"):
            tail += f" (GPA: {education['gpa']})"
        if education.get("graduation"):
            tail += f" - {education['graduation']}"
        paragraph = _para()
        paragraph.append(_run(degree, bold=True, sz=SZ))
        if tail:
            paragraph.append(_run(tail, sz=SZ))
        paragraphs.append(paragraph)
        if education.get("honors"):
            honors = _para()
            honors.append(_run("Honors: " + ", ".join(education["honors"]), italic=True, sz=SZ))
            paragraphs.append(honors)
        if index == 0 and context.get("coursework"):
            coursework = _para()
            coursework.append(_run("Relevant Coursework: ", italic=True, sz=SZ))
            coursework.append(_run(context["coursework"], italic=True, sz=SZ))
            paragraphs.append(coursework)
    _span_cell(tr, paragraphs)


def _render_projects_leadership(
    table, context: dict, include_projects: bool, include_leadership: bool
) -> None:
    tr = _new_row(table)
    paragraphs = []
    if include_projects:
        for project in context.get("projects", []):
            title = _para()
            title.append(_run(project.get("title", ""), bold=True, sz=SZ))
            paragraphs.append(title)
            paragraphs.extend(_bullet_para(NUM_ID, bullet) for bullet in project.get("bullets", []))
    if include_leadership:
        for leadership in context.get("leadership", []):
            text = " | ".join(
                value for value in [leadership.get("organization", ""), leadership.get("role", "")] if value
            )
            title = _para()
            title.append(_run(text, bold=True, sz=SZ))
            paragraphs.append(title)
            paragraphs.extend(_bullet_para(NUM_ID, bullet) for bullet in leadership.get("bullets", []))
    _span_cell(tr, paragraphs)


def _render_skills(table, skills: list[dict]) -> None:
    tr = _new_row(table)
    paragraphs = []
    for category in skills:
        paragraph = _bullet_para(NUM_ID, "")
        for child in list(paragraph):
            if child.tag == qn("w:r"):
                paragraph.remove(child)
        paragraph.append(_run(f"{category.get('name', '')}:", bold=True, sz=SZ))
        paragraph.append(_run(f" {category.get('items', '')}", sz=SZ))
        paragraphs.append(paragraph)
    _span_cell(tr, paragraphs)


# ── Cross-platform PDF ────────────────────────────────────────────────────────
def _find_soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    # Common Windows install paths
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if Path(p).exists():
            return p
    return None


def docx_to_pdf(docx_path: str | Path, pdf_path: str | Path) -> None:
    """Convert DOCX to PDF via LibreOffice, or MS Word on Windows as a fallback."""
    # Absolute paths — Word/LibreOffice resolve relative paths from their own cwd.
    docx_path, pdf_path = Path(docx_path).resolve(), Path(pdf_path).resolve()
    soffice = _find_soffice()
    if soffice:
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir",
             str(pdf_path.parent), str(docx_path)],
            check=True, capture_output=True, timeout=120)
        produced = pdf_path.parent / (docx_path.stem + ".pdf")
        if produced != pdf_path and produced.exists():
            produced.replace(pdf_path)
        return
    if os.name == "nt":
        _word_to_pdf(docx_path, pdf_path)
        return
    raise RuntimeError("No PDF converter found. Install LibreOffice for PDF export.")


def _word_to_pdf(docx_path: Path, pdf_path: Path) -> None:
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    word = doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(docx_path), ReadOnly=1)
        doc.SaveAs(str(pdf_path), FileFormat=17)  # wdFormatPDF
    finally:
        if doc is not None:
            doc.Close(False)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()
