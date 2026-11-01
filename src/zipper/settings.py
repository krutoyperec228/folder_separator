"""Persistent user settings (JSON)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

__all__ = ["SETTINGS_PATH", "load_settings", "save_settings"]


def _config_dir() -> Path:
    if sys.platform == "win32":
        base = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "ZipperGUI"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ZipperGUI"
    base = os.getenv("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "ZipperGUI"


SETTINGS_PATH: Path = _config_dir() / "settings.json"

_DEFAULTS: dict[str, Any] = {
    "src": "",
    "out": "",
    "size_mb": "15",
    "extensions": "",
    "prefix": "archive",
    "compression": "deflate",
    "recursive": True,
}


def load_settings() -> dict[str, Any]:
    merged = dict(_DEFAULTS)
    try:
        if SETTINGS_PATH.exists():
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged.update({k: v for k, v in data.items() if k in _DEFAULTS})
    except (OSError, ValueError):
        pass
    return merged


def save_settings(data: dict[str, Any]) -> None:
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = SETTINGS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(SETTINGS_PATH)
    except OSError:
        pass