from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def skills_home() -> Path:
    override = os.environ.get("CODEX_COPILOT_SKILLS_HOME")
    if override:
        return Path(override).expanduser()
    existing = codex_home() / "skills" / "codex-copilot"
    if existing.exists() or existing.is_symlink():
        return existing.parent
    return Path.home() / ".agents" / "skills"


def skill_locations() -> list[Path]:
    candidates = [skills_home() / "codex-copilot", codex_home() / "skills" / "codex-copilot"]
    if codex_home().resolve() == (Path.home() / ".codex").resolve():
        candidates.append(Path.home() / ".agents" / "skills" / "codex-copilot")
    return list(dict.fromkeys(candidates))


def bin_dir() -> Path:
    return Path(os.environ.get("CODEX_COPILOT_BIN_DIR", Path.home() / ".local" / "bin")).expanduser()


def state_dir() -> Path:
    return Path(os.environ.get("CODEX_COPILOT_STATE_DIR", Path.home() / ".codex-copilot")).expanduser()


def share_dir() -> Path:
    return Path(os.environ.get("CODEX_COPILOT_SHARE_DIR", Path.home() / ".local" / "share" / "codex-copilot")).expanduser()

