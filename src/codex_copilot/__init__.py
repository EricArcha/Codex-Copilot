"""Codex-Copilot runtime."""

from pathlib import Path

VERSION = (Path(__file__).resolve().parents[2] / "VERSION").read_text().strip() if (Path(__file__).resolve().parents[2] / "VERSION").exists() else "0.1.0"

