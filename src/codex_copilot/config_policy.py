"""Shared installation and dispatch requirements; preferences do not authorize work."""
from __future__ import annotations

from typing import Any

from .config_edit import MISSING, get_path, parse_toml
from .paths import codex_home


REQUIRED_CONFIG: dict[str, Any] = {
    "features.multi_agent": True,
    "agents.max_concurrent_threads_per_session": 3,
    "agents.default_subagent_model": "gpt-6-luna",
    "agents.default_subagent_reasoning_effort": "low",
    "features.fast_mode": False,
}


def config_checks(config: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for key, expected in REQUIRED_CONFIG.items():
        actual = get_path(config, key, MISSING)
        matches = type(actual) is type(expected) and actual == expected
        checks.append({"key": key, "expected": expected,
                       "actual": actual if type(actual) in (str, bool, int) else None,
                       "missing": actual is MISSING, "matches": matches,
                       "impact": "cost_policy" if key == "features.fast_mode" else "dispatch_safety",
                       "blocking": not matches})
    tier = get_path(config, "service_tier", MISSING)
    # Unknown preference strings may contain private content. Never echo them.
    known_tiers = {"standard", "default", "auto", "fast", "priority", "flex", "ultrafast"}
    checks.append({"key": "service_tier", "expected": "user preference (not managed)",
                   "actual": tier if isinstance(tier, str) and tier in known_tiers else None,
                   "missing": tier is MISSING, "matches": True,
                   "impact": "preference", "blocking": False})
    return checks


def require_dispatch_config() -> None:
    try:
        config = parse_toml((codex_home() / "config.toml").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError("Dispatch blocked: Codex configuration is missing, unreadable or invalid") from None
    blocked = [item["key"] for item in config_checks(config) if item["blocking"]]
    if blocked:
        raise ValueError("Dispatch blocked: required settings differ: " + ", ".join(blocked))
