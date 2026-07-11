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
TOKEN_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def _set_rel_target(doc, rel_id: str, target: str) -> None:
    try:
        doc.part.rels[rel_id]._target = target
    except Exception:
        pass


def render_docx(context: dict, output_path: str, template_path: str | Path | None = None) -> str:
    """Build the default-template DOCX from a résumé context. Returns the path."""
    if template_path:
        return render_token_docx(context, output_path, template_path)

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

    # Summary
    _build_section_header(table, "PROFESSIONAL SUMMARY")
    tr = _new_row(table)
    p = _para(justify=True)
    p.append(_run(context.get("summary", ""), sz=SZ))
    _span_cell(tr, [p])

    # Experience
    _build_section_header(table, "EXPERIENCE", space_before=120)
    for e in context.get("experiences", []):
        _build_experience_header(table, e.get("company", ""), e.get("role", ""), e.get("date", ""))
        _build_bullets_row(table, e.get("bullets", []), NUM_ID)

    # Education
    _build_section_header(table, "EDUCATION", space_before=120)
    tr = _new_row(table)
    paras = []
    for i, ed in enumerate(context.get("education", [])):
        deg = ed.get("degree", "")
        if ed.get("field"):
            deg = f"{deg}, {ed['field']}" if deg else ed["field"]
        tail = ""
        if ed.get("institution"):
            tail += f" - {ed['institution']}"
        if ed.get("gpa"):
            tail += f" (GPA: {ed['gpa']})"
        if ed.get("graduation"):
            tail += f" — {ed['graduation']}"
        pe = _para()
        pe.append(_run(deg, bold=True, sz=SZ))
        if tail:
            pe.append(_run(tail, sz=SZ))
        paras.append(pe)
        if ed.get("honors"):
            ph = _para()
            ph.append(_run("Honors: " + ", ".join(ed["honors"]), italic=True, sz=SZ))
            paras.append(ph)
        if i == 0 and context.get("coursework"):
            pc = _para()
            pc.append(_run("Relevant Coursework: ", italic=True, sz=SZ))
            pc.append(_run(context["coursework"], italic=True, sz=SZ))
            paras.append(pc)
    _span_cell(tr, paras)

    # Projects & Leadership
    _build_section_header(table, "PROJECTS & LEADERSHIP", space_before=120)
    tr = _new_row(table)
    paras = []
    for proj in context.get("projects", []):
        tp = _para()
        tp.append(_run(proj.get("title", ""), bold=True, sz=SZ))
        paras.append(tp)
        for b in proj.get("bullets", []):
            paras.append(_bullet_para(NUM_ID, b))
    for ld in context.get("leadership", []):
        title = " | ".join([x for x in [ld.get("organization", ""), ld.get("role", "")] if x])
        lp = _para()
        lp.append(_run(title, bold=True, sz=SZ))
        paras.append(lp)
        for b in ld.get("bullets", []):
            paras.append(_bullet_para(NUM_ID, b))
    _span_cell(tr, paras)

    # Skills
    _build_section_header(table, "SKILLS", space_before=120)
    tr = _new_row(table)
    paras = []
    for cat in context.get("skills", []):
        p = _bullet_para(NUM_ID, "")
        for child in list(p):
            if child.tag == qn("w:r"):
                p.remove(child)
        p.append(_run(f"{cat.get('name', '')}:", bold=True, sz=SZ))
        p.append(_run(f" {cat.get('items', '')}", sz=SZ))
        paras.append(p)
    _span_cell(tr, paras)

    doc.save(output_path)
    return output_path


# ── Cross-platform PDF ────────────────────────────────────────────────────────
def render_token_docx(context: dict, output_path: str, template_path: str | Path) -> str:
    """Render a user-uploaded DOCX template containing {{token}} placeholders."""
    doc = Document(str(template_path))
    values = _token_values(context)

    for paragraph in doc.paragraphs:
        _replace_tokens_in_paragraph(paragraph, values)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _replace_tokens_in_paragraph(paragraph, values)

    doc.save(output_path)
    return output_path


def _token_values(context: dict) -> dict[str, str]:
    ident = context.get("identity", {})
    links = ident.get("links", []) or []
    link_text = "\n".join(
        " - ".join([x for x in [link.get("label", ""), link.get("url", "")] if x])
        for link in links
    )
    contact_bits = [ident.get("location", ""), ident.get("phone", ""), ident.get("email", "")]
    if link_text:
        contact_bits.append(link_text)

    return {
        "name": ident.get("name", ""),
        "location": ident.get("location", ""),
        "phone": ident.get("phone", ""),
        "email": ident.get("email", ""),
        "links": link_text,
        "contact": " | ".join([bit for bit in contact_bits if bit]),
        "summary": context.get("summary", ""),
        "experience": _format_experience(context.get("experiences", [])),
        "education": _format_education(context.get("education", [])),
        "coursework": context.get("coursework", ""),
        "projects": _format_titled_bullets(context.get("projects", []), "title"),
        "leadership": _format_titled_bullets(context.get("leadership", []), "organization"),
        "skills": _format_skills(context.get("skills", [])),
        "family": context.get("family", ""),
    }


def _replace_tokens_in_paragraph(paragraph, values: dict[str, str]) -> None:
    text = paragraph.text
    if "{{" not in text:
        return
    replaced = TOKEN_RE.sub(lambda m: values.get(m.group(1), ""), text)
    for run in paragraph.runs:
        run.text = ""
    run = paragraph.add_run()
    lines = replaced.splitlines() or [""]
    for i, line in enumerate(lines):
        if i:
            run.add_break()
        run.add_text(line)


def _format_experience(experiences: list[dict]) -> str:
    blocks = []
    for exp in experiences:
        header = " | ".join([x for x in [exp.get("company", ""), exp.get("role", ""), exp.get("date", "")] if x])
        bullets = "\n".join(f"- {b}" for b in exp.get("bullets", []) if b)
        blocks.append("\n".join([x for x in [header, bullets] if x]))
    return "\n\n".join(blocks)


def _format_education(education: list[dict]) -> str:
    blocks = []
    for ed in education:
        degree = ed.get("degree", "")
        if ed.get("field"):
            degree = f"{degree}, {ed['field']}" if degree else ed["field"]
        line = " - ".join([x for x in [degree, ed.get("institution", ""), ed.get("graduation", "")] if x])
        if ed.get("gpa"):
            line = f"{line} (GPA: {ed['gpa']})" if line else f"GPA: {ed['gpa']}"
        honors = ", ".join(ed.get("honors", []))
        blocks.append("\n".join([x for x in [line, f"Honors: {honors}" if honors else ""] if x]))
    return "\n\n".join(blocks)


def _format_titled_bullets(items: list[dict], title_key: str) -> str:
    blocks = []
    for item in items:
        title = item.get(title_key, "")
        if title_key == "organization" and item.get("role"):
            title = " | ".join([x for x in [title, item.get("role", "")] if x])
        bullets = "\n".join(f"- {b}" for b in item.get("bullets", []) if b)
        blocks.append("\n".join([x for x in [title, bullets] if x]))
    return "\n\n".join(blocks)


def _format_skills(skills: list[dict]) -> str:
    return "\n".join(
        f"{cat.get('name', '')}: {cat.get('items', '')}".strip(": ")
        for cat in skills
        if cat.get("name") or cat.get("items")
    )


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
