from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def skills_home() -> Path:
    return Path(os.environ.get("CODEX_COPILOT_SKILLS_HOME", Path.home() / ".agents" / "skills")).expanduser()


def bin_dir() -> Path:
    return Path(os.environ.get("CODEX_COPILOT_BIN_DIR", Path.home() / ".local" / "bin")).expanduser()


def state_dir() -> Path:
    return Path(os.environ.get("CODEX_COPILOT_STATE_DIR", Path.home() / ".codex-copilot")).expanduser()


def share_dir() -> Path:
    return Path(os.environ.get("CODEX_COPILOT_SHARE_DIR", Path.home() / ".local" / "share" / "codex-copilot")).expanduser()

