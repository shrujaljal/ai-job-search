"""Import and merge profile facts from DOCX, PDF, and Markdown resumes."""

from __future__ import annotations

import re
import shutil
from copy import deepcopy
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph

import config

SUPPORTED_SUFFIXES = {".docx", ".pdf", ".md", ".markdown"}
DEFAULT_ORDER = ["summary", "experience", "education", "projects_leadership", "skills"]
DEFAULT_HEADINGS = {
    "summary": "Professional Summary",
    "experience": "Experience",
    "education": "Education",
    "projects": "Projects",
    "leadership": "Leadership",
    "projects_leadership": "Projects & Leadership",
    "skills": "Skills",
    "honors": "Honors & Awards",
}
SECTION_ALIASES = {
    "summary": {"summary", "professional summary", "profile", "professional profile", "about", "objective", "career objective"},
    "experience": {"experience", "professional experience", "work experience", "employment", "employment history", "career history"},
    "education": {"education", "academic background", "academic experience", "qualifications"},
    "skills": {"skills", "technical skills", "core skills", "core competencies", "competencies", "tools", "technologies"},
    "projects": {"projects", "selected projects", "academic projects", "professional projects"},
    "leadership": {"leadership", "leadership experience", "activities", "volunteer experience", "volunteering", "community involvement"},
    "projects_leadership": {"projects and leadership", "projects leadership", "projects & leadership"},
    "honors": {"honors", "awards", "honors and awards", "honors & awards", "achievements", "awards and recognition"},
}
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
URL_RE = re.compile(r"(?:https?://|www\.|linkedin\.com/)\S+", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d().\s-]{7,}\d)")
DATE_RE = re.compile(r"\b(?:19|20)\d{2}\b|\bpresent\b|\bcurrent\b", re.I)
ROLE_RE = re.compile(r"\b(analyst|manager|director|lead|intern|consultant|associate|specialist|coordinator|assistant|engineer|officer|advisor|representative|founder|president)\b", re.I)
BULLET_RE = re.compile(r"^\s*(?:[-*\u2022\u25aa\u25e6\u2023]|\d+[.)])\s+")


@dataclass
class Line:
    text: str
    heading: bool = False
    level: int = 0


def extract_lines(path: Path) -> list[Line]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError("Supported profile files are DOCX, PDF, MD, and Markdown.")
    if suffix == ".docx":
        return _docx_lines(path)
    if suffix == ".pdf":
        return _pdf_lines(path)
    return _markdown_lines(path)


def _docx_lines(path: Path) -> list[Line]:
    try:
        document = Document(str(path))
    except (BadZipFile, PackageNotFoundError, ValueError) as exc:
        raise ValueError("The DOCX file is damaged or is not a Word document.") from exc
    result: list[Line] = []
    for block in document.iter_inner_content():
        if isinstance(block, Paragraph):
            line = _docx_paragraph_line(block)
            if line:
                result.append(line)
            continue
        if not isinstance(block, Table):
            continue
        for row in block.rows:
            unique_cells = list({id(cell._tc): cell for cell in row.cells}.values())
            if len(unique_cells) == 1:
                for paragraph in unique_cells[0].paragraphs:
                    line = _docx_paragraph_line(paragraph)
                    if line:
                        result.append(line)
                continue
            values = [cell.text.strip().replace("\n", " | ") for cell in unique_cells if cell.text.strip()]
            if values:
                text = " | ".join(values)
                result.append(Line(text, _looks_like_heading(text)))
    return result


def _docx_paragraph_line(paragraph: Paragraph) -> Line | None:
    text = paragraph.text.strip()
    if not text:
        return None
    style = (paragraph.style.name or "").lower() if paragraph.style else ""
    if "list" in style and not BULLET_RE.match(text):
        text = f"- {text}"
    heading = style.startswith("heading") or _looks_like_heading(text)
    level_match = re.search(r"(\d+)", style)
    return Line(text, heading, int(level_match.group(1)) if level_match else 0)


def _pdf_lines(path: Path) -> list[Line]:
    try:
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError
    except ImportError as exc:
        raise ValueError("PDF import requires pypdf. Run python run.py --install.") from exc
    try:
        reader = PdfReader(str(path))
        result = []
        for page in reader.pages:
            for raw in (page.extract_text() or "").splitlines():
                text = raw.strip()
                if text:
                    result.append(Line(text, _looks_like_heading(text)))
    except (PyPdfError, OSError, ValueError) as exc:
        raise ValueError("The PDF is damaged, encrypted, or has no readable structure.") from exc
    return result


def _markdown_lines(path: Path) -> list[Line]:
    result = []
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        text = raw.strip()
        if not text:
            continue
        match = re.match(r"^(#{1,6})\s+(.+)$", text)
        if match:
            result.append(Line(match.group(2).strip(), True, len(match.group(1))))
        else:
            result.append(Line(text, False, 0))
    return result


def _looks_like_heading(text: str) -> bool:
    clean = _heading_key(text)
    if _canonical_heading(clean):
        return True
    return len(text) <= 45 and len(text.split()) <= 6 and text.isupper() and not BULLET_RE.match(text)


def _heading_key(text: str) -> str:
    return re.sub(r"[^a-z0-9&]+", " ", text.lower()).strip().replace("&", "and")


def _canonical_heading(text: str) -> str | None:
    clean = _heading_key(text)
    for key, aliases in SECTION_ALIASES.items():
        if clean in aliases:
            return key
    return None


def parse_resume(lines: list[Line], filename: str) -> dict:
    sections: dict[str, list[str]] = {}
    headings: dict[str, str] = {}
    order: list[str] = []
    preamble: list[str] = []
    custom_titles: dict[str, str] = {}
    current: str | None = None

    for line in lines:
        canonical = _canonical_heading(line.text) if line.heading else None
        if canonical:
            current = canonical
            sections.setdefault(current, [])
            headings.setdefault(current, line.text.strip())
            if current not in order:
                order.append(current)
            continue
        if line.heading and current is None and not sections and len(line.text.split()) <= 5:
            preamble.append(line.text)
            continue
        if line.heading and current == "experience" and line.level != 1:
            sections[current].append(line.text)
            continue
        if line.heading and (line.level == 1 or current is None):
            slug = _slug(line.text)
            current = f"custom:{slug}"
            sections.setdefault(current, [])
            custom_titles[current] = line.text.strip()
            if current not in order:
                order.append(current)
            continue
        if line.heading and current:
            sections[current].append(line.text)
            continue
        if current:
            sections[current].append(line.text)
        else:
            preamble.append(line.text)

    all_text = "\n".join(line.text for line in lines)
    identity = _identity(preamble, all_text)
    custom_sections = [
        {"id": key.split(":", 1)[1], "title": custom_titles[key], "lines": _unique(sections[key])}
        for key in order if key.startswith("custom:") and sections.get(key)
    ]
    parsed = {
        "identity": identity,
        "summary": _summary(sections.get("summary", [])),
        "experience": _experience(sections.get("experience", [])),
        "education": _education(sections.get("education", [])),
        "projects": _titled_bullets(sections.get("projects", []), "title"),
        "leadership": _titled_bullets(sections.get("leadership", []), "organization"),
        "skills": _skills(sections.get("skills", [])),
        "honors": _bullet_values(sections.get("honors", [])),
        "custom_sections": custom_sections,
        "resume_blueprint": {
            "source_files": [filename],
            "section_order": order or DEFAULT_ORDER.copy(),
            "section_headings": {**DEFAULT_HEADINGS, **headings, **custom_titles},
        },
    }
    if "projects_leadership" in sections:
        combined = sections["projects_leadership"]
        parsed["projects"] = _titled_bullets(combined, "title")
    return parsed


def _identity(preamble: list[str], all_text: str) -> dict:
    email = (EMAIL_RE.search(all_text).group(0) if EMAIL_RE.search(all_text) else "")
    phone_match = PHONE_RE.search(all_text)
    phone = phone_match.group(0).strip() if phone_match else ""
    urls = [match.rstrip(".,;)") for match in URL_RE.findall(all_text)]
    name = ""
    location = ""
    for text in preamble:
        has_contact = EMAIL_RE.search(text) or URL_RE.search(text) or PHONE_RE.search(text)
        if has_contact:
            cleaned = EMAIL_RE.sub("", text)
            cleaned = URL_RE.sub("", cleaned)
            cleaned = PHONE_RE.sub("", cleaned)
            candidates = [part.strip(" -|,") for part in re.split(r"[|\u2022]", cleaned)]
            location = location or next((part for part in candidates if part), "")
            continue
        if not name and 1 < len(text.split()) <= 5 and len(text) <= 60:
            name = text
        elif name and not location and len(text) <= 80:
            location = text
    links = []
    for url in _unique(urls):
        normalized_url = url if re.match(r"https?://", url, re.I) else f"https://{url}"
        links.append({
            "label": "LinkedIn" if "linkedin" in url.lower() else "Portfolio",
            "url": normalized_url,
        })
    return {"name": name, "email": email, "phone": phone, "location": location, "links": links}


def _summary(lines: list[str]) -> str:
    return " ".join(_clean_bullet(line) for line in lines if line.strip()).strip()


def _experience(lines: list[str]) -> list[dict]:
    groups = _group_entries(lines)
    result = []
    for headers, bullets in groups:
        if not headers and not bullets:
            continue
        header_text = " | ".join(headers)
        parts = [part.strip() for part in re.split(r"\s*[|\u2022]\s*", header_text) if part.strip()]
        date = next((part for part in reversed(parts) if DATE_RE.search(part)), "")
        role = next((part for part in parts if ROLE_RE.search(part)), "")
        company = next((part for part in parts if part not in {date, role}), "")
        if not role and len(parts) > 1:
            role = parts[1]
        if not company and parts:
            company = parts[0]
        result.append({"company": company, "role": role, "date": date, "bullets": _unique(bullets)})
    return result


def _education(lines: list[str]) -> list[dict]:
    groups = _group_entries(lines)
    result = []
    for headers, bullets in groups:
        values = headers + bullets
        if not values:
            continue
        joined = " | ".join(values)
        parts = [part.strip() for part in re.split(r"\s*[|\u2022]\s*", joined) if part.strip()]
        graduation = next((part for part in parts if DATE_RE.search(part)), "")
        gpa_match = re.search(r"\bGPA\s*[:=]?\s*([0-4](?:\.\d{1,2})?)", joined, re.I)
        degree = next((part for part in parts if re.search(r"\b(bachelor|master|mba|phd|doctor|degree|b\.?s\.?|m\.?s\.?)\b", part, re.I)), "")
        institution = next((part for part in parts if re.search(r"\b(university|college|institute|school)\b", part, re.I)), "")
        honors = [part for part in parts if re.search(r"\b(honor|award|society|cum laude|dean)\b", part, re.I)]
        result.append({"degree": degree, "field": "", "institution": institution, "location": "", "graduation": graduation, "gpa": gpa_match.group(1) if gpa_match else "", "honors": _unique(honors)})
    return result


def _skills(lines: list[str]) -> list[dict]:
    result = []
    for line in lines:
        clean = _clean_bullet(line)
        if not clean:
            continue
        if ":" in clean:
            name, items = clean.split(":", 1)
        else:
            name, items = "Core", clean
        result.append({"name": name.strip(), "items": items.strip()})
    return result


def _titled_bullets(lines: list[str], title_key: str) -> list[dict]:
    result = []
    for headers, bullets in _group_entries(lines):
        title = " | ".join(headers).strip()
        if title or bullets:
            item = {title_key: title, "bullets": _unique(bullets)}
            if title_key == "organization":
                item["role"] = ""
            else:
                item["families"] = []
            result.append(item)
    return result


def _group_entries(lines: list[str]) -> list[tuple[list[str], list[str]]]:
    groups: list[tuple[list[str], list[str]]] = []
    headers: list[str] = []
    bullets: list[str] = []
    for raw in lines:
        if BULLET_RE.match(raw):
            bullets.append(_clean_bullet(raw))
        else:
            if bullets:
                groups.append((headers, bullets))
                headers, bullets = [], []
            headers.append(raw.strip())
    if headers or bullets:
        groups.append((headers, bullets))
    return groups


def _bullet_values(lines: list[str]) -> list[str]:
    return _unique(_clean_bullet(line) for line in lines)


def _clean_bullet(text: str) -> str:
    return BULLET_RE.sub("", text).strip()


def merge_profile(existing: dict, incoming_documents: list[dict]) -> tuple[dict, dict]:
    profile = _normalized_profile(existing)
    stats = {"files": len(incoming_documents), "items_added": 0, "duplicates_removed": 0, "sections_added": 0}
    first_source = not profile.get("resume_blueprint", {}).get("source_files")
    for incoming in incoming_documents:
        _merge_identity(profile["identity"], incoming.get("identity", {}))
        if incoming.get("summary") and not profile.get("summary"):
            profile["summary"] = incoming["summary"]
        for key, identity_fields in (
            ("experience", ("company", "role", "date")),
            ("education", ("institution", "degree")),
            ("projects", ("title",)),
            ("leadership", ("organization", "role")),
        ):
            _merge_entries(profile[key], incoming.get(key, []), identity_fields, stats)
        _merge_skills(profile["skills"], incoming.get("skills", []))
        profile["honors"] = _merge_unique(profile.get("honors", []), incoming.get("honors", []), stats)
        _merge_custom(profile["custom_sections"], incoming.get("custom_sections", []), stats)
        _merge_blueprint(profile["resume_blueprint"], incoming.get("resume_blueprint", {}), first_source)
        first_source = False
    _dedupe_all(profile, stats)
    return profile, stats


def _normalized_profile(profile: dict) -> dict:
    result = deepcopy(profile or {})
    result.setdefault("identity", {})
    for key in ("experience", "education", "projects", "leadership", "skills", "honors", "custom_sections"):
        result.setdefault(key, [])
    for key in ("experience", "education", "projects", "leadership"):
        result[key] = [item for item in result[key] if _entry_has_content(item)]
    result["skills"] = [
        item for item in result["skills"]
        if item.get("name") or _split_items(item.get("items", ""))
    ]
    result.setdefault("summary", "")
    blueprint = result.setdefault("resume_blueprint", {})
    blueprint.setdefault("source_files", [])
    blueprint.setdefault("section_order", DEFAULT_ORDER.copy())
    blueprint["section_headings"] = {
        **DEFAULT_HEADINGS,
        **blueprint.get("section_headings", {}),
    }
    return result


def _entry_has_content(item: dict) -> bool:
    return any(
        value for key, value in item.items()
        if key not in {"bullets", "honors", "families"}
    ) or any(
        value
        for key in ("bullets", "honors", "families")
        for value in item.get(key, [])
        if value
    )


def clean_profile(profile: dict) -> dict:
    """Normalize a manually edited profile and remove duplicate list items."""
    result = _normalized_profile(profile)
    _dedupe_all(result, {"duplicates_removed": 0})
    return result


def _merge_identity(existing: dict, incoming: dict) -> None:
    for key in ("name", "email", "phone", "location"):
        value = incoming.get(key, "")
        if value and (not existing.get(key) or existing.get(key) in {"Your Name", "you@example.com"}):
            existing[key] = value
    existing["links"] = _merge_links(existing.get("links", []), incoming.get("links", []))


def _merge_links(existing: list[dict], incoming: list[dict]) -> list[dict]:
    result = [link for link in existing if link.get("url")]
    seen = {link.get("url", "").lower().rstrip("/") for link in result}
    for link in incoming:
        normalized = link.get("url", "").lower().rstrip("/")
        if normalized and normalized not in seen:
            result.append(link)
            seen.add(normalized)
    return result


def _merge_entries(existing: list[dict], incoming: list[dict], fields: tuple[str, ...], stats: dict) -> None:
    for item in incoming:
        match = next((entry for entry in existing if _entries_match(entry, item, fields)), None)
        if match is None:
            clean = dict(item)
            clean["bullets"] = _unique(item.get("bullets", []))
            existing.append(clean)
            stats["items_added"] += len(clean["bullets"])
            continue
        for key, value in item.items():
            if key != "bullets" and value and not match.get(key):
                match[key] = value
        match["bullets"] = _merge_unique(match.get("bullets", []), item.get("bullets", []), stats)


def _entries_match(left: dict, right: dict, fields: tuple[str, ...]) -> bool:
    compared = False
    for field in fields:
        left_value = _normalize(_entry_value(left, field))
        right_value = _normalize(_entry_value(right, field))
        if field == "date" and (not left_value or not right_value):
            continue
        if not left_value or not right_value or left_value != right_value:
            return False
        compared = True
    return compared


def _entry_value(item: dict, field: str) -> str:
    if field == "date" and not item.get("date"):
        return " - ".join(value for value in [item.get("start", ""), item.get("end", "")] if value)
    return str(item.get(field, ""))


def _merge_skills(existing: list[dict], incoming: list[dict]) -> None:
    for category in incoming:
        name = category.get("name", "Core")
        match = next((item for item in existing if _normalize(item.get("name", "")) == _normalize(name)), None)
        new_items = _split_items(category.get("items", ""))
        if match is None:
            existing.append({"name": name, "items": ", ".join(new_items)})
        else:
            match["items"] = ", ".join(_unique([*_split_items(match.get("items", "")), *new_items]))


def _split_items(value: str | list[str]) -> list[str]:
    values = value if isinstance(value, list) else re.split(r"[,;|]", value)
    return [item.strip() for item in values if item.strip()]


def _merge_custom(existing: list[dict], incoming: list[dict], stats: dict) -> None:
    for section in incoming:
        match = next((item for item in existing if _normalize(item.get("title", "")) == _normalize(section.get("title", ""))), None)
        if match:
            match["lines"] = _merge_unique(match.get("lines", []), section.get("lines", []), stats)
        else:
            existing.append(section)
            stats["sections_added"] += 1


def _merge_blueprint(existing: dict, incoming: dict, replace_order: bool) -> None:
    existing.setdefault("source_files", [])
    existing["source_files"] = _unique([*existing["source_files"], *incoming.get("source_files", [])])
    existing.setdefault("section_order", DEFAULT_ORDER.copy())
    if replace_order and incoming.get("section_order"):
        existing["section_order"] = incoming["section_order"]
    else:
        for key in incoming.get("section_order", []):
            if key not in existing["section_order"]:
                existing["section_order"].append(key)
    existing.setdefault("section_headings", DEFAULT_HEADINGS.copy())
    for key, heading in incoming.get("section_headings", {}).items():
        if replace_order:
            existing["section_headings"][key] = heading
        else:
            existing["section_headings"].setdefault(key, heading)


def _merge_unique(existing: list[str], incoming: list[str], stats: dict | None = None) -> list[str]:
    result = [item.strip() for item in existing if item and item.strip()]
    for item in incoming:
        clean = item.strip() if isinstance(item, str) else ""
        if not clean:
            continue
        if any(_same_text(clean, current) for current in result):
            if stats is not None:
                stats["duplicates_removed"] += 1
            continue
        result.append(clean)
        if stats is not None:
            stats["items_added"] += 1
    return result


def _dedupe_all(profile: dict, stats: dict) -> None:
    for key in ("experience", "projects", "leadership"):
        for item in profile.get(key, []):
            before = len(item.get("bullets", []))
            item["bullets"] = _unique(item.get("bullets", []))
            stats["duplicates_removed"] += before - len(item["bullets"])
    before = len(profile.get("honors", []))
    profile["honors"] = _unique(profile.get("honors", []))
    stats["duplicates_removed"] += before - len(profile["honors"])
    for section in profile.get("custom_sections", []):
        before = len(section.get("lines", []))
        section["lines"] = _unique(section.get("lines", []))
        stats["duplicates_removed"] += before - len(section["lines"])
    for category in profile.get("skills", []):
        items = _split_items(category.get("items", ""))
        unique = _unique(items)
        stats["duplicates_removed"] += len(items) - len(unique)
        category["items"] = ", ".join(unique)


def _unique(values) -> list[str]:
    result: list[str] = []
    for value in values:
        clean = value.strip() if isinstance(value, str) else ""
        if clean and not any(_same_text(clean, current) for current in result):
            result.append(clean)
    return result


def _same_text(left: str, right: str) -> bool:
    a, b = _normalize(left), _normalize(right)
    if not a or not b:
        return not a and not b
    if a == b:
        return True
    return min(len(a), len(b)) >= 45 and SequenceMatcher(None, a, b).ratio() >= 0.9


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "section"


def save_source(source: Path, original_name: str) -> str:
    directory = config.DATA_DIR / "profile_sources"
    directory.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._ -]+", "", Path(original_name).name).strip(" .") or "profile-source"
    destination = directory / safe
    counter = 2
    while destination.exists():
        destination = directory / f"{Path(safe).stem}-{counter}{Path(safe).suffix}"
        counter += 1
    shutil.copyfile(source, destination)
    return destination.name


def enrichment_prompt(profile: dict) -> str:
    blocks = [
        "# Resume Experience Enrichment Prompts",
        "",
        "Use each prompt in your preferred chatbot. Keep every claim factual. Afterward, save all responses in one Markdown file and upload it in Settings > Profile.",
        "",
    ]
    for index, experience in enumerate(profile.get("experience", []), 1):
        company = experience.get("company", "")
        role = experience.get("role", "")
        date = experience.get("date", "")
        bullets = "\n".join(f"- {bullet}" for bullet in experience.get("bullets", []) if bullet)
        blocks.extend([
            f"## Prompt {index}: {company} — {role}",
            "",
            "```text",
            "You are building a factual master-resume bullet library. Expand the experience below into a comprehensive set of distinct resume bullets suitable for different job descriptions.",
            "",
            "Rules:",
            "- Use only facts explicitly present below or additional facts I provide in this chat.",
            "- Ask clarifying questions before adding scope, tools, metrics, stakeholders, or outcomes that are not supplied.",
            "- Cover responsibilities, analysis, operations, communication, leadership, process improvement, and measurable outcomes when supported.",
            "- Do not repeat or lightly paraphrase the same bullet.",
            "- Return only the Markdown structure shown below.",
            "",
            "Required output:",
            "# Experience",
            f"## {company} | {role} | {date}",
            "- [unique factual bullet]",
            "- [unique factual bullet]",
            "",
            "Existing facts:",
            bullets or "- No bullets yet; ask me detailed questions about this experience.",
            "```",
            "",
        ])
    return "\n".join(blocks)
