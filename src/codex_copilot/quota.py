from __future__ import annotations

import json
import math
import os
import queue
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from .paths import state_dir
from . import VERSION
from .process import codex_command
from . import process_tree
from .routing import QuotaBand, band_for_windows


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


def _object(raw: Any, label: str) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid quota {label}: expected an object")
    return raw


def _window(raw: dict[str, Any] | None) -> Window | None:
    raw = _object(raw, "window")
    if not raw or raw.get("usedPercent") is None:
        return None
    used = float(raw["usedPercent"])
    if isinstance(raw["usedPercent"], bool) or not math.isfinite(used) or not 0 <= used <= 100:
        raise ValueError("Invalid quota usedPercent")
    return Window(
        used_percent=used,
        remaining_percent=max(0.0, min(100.0, 100.0 - used)),
        duration_mins=raw.get("windowDurationMins"),
        resets_at=raw.get("resetsAt"),
    )


def snapshot_from_result(result: dict[str, Any], source: str = "app-server") -> QuotaSnapshot:
    result = _object(result, "result")
    limits_by_id = _object(result.get("rateLimitsByLimitId"), "rateLimitsByLimitId")
    limits = _object(limits_by_id.get("codex") if limits_by_id.get("codex") is not None else result.get("rateLimits"), "rateLimits")
    primary = _window(limits.get("primary"))
    secondary = _window(limits.get("secondary"))
    remaining = [window.remaining_percent for window in (primary, secondary) if window]
    effective = min(remaining) if remaining else None
    reached_type = limits.get("rateLimitReachedType")
    spend_reached = bool(limits.get("spendControlReached"))
    band = band_for_windows(
        primary.remaining_percent if primary else None,
        secondary.remaining_percent if secondary else None,
        reached=bool(reached_type),
        spend_control_reached=spend_reached,
    )
    credits = _object(limits.get("credits"), "credits")
    reset_credits = _object(result.get("rateLimitResetCredits"), "rateLimitResetCredits")
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
        return json.loads(Path(fixture).read_text(encoding="utf-8"))["result"]

    if timeout <= 0:
        raise TimeoutError("Quota timeout must be positive")
    deadline = time.monotonic() + timeout
    proc, job = process_tree.start(
        codex_command(["app-server", "--listen", "stdio://"]),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="strict",
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
                    "version": VERSION,
                }
            },
        },
        {"method": "initialized", "params": {}},
        {"method": "account/rateLimits/read", "id": 1},
    ]
    inbox: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=64)
    stop = threading.Event()

    def deliver(kind: str, value: Any) -> None:
        while not stop.is_set():
            try:
                inbox.put((kind, value), timeout=0.1)
                return
            except queue.Full:
                pass

    def read_stdout() -> None:
        try:
            for line in proc.stdout:
                if stop.is_set():
                    return
                deliver("line", line)
            deliver("eof", None)
        except (OSError, ValueError) as exc:
            deliver("error", exc)

    reader = threading.Thread(target=read_stdout, name="codex-copilot-quota-reader", daemon=True)
    reader.start()
    try:
        for message in messages:
            proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        proc.stdin.flush()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"App Server did not return quota within {timeout:g}s")
            try:
                kind, line = inbox.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError(f"App Server did not return quota within {timeout:g}s") from None
            if kind == "eof":
                raise RuntimeError("App Server closed stdout before returning quota")
            if kind == "error":
                raise RuntimeError("App Server stdout could not be read") from line
            message = json.loads(line)
            if not isinstance(message, dict):
                raise RuntimeError("App Server returned a non-object response")
            if message.get("id") == 0 and "error" in message:
                raise RuntimeError(f"App Server initialization failed: {message['error']}")
            if message.get("id") == 1:
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                result = message.get("result")
                if not isinstance(result, dict):
                    raise RuntimeError("App Server returned an invalid quota result")
                return result
    finally:
        stop.set()
        try:
            process_tree.stop(proc, job)
        finally:
            reader.join(timeout=1)
            proc.stdin.close()
            proc.stdout.close()
        if reader.is_alive():
            raise RuntimeError("App Server stdout reader did not stop")


def cache_path() -> Path:
    return state_dir() / "quota-cache.json"


def cached_quota(*, ttl: int = 60) -> QuotaSnapshot | None:
    """Reuse a recent live quota result without starting another app server."""
    return _cached_snapshot(cache_path(), ttl, source="cache")


def _cached_snapshot(cache: Path, ttl: int, *, source: str) -> QuotaSnapshot | None:
    """Load a recent successful app-server result and label its cache use."""
    if not cache.exists():
        return None
    try:
        raw = json.loads(cache.read_text(encoding="utf-8"))
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


def get_quota(*, refresh: bool = False, timeout: float = 20.0, ttl: int = 60) -> QuotaSnapshot:
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
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
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
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
