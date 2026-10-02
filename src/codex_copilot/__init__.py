"""Codex-Copilot runtime."""

from pathlib import Path

VERSION = (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip()
