"""
Configuration store for the V2 app.

Everything that used to be hardcoded (profile, scoring rules, résumé content,
app settings) lives in JSON files the user can edit through the Settings UI.

- `defaults/`  ships sensible starting values (version-controlled).
- `data/`      holds the user's live, editable copy (git-ignored). On first run,
               any missing file is copied from defaults.

This module is intentionally dependency-light so it can be imported anywhere.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DEFAULTS_DIR = BACKEND_DIR / "defaults"
_DATA_OVERRIDE = os.environ.get("JOB_AGENT_DATA_DIR", "").strip()
DATA_DIR = Path(_DATA_OVERRIDE).expanduser().resolve() if _DATA_OVERRIDE else (BACKEND_DIR / "data")

# The editable config documents (filename stem -> lives in data/ as <stem>.json).
CONFIG_NAMES = ("profile", "rules", "resume_content", "settings")


def ensure_config() -> None:
    """Create data/ and copy any missing config file from defaults/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "templates").mkdir(exist_ok=True)   # user-uploaded résumé templates
    (DATA_DIR / "output").mkdir(exist_ok=True)      # tracker, daily plan, etc.
    for name in CONFIG_NAMES:
        target = DATA_DIR / f"{name}.json"
        if not target.exists():
            src = DEFAULTS_DIR / f"{name}.json"
            if src.exists():
                shutil.copyfile(src, target)
            else:
                target.write_text("{}", encoding="utf-8")


def _path(name: str) -> Path:
    if name not in CONFIG_NAMES:
        raise KeyError(f"Unknown config '{name}'. Valid: {', '.join(CONFIG_NAMES)}")
    return DATA_DIR / f"{name}.json"


def load(name: str) -> dict:
    """Load a config document (falls back to its default, then {})."""
    p = _path(name)
    if not p.exists():
        ensure_config()
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        default = DEFAULTS_DIR / f"{name}.json"
        if default.exists():
            return json.loads(default.read_text(encoding="utf-8"))
        return {}


def save(name: str, data: dict) -> None:
    """Persist a config document (atomically: write temp, then replace)."""
    p = _path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def reset(name: str) -> dict:
    """Restore a config document from its shipped default."""
    default = DEFAULTS_DIR / f"{name}.json"
    data = json.loads(default.read_text(encoding="utf-8")) if default.exists() else {}
    save(name, data)
    return data
