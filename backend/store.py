"""
User data store: application tracker + daily plan (JSON in data/output/).

Atomic writes; simple auto-increment ids for tracker rows so the API can
update/delete individual applications.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
OUTPUT = DATA / "output"
TRACKER = OUTPUT / "tracker.json"
PLAN = OUTPUT / "daily_plan.json"

STATUSES = ["To Apply", "Applied", "Phone Screen", "Interview",
            "Final Round", "Offer", "Rejected"]


def _read(path: Path, fallback):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return fallback
    return fallback


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# ── Tracker ───────────────────────────────────────────────────────────────────
def list_applications() -> list[dict]:
    return _read(TRACKER, [])


def _next_id(rows: list[dict]) -> int:
    return (max((r.get("id", 0) for r in rows), default=0)) + 1


def has_application(company: str, role: str, rows: list[dict] | None = None) -> bool:
    rows = rows if rows is not None else list_applications()
    c, r = company.lower().strip(), role.lower().strip()
    return any(x.get("company", "").lower().strip() == c
               and x.get("role", "").lower().strip() == r for x in rows)


def add_application(company: str, role: str, location: str = "", url: str = "",
                    status: str = "To Apply", notes: str = "") -> dict | None:
    rows = list_applications()
    if has_application(company, role, rows):
        return None
    row = {"id": _next_id(rows), "company": company, "role": role,
           "location": location, "url": url, "date_added": str(date.today()),
           "status": status, "notes": notes}
    rows.append(row)
    _write(TRACKER, rows)
    return row


def update_application(app_id: int, fields: dict) -> bool:
    rows = list_applications()
    for r in rows:
        if r.get("id") == app_id:
            for k in ("status", "notes", "location", "url"):
                if k in fields:
                    r[k] = fields[k]
            _write(TRACKER, rows)
            return True
    return False


def delete_application(app_id: int) -> bool:
    rows = list_applications()
    new = [r for r in rows if r.get("id") != app_id]
    if len(new) == len(rows):
        return False
    _write(TRACKER, new)
    return True


# ── Daily plan ────────────────────────────────────────────────────────────────
def get_plan() -> dict:
    return _read(PLAN, {})


def save_plan(data: dict) -> None:
    _write(PLAN, data)


# ── Dashboard aggregates ──────────────────────────────────────────────────────
def dashboard() -> dict:
    rows = list_applications()
    by_status = {s: 0 for s in STATUSES}
    for r in rows:
        by_status[r.get("status", "To Apply")] = by_status.get(r.get("status", "To Apply"), 0) + 1
    return {
        "total": len(rows),
        "applied": sum(1 for r in rows if r.get("status") != "To Apply"),
        "interviewing": sum(1 for r in rows if r.get("status") in
                            ("Phone Screen", "Interview", "Final Round")),
        "offers": by_status.get("Offer", 0),
        "by_status": by_status,
        "applications": rows,
        "statuses": STATUSES,
    }
