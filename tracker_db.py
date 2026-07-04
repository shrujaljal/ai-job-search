"""
SQLite-backed application tracker.

A single local database file (output/tracker.db) with atomic writes — durable
across refreshes and restarts, and safe from the partial-write corruption a
plain JSON file can suffer. On first run it imports any existing tracker.json.
"""

import json
import sqlite3
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = ROOT / "output" / "tracker.db"
JSON_PATH = ROOT / "output" / "tracker.json"

_COLUMNS = ["company", "role", "location", "url", "date_added", "status", "notes"]


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the table if needed and one-time migrate from tracker.json."""
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company    TEXT NOT NULL,
                role       TEXT NOT NULL,
                location   TEXT DEFAULT '',
                url        TEXT DEFAULT '',
                date_added TEXT DEFAULT '',
                status     TEXT DEFAULT 'To Apply',
                notes      TEXT DEFAULT ''
            )
        """)
    _migrate_from_json()


def _migrate_from_json() -> None:
    """Import tracker.json once (only if the DB is empty), then back it up."""
    if not JSON_PATH.exists():
        return
    with _conn() as c:
        if c.execute("SELECT COUNT(*) FROM applications").fetchone()[0] > 0:
            return
        try:
            rows = json.loads(JSON_PATH.read_text() or "[]")
        except (json.JSONDecodeError, OSError):
            return
        for r in rows:
            if not r.get("company") and not r.get("role"):
                continue
            c.execute(
                f"INSERT INTO applications ({','.join(_COLUMNS)}) "
                f"VALUES ({','.join('?' * len(_COLUMNS))})",
                tuple(r.get(col, "") for col in _COLUMNS))
    try:
        JSON_PATH.rename(JSON_PATH.with_suffix(".json.migrated"))
    except OSError:
        pass


def list_applications() -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM applications ORDER BY date_added DESC, id DESC")]


def has_application(company: str, role: str) -> bool:
    with _conn() as c:
        return c.execute(
            "SELECT 1 FROM applications WHERE lower(trim(company))=? "
            "AND lower(trim(role))=? LIMIT 1",
            (company.lower().strip(), role.lower().strip())).fetchone() is not None


def add_application(company: str, role: str, location: str = "", url: str = "",
                    status: str = "To Apply", notes: str = "") -> bool:
    """Insert a new application (status defaults to 'To Apply'). False if a dup."""
    if has_application(company, role):
        return False
    with _conn() as c:
        c.execute(
            f"INSERT INTO applications ({','.join(_COLUMNS)}) "
            f"VALUES ({','.join('?' * len(_COLUMNS))})",
            (company, role, location, url, str(date.today()), status, notes))
    return True


def update_application(app_id: int, status: str | None = None,
                       notes: str | None = None) -> None:
    with _conn() as c:
        if status is not None:
            c.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
        if notes is not None:
            c.execute("UPDATE applications SET notes=? WHERE id=?", (notes, app_id))


def delete_application(app_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM applications WHERE id=?", (app_id,))
