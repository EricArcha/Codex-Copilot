from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from .paths import state_dir
from .routing import QuotaBand, band_for_remaining


@dataclass(frozen=True)
class Window:
    used_percent: float
    remaining_percent: float
    duration_mins: int | None
    resets_at: int | None


@dataclass(frozen=True)
class QuotaSnapshot:
    fetched_at: int
    band: str
    effective_remaining_percent: float | None
    primary: Window | None
    secondary: Window | None
    plan_type: str | None
    credits_balance: str | None
    reset_credits_available: int
    reached_type: str | None
    spend_control_reached: bool
    source: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _window(raw: dict[str, Any] | None) -> Window | None:
    if not raw or raw.get("usedPercent") is None:
        return None
    used = float(raw["usedPercent"])
    return Window(
        used_percent=used,
        remaining_percent=max(0.0, min(100.0, 100.0 - used)),
        duration_mins=raw.get("windowDurationMins"),
        resets_at=raw.get("resetsAt"),
    )


def snapshot_from_result(result: dict[str, Any], source: str = "app-server") -> QuotaSnapshot:
    limits_by_id = result.get("rateLimitsByLimitId") or {}
    limits = limits_by_id.get("codex") or result.get("rateLimits") or {}
    primary = _window(limits.get("primary"))
    secondary = _window(limits.get("secondary"))
    remaining = [window.remaining_percent for window in (primary, secondary) if window]
    effective = min(remaining) if remaining else None
    reached_type = limits.get("rateLimitReachedType")
    spend_reached = bool(limits.get("spendControlReached"))
    band = band_for_remaining(
        effective,
        reached=bool(reached_type),
        spend_control_reached=spend_reached,
    )
    credits = limits.get("credits") or {}
    reset_credits = result.get("rateLimitResetCredits") or {}
    return QuotaSnapshot(
        fetched_at=int(time.time()),
        band=band.value,
        effective_remaining_percent=effective,
        primary=primary,
        secondary=secondary,
        plan_type=limits.get("planType"),
        credits_balance=credits.get("balance"),
        reset_credits_available=int(reset_credits.get("availableCount") or 0),
        reached_type=reached_type,
        spend_control_reached=spend_reached,
        source=source,
    )


def unknown_snapshot(error: str) -> QuotaSnapshot:
    return QuotaSnapshot(
        fetched_at=int(time.time()),
        band=QuotaBand.UNKNOWN.value,
        effective_remaining_percent=None,
        primary=None,
        secondary=None,
        plan_type=None,
        credits_balance=None,
        reset_credits_available=0,
        reached_type=None,
        spend_control_reached=False,
        source="unavailable",
        error=error,
    )


def _read_rpc_result(timeout: float) -> dict[str, Any]:
    fixture = os.environ.get("CODEX_COPILOT_QUOTA_FIXTURE")
    if fixture:
        return json.loads(Path(fixture).read_text())["result"]

    proc = subprocess.Popen(
        ["codex", "app-server", "--listen", "stdio://"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    messages = [
        {
            "method": "initialize",
            "id": 0,
            "params": {
                "clientInfo": {
                    "name": "codex_copilot",
                    "title": "Codex Copilot",
                    "version": "0.1.0",
                }
            },
        },
        {"method": "initialized", "params": {}},
        {"method": "account/rateLimits/read", "id": 1},
    ]
    try:
        for message in messages:
            proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        proc.stdin.flush()
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            events = selector.select(max(0.0, deadline - time.monotonic()))
            if not events:
                break
            line = proc.stdout.readline()
            if not line:
                break
            message = json.loads(line)
            if message.get("id") == 1:
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                return message["result"]
        raise TimeoutError(f"App Server did not return quota within {timeout:g}s")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=1)


def cache_path() -> Path:
    return state_dir() / "quota-cache.json"


def _cached_snapshot(cache: Path, ttl: int, *, source: str) -> QuotaSnapshot | None:
    """Load a recent successful app-server result and label its cache use."""
    if not cache.exists():
        return None
    try:
        raw = json.loads(cache.read_text())
        age = time.time() - raw["fetched_at"]
        if not 0 <= age <= ttl:
            return None
        snapshot = _snapshot_from_dict(raw)
        # The cache is written only after a successful live read. Keeping this
        # provenance check prevents an unavailable or prior fallback result from
        # becoming a future source of authority.
        if snapshot.source != "app-server":
            return None
        return replace(snapshot, source=source)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def get_quota(*, refresh: bool = False, timeout: float = 10.0, ttl: int = 60) -> QuotaSnapshot:
    cache = cache_path()
    if not refresh:
        cached = _cached_snapshot(cache, ttl, source="cache")
        if cached:
            return cached
    try:
        snapshot = snapshot_from_result(_read_rpc_result(timeout))
        cache.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json(cache, snapshot.to_dict())
        return snapshot
    except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        # A live read remains authoritative. A transient failure may reuse only
        # the tool's own very recent successful result, never caller-provided
        # quota input. The source and error make the degraded mode explicit.
        cached = _cached_snapshot(cache, ttl, source="cache-fallback")
        if cached:
            return replace(cached, error=f"Fresh quota read failed: {exc}")
        return unknown_snapshot(str(exc))


def _snapshot_from_dict(raw: dict[str, Any]) -> QuotaSnapshot:
    def convert(value: dict[str, Any] | None) -> Window | None:
        return Window(**value) if value else None

    return QuotaSnapshot(
        **{
            **raw,
            "primary": convert(raw.get("primary")),
            "secondary": convert(raw.get("secondary")),
        }
    )


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)
