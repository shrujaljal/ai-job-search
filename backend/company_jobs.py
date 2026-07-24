"""Target-company career-site adapters and tracker correlation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
import ipaddress
import json
import re
import socket
from urllib.parse import urljoin, urlparse, urlunparse

import httpx

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
_JOB_HINT = re.compile(r"\b(job|jobs|career|careers|position|opening|vacanc)", re.I)
_GENERIC_LINK_LABELS = {
    "job", "jobs", "career", "careers", "open positions", "view jobs",
    "search jobs", "job search", "all jobs", "current openings",
}


class CareerSiteError(RuntimeError):
    pass


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.parts.append(value)


class _LinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.current_href = ""
        self.current_text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self.current_href = dict(attrs).get("href") or ""
            self.current_text = []

    def handle_data(self, data: str) -> None:
        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self.current_href:
            return
        text = re.sub(r"\s+", " ", " ".join(self.current_text)).strip()
        href = urljoin(self.base_url, self.current_href)
        if text and (_JOB_HINT.search(href) or _JOB_HINT.search(text)):
            self.links.append((text, href))
        self.current_href = ""
        self.current_text = []


def html_text(value: str) -> str:
    parser = _TextParser()
    parser.feed(unescape(value or ""))
    return "\n".join(parser.parts)


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CareerSiteError("Use a complete http:// or https:// career-site URL.")
    if parsed.username or parsed.password:
        raise CareerSiteError("Career-site URLs cannot contain credentials.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    except socket.gaierror as exc:
        raise CareerSiteError(f"Could not resolve {parsed.hostname}.") from exc
    for item in addresses:
        address = ipaddress.ip_address(item[4][0])
        if not address.is_global:
            raise CareerSiteError("Private or local network addresses are not allowed.")


def _request(url: str) -> tuple[bytes, str]:
    current = url
    with httpx.Client(timeout=20, follow_redirects=False, headers={
        "User-Agent": "JobApplicationAgent/2.0 (+local career search)",
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    }) as client:
        for _ in range(4):
            _validate_public_url(current)
            with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise CareerSiteError("Career site returned an invalid redirect.")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise CareerSiteError("Career-site response exceeded 5 MB.")
                return bytes(body), current
    raise CareerSiteError("Career site redirected too many times.")


def _get_json(url: str) -> dict | list:
    body, _ = _request(url)
    try:
        return json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise CareerSiteError("Career site did not return valid job data.") from exc


def _iso_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return value


def _greenhouse_token(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.hostname not in {
        "boards.greenhouse.io", "job-boards.greenhouse.io", "boards-api.greenhouse.io",
    }:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.hostname == "boards-api.greenhouse.io":
        try:
            return parts[parts.index("boards") + 1]
        except (ValueError, IndexError):
            return None
    return parts[0] if parts else None


def _lever_site(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url)
    hosts = {
        "jobs.lever.co": "https://api.lever.co",
        "api.lever.co": "https://api.lever.co",
        "jobs.eu.lever.co": "https://api.eu.lever.co",
        "api.eu.lever.co": "https://api.eu.lever.co",
    }
    api_root = hosts.get(parsed.hostname or "")
    if not api_root:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.hostname and parsed.hostname.startswith("api."):
        try:
            site = parts[parts.index("postings") + 1]
        except (ValueError, IndexError):
            return None
    else:
        site = parts[0] if parts else ""
    return (site, api_root) if site else None


def _ashby_board(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.hostname not in {"jobs.ashbyhq.com", "api.ashbyhq.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.hostname == "api.ashbyhq.com":
        try:
            return parts[parts.index("job-board") + 1]
        except (ValueError, IndexError):
            return None
    return parts[0] if parts else None


def _greenhouse_jobs(token: str, company: str) -> list[dict]:
    payload = _get_json(
        f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    )
    return [{
        "id": str(job.get("id", "")),
        "title": job.get("title", ""),
        "company": company,
        "location": job.get("location", {}).get("name", ""),
        "url": job.get("absolute_url", ""),
        "posted_at": _iso_date(job.get("updated_at")),
        "jd_text": html_text(job.get("content", "")),
        "source": "Greenhouse",
    } for job in payload.get("jobs", [])]


def _lever_jobs(site: str, api_root: str, company: str) -> list[dict]:
    payload = _get_json(f"{api_root}/v0/postings/{site}?mode=json")
    return [{
        "id": str(job.get("id", "")),
        "title": job.get("text", ""),
        "company": company,
        "location": job.get("categories", {}).get("location", ""),
        "url": job.get("hostedUrl", ""),
        "posted_at": "",
        "jd_text": job.get("descriptionPlain") or html_text(job.get("description", "")),
        "source": "Lever",
    } for job in payload if isinstance(job, dict)]


def _ashby_jobs(board: str, company: str) -> list[dict]:
    payload = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{board}")
    return [{
        "id": str(job.get("id") or job.get("jobUrl") or ""),
        "title": job.get("title", ""),
        "company": company,
        "location": job.get("location", ""),
        "url": job.get("jobUrl") or job.get("applyUrl", ""),
        "posted_at": _iso_date(job.get("publishedAt")),
        "jd_text": job.get("descriptionPlain") or html_text(job.get("descriptionHtml", "")),
        "source": "Ashby",
    } for job in payload.get("jobs", []) if isinstance(job, dict)]


def _generic_jobs(url: str, company: str) -> list[dict]:
    body, final_url = _request(url)
    parser = _LinkParser(final_url)
    parser.feed(body.decode("utf-8", errors="replace"))
    seen: set[str] = set()
    jobs = []
    for title, href in parser.links:
        normalized = normalize_url(href)
        if (normalized in seen or len(title) < 3 or len(title) > 180
                or _norm(title) in _GENERIC_LINK_LABELS):
            continue
        seen.add(normalized)
        jobs.append({
            "id": normalized,
            "title": title,
            "company": company,
            "location": "",
            "url": href,
            "posted_at": "",
            "jd_text": "",
            "source": "Career site",
        })
    return jobs


def fetch_source(source: dict) -> list[dict]:
    url = str(source.get("url", "")).strip()
    company = str(source.get("name", "")).strip() or (urlparse(url).hostname or "Company")
    if token := _greenhouse_token(url):
        return _greenhouse_jobs(token, company)
    if lever := _lever_site(url):
        return _lever_jobs(lever[0], lever[1], company)
    if board := _ashby_board(url):
        return _ashby_jobs(board, company)
    return _generic_jobs(url, company)


def filter_recent(jobs: list[dict], recent_days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=recent_days)
    output = []
    for job in jobs:
        value = job.get("posted_at", "")
        if not value:
            job["recent"] = None
            output.append(job)
            continue
        try:
            posted = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if posted.tzinfo is None:
                posted = posted.replace(tzinfo=timezone.utc)
            job["recent"] = posted >= cutoff
            if job["recent"]:
                output.append(job)
        except ValueError:
            job["recent"] = None
            output.append(job)
    return output


def normalize_url(url: str) -> str:
    parsed = urlparse(url or "")
    host = (parsed.hostname or "").lower()
    path = re.sub(r"/+$", "", parsed.path)
    return urlunparse((parsed.scheme.lower(), host, path, "", "", ""))


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def annotate_tracker(jobs: list[dict], applications: list[dict]) -> None:
    by_url = {normalize_url(row.get("url", "")): row for row in applications if row.get("url")}
    by_role = {
        (_norm(row.get("company", "")), _norm(row.get("role", ""))): row
        for row in applications
    }
    for job in jobs:
        row = by_url.get(normalize_url(job.get("url", "")))
        if row is None:
            row = by_role.get((_norm(job.get("company", "")), _norm(job.get("title", ""))))
        job["tracked"] = row is not None
        job["application_id"] = row.get("id") if row else None
        job["application_status"] = row.get("status", "") if row else ""
        job["already_applied"] = bool(row and row.get("status") != "To Apply")
