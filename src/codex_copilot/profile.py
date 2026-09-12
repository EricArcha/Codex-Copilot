from __future__ import annotations

import json
from pathlib import Path

from .paths import state_dir
from .routing import Profile


def profile_path() -> Path:
    return state_dir() / "profile.json"


def active_profile() -> Profile:
    try:
        return Profile(json.loads(profile_path().read_text())["profile"])
    except (OSError, ValueError, KeyError, TypeError):
        return Profile.BALANCED


def set_profile(profile: Profile) -> None:
    path = profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"profile": profile.value}, indent=2) + "\n")
    temporary.replace(path)
