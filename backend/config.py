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
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parent
DEFAULTS_DIR = BACKEND_DIR / "defaults"
_DATA_OVERRIDE = os.environ.get("JOB_AGENT_DATA_DIR", "").strip()
DATA_ROOT = Path(_DATA_OVERRIDE).expanduser().resolve() if _DATA_OVERRIDE else (BACKEND_DIR / "data")
DATA_DIR = DATA_ROOT

# The editable config documents (filename stem -> lives in data/ as <stem>.json).
CONFIG_NAMES = ("profile", "rules", "resume_content", "settings", "target_companies")
_ACCOUNT_ID = re.compile(r"[^a-z0-9]+")


def ensure_config() -> None:
    """Create data/ and copy any missing config file from defaults/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "profile_sources").mkdir(exist_ok=True)
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


def _accounts_path() -> Path:
    return DATA_ROOT / "accounts.json"


def _account_name_from_data() -> str:
    try:
        settings = json.loads((DATA_ROOT / "settings.json").read_text(encoding="utf-8"))
        profile = json.loads((DATA_ROOT / "profile.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return "Default profile"
    values = (
        settings.get("candidate_name"),
        profile.get("identity", {}).get("name"),
    )
    return next((value for value in values if value and value != "Your Name"),
                "Default profile")


def _default_accounts() -> dict:
    return {
        "active_id": "default",
        "accounts": [{
            "id": "default",
            "name": _account_name_from_data(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }],
    }


def _write_accounts(data: dict) -> None:
    path = _accounts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def accounts() -> dict:
    path = _accounts_path()
    if not path.exists():
        data = _default_accounts()
        _write_accounts(data)
        return data
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = _default_accounts()
        _write_accounts(data)
    return data


def _account_dir(account_id: str) -> Path:
    return DATA_ROOT if account_id == "default" else DATA_ROOT / "accounts" / account_id


def initialize_accounts() -> dict:
    """Select the persisted account while preserving legacy data as `default`."""
    global DATA_DIR
    DATA_DIR = DATA_ROOT
    ensure_config()
    data = accounts()
    valid_ids = {item.get("id") for item in data.get("accounts", [])}
    active_id = data.get("active_id", "default")
    if active_id not in valid_ids:
        active_id = "default"
        data["active_id"] = active_id
        _write_accounts(data)
    DATA_DIR = _account_dir(active_id)
    ensure_config()
    return data


def active_account_id() -> str:
    return accounts().get("active_id", "default")


def activate_account(account_id: str) -> dict:
    global DATA_DIR
    data = accounts()
    account = next((item for item in data.get("accounts", [])
                    if item.get("id") == account_id), None)
    if account is None:
        raise KeyError(f"Unknown account '{account_id}'")
    data["active_id"] = account_id
    _write_accounts(data)
    DATA_DIR = _account_dir(account_id)
    ensure_config()
    return account


def create_account(name: str) -> dict:
    cleaned_name = re.sub(r"\s+", " ", name).strip()
    if not cleaned_name:
        raise ValueError("Account name is required.")
    data = accounts()
    previous_active_id = data.get("active_id", "default")
    stem = _ACCOUNT_ID.sub("-", cleaned_name.lower()).strip("-")[:36] or "profile"
    account_id = f"{stem}-{uuid4().hex[:6]}"
    account = {
        "id": account_id,
        "name": cleaned_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "setup_pending": True,
        "setup_complete": False,
        "return_to_id": previous_active_id,
    }
    data.setdefault("accounts", []).append(account)
    data["active_id"] = account_id
    _write_accounts(data)
    activate_account(account_id)
    return account


def can_cancel_account_setup() -> bool:
    data = accounts()
    active_id = data.get("active_id", "default")
    if active_id == "default":
        return False
    account = next((item for item in data.get("accounts", [])
                    if item.get("id") == active_id), None)
    if account is None:
        return False
    if account.get("setup_complete"):
        return False
    settings = load("settings")
    return bool(account.get("setup_pending") or not settings.get("onboarding_complete"))


def finish_account_setup() -> None:
    data = accounts()
    active_id = data.get("active_id", "default")
    account = next((item for item in data.get("accounts", [])
                    if item.get("id") == active_id), None)
    if account is None:
        return
    account["setup_complete"] = True
    account.pop("setup_pending", None)
    account.pop("return_to_id", None)
    _write_accounts(data)


def cancel_account_setup() -> dict:
    """Remove an unfinished secondary profile and restore its previous profile."""
    global DATA_DIR
    data = accounts()
    active_id = data.get("active_id", "default")
    account = next((item for item in data.get("accounts", [])
                    if item.get("id") == active_id), None)
    if active_id == "default" or account is None or not can_cancel_account_setup():
        raise ValueError("This profile setup cannot be cancelled.")

    valid_ids = {item.get("id") for item in data.get("accounts", [])}
    return_to_id = account.get("return_to_id")
    if return_to_id not in valid_ids or return_to_id == active_id:
        return_to_id = "default"
    target = _account_dir(active_id).resolve()
    account_root = (DATA_ROOT / "accounts").resolve()
    if account_root not in target.parents:
        raise RuntimeError("Refusing to remove a profile outside the accounts directory.")

    data["accounts"] = [
        item for item in data.get("accounts", []) if item.get("id") != active_id
    ]
    data["active_id"] = return_to_id
    _write_accounts(data)
    DATA_DIR = _account_dir(return_to_id)
    ensure_config()
    if target.exists():
        shutil.rmtree(target)
    return next(item for item in data["accounts"] if item.get("id") == return_to_id)


def rename_account(account_id: str, name: str) -> dict:
    cleaned_name = re.sub(r"\s+", " ", name).strip()
    if not cleaned_name:
        raise ValueError("Account name is required.")
    data = accounts()
    account = next((item for item in data.get("accounts", [])
                    if item.get("id") == account_id), None)
    if account is None:
        raise KeyError(f"Unknown account '{account_id}'")
    account["name"] = cleaned_name
    _write_accounts(data)
    return account
