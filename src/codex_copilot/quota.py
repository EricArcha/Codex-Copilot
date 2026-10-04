from __future__ import annotations

import json
import math
import os
import queue
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, fields, replace
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
    error_category: str | None = None
    retryable: bool | None = None
    quota_status: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["quota_status"] = self.quota_status or _status(self, cache_status="not_checked")
        return result


def _status(snapshot: QuotaSnapshot, *, cache_status: str, phase: str | None = None,
            exit_code: int | None = None) -> dict[str, Any]:
    return {"read_success": snapshot.source == "app-server",
            "available": snapshot.source != "unavailable" and snapshot.band != "unknown",
            "source": snapshot.source, "cache_status": cache_status,
            "error_category": snapshot.error_category, "retryable": snapshot.retryable,
            "phase": phase, "process_exit_code": exit_code,
            "next_step": snapshot.error}


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


_DIAGNOSTICS = {
    "permission_denied": ("Quota query was denied permission; use host-approved execution for this command.", True),
    "state_initialization_failed": ("App Server could not initialize local state; check host permissions and state availability.", True),
    "process_exit": ("App Server ended before returning quota; inspect the resolved executable, failure phase and natural exit code before changing the installation.", True),
    "authentication_failed": ("Quota query requires a valid ChatGPT login.", False),
    "initialization_failed": ("App Server initialization failed.", False),
    "timeout": ("App Server quota query timed out.", True),
    "protocol_error": ("App Server returned an invalid quota response.", False),
    "state_write_failed": ("Quota was read, but its local cache could not be written; use host-approved execution for local state access.", True),
}


class QuotaReadError(RuntimeError):
    """A fixed diagnostic; raw child output must never leave the reader."""

    def __init__(self, category: str, *, phase: str | None = None, exit_code: int | None = None):
        self.category = category
        self.phase = phase
        self.exit_code = exit_code
        super().__init__(_DIAGNOSTICS[category][0])


def _failure_category(exc: Exception) -> str:
    if isinstance(exc, QuotaReadError):
        return exc.category
    if isinstance(exc, PermissionError):
        return "permission_denied"
    if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)):
        return "timeout"
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return "protocol_error"
    return "process_exit"


def _stderr_category(raw: bytes, default: str = "process_exit") -> str:
    # Inspect only the bounded in-memory tail. Never return or persist its text.
    text = raw.decode("utf-8", errors="replace").lower()
    if "failed to initialize sqlite state runtime" in text or "failed to initialize state runtime" in text:
        return "state_initialization_failed"
    if "permission denied" in text or "operation not permitted" in text or "access is denied" in text:
        return "permission_denied"
    if "not logged in" in text or "authentication required" in text or "unauthorized" in text:
        return "authentication_failed"
    return default


def unknown_snapshot(error: str, *, category: str | None = None) -> QuotaSnapshot:
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
        error_category=category,
        retryable=_DIAGNOSTICS[category][1] if category else None,
    )


def _read_rpc_result(timeout: float) -> dict[str, Any]:
    fixture = os.environ.get("CODEX_COPILOT_QUOTA_FIXTURE")
    if fixture:
        return json.loads(Path(fixture).read_text(encoding="utf-8"))["result"]

    if timeout <= 0:
        raise TimeoutError("Quota timeout must be positive")
    deadline = time.monotonic() + timeout
    try:
        proc, job = process_tree.start(
            codex_command(["app-server", "--listen", "stdio://"]),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="strict", bufsize=1,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise QuotaReadError(_failure_category(exc), phase="startup") from None
    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None
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
    phase = "initialize"

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

    stderr_tail = bytearray()
    stderr_lock = threading.Lock()

    def read_stderr() -> None:
        try:
            while True:
                chunk = proc.stderr.buffer.read1(4096)
                if not chunk:
                    return
                with stderr_lock:
                    stderr_tail.extend(chunk)
                    del stderr_tail[:-8192]
        except (OSError, ValueError):
            return

    def child_failure(default: str = "process_exit") -> QuotaReadError:
        # Observe the child's own exit before cleanup. Never report our kill code.
        remaining = max(0.0, deadline - time.monotonic())
        try:
            code = proc.wait(timeout=min(0.2, remaining))
        except subprocess.TimeoutExpired:
            code = None
        stderr_reader.join(timeout=min(0.2, max(0.0, deadline - time.monotonic())))
        with stderr_lock:
            return QuotaReadError(_stderr_category(bytes(stderr_tail), default), phase=phase, exit_code=code)

    stderr_reader = threading.Thread(target=read_stderr, name="codex-copilot-quota-stderr", daemon=True)
    stderr_reader.start()

    reader = threading.Thread(target=read_stdout, name="codex-copilot-quota-reader", daemon=True)
    reader.start()
    def send(message: dict[str, Any]) -> None:
        proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        proc.stdin.flush()

    try:
        send(messages[0])
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"App Server did not return quota within {timeout:g}s")
            try:
                kind, line = inbox.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError(f"App Server did not return quota within {timeout:g}s") from None
            if kind == "eof":
                raise child_failure()
            if kind == "error":
                raise QuotaReadError("protocol_error") from None
            try:
                message = json.loads(line)
            except ValueError:
                raise QuotaReadError("protocol_error") from None
            if not isinstance(message, dict):
                raise QuotaReadError("protocol_error")
            if message.get("id") == 0:
                if phase != "initialize":
                    raise QuotaReadError("protocol_error")
                if "error" in message:
                    category = _stderr_category(json.dumps(message["error"]).encode(), "initialization_failed")
                    raise QuotaReadError(category)
                if not isinstance(message.get("result"), dict):
                    raise QuotaReadError("protocol_error")
                send(messages[1])
                phase = "quota_read"
                send(messages[2])
                continue
            if message.get("id") == 1:
                if phase != "quota_read":
                    raise QuotaReadError("protocol_error")
                if "error" in message:
                    raise QuotaReadError(_stderr_category(json.dumps(message["error"]).encode(), "protocol_error"))
                result = message.get("result")
                if not isinstance(result, dict):
                    raise QuotaReadError("protocol_error")
                return result
    except BrokenPipeError:
        raise child_failure() from None
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        if getattr(exc, "phase", None) is None:
            exc.phase = phase
        if getattr(exc, "exit_code", None) is None:
            exc.exit_code = proc.poll()
        raise
    finally:
        stop.set()
        try:
            process_tree.stop(proc, job)
        finally:
            reader.join(timeout=1)
            stderr_reader.join(timeout=1)
            try:
                try:
                    proc.stdin.close()
                except BrokenPipeError:
                    # The stopped child may have closed its input before the
                    # buffered writer flushes. Preserve the RPC result/error.
                    pass
            finally:
                try:
                    proc.stdout.close()
                finally:
                    proc.stderr.close()
        if reader.is_alive() or stderr_reader.is_alive():
            raise QuotaReadError("process_exit")


def cache_path() -> Path:
    return state_dir() / "quota-cache.json"


def cached_quota(*, ttl: int = 60) -> QuotaSnapshot | None:
    """Reuse a recent live quota result without starting another app server."""
    return _cached_snapshot(cache_path(), ttl, source="cache")


def _cached_snapshot(cache: Path, ttl: int, *, source: str) -> QuotaSnapshot | None:
    return _inspect_cache(cache, ttl, source=source)[0]


def _inspect_cache(cache: Path, ttl: int, *, source: str) -> tuple[QuotaSnapshot | None, str]:
    """Load a recent successful app-server result and label its cache use."""
    try:
        raw = json.loads(cache.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or type(raw.get("fetched_at")) not in (int, float):
            return None, "invalid"
        age = time.time() - raw["fetched_at"]
        if not 0 <= age <= ttl:
            return None, "expired" if age > ttl else "invalid"
        snapshot = _snapshot_from_dict(raw)
        # The cache is written only after a successful live read. Keeping this
        # provenance check prevents an unavailable or prior fallback result from
        # becoming a future source of authority.
        if snapshot.source != "app-server" or snapshot.error_category or snapshot.error:
            return None, "invalid"
        snapshot = replace(snapshot, source=source, quota_status=None)
        return replace(snapshot, quota_status=_status(snapshot, cache_status="valid")), "valid"
    except FileNotFoundError:
        return None, "missing"
    except OSError:
        return None, "unreadable"
    except (ValueError, KeyError, TypeError, AttributeError):
        return None, "invalid"


def get_quota(*, refresh: bool = False, timeout: float = 20.0, ttl: int = 60) -> QuotaSnapshot:
    cache = cache_path()
    if not refresh:
        cached, _ = _inspect_cache(cache, ttl, source="cache")
        if cached:
            return cached
    try:
        snapshot = snapshot_from_result(_read_rpc_result(timeout))
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            payload = asdict(snapshot)
            payload.pop("quota_status", None)  # Diagnostics are output, not cache authority.
            _atomic_json(cache, payload)
        except OSError:
            # A successful live observation remains authoritative even if caching fails.
            snapshot = replace(snapshot, error=_DIAGNOSTICS["state_write_failed"][0],
                               error_category="state_write_failed", retryable=True)
            return replace(snapshot, quota_status=_status(snapshot, cache_status="write_failed", phase="cache_write"))
        return replace(snapshot, quota_status=_status(snapshot, cache_status="valid"))
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        # A live read remains authoritative. A transient failure may reuse only
        # the tool's own very recent successful result, never caller-provided
        # quota input. The source and error make the degraded mode explicit.
        category = _failure_category(exc)
        message, retryable = _DIAGNOSTICS[category]
        cached, cache_state = _inspect_cache(cache, ttl, source="cache-fallback")
        if cached:
            snapshot = replace(cached, error=message, error_category=category, retryable=retryable)
        else:
            snapshot = unknown_snapshot(message, category=category)
        return replace(snapshot, quota_status=_status(snapshot, cache_status=cache_state,
                       phase=getattr(exc, "phase", "quota_read"), exit_code=getattr(exc, "exit_code", None)))


def _snapshot_from_dict(raw: dict[str, Any]) -> QuotaSnapshot:
    def convert(value: dict[str, Any] | None) -> Window | None:
        return Window(**value) if value else None

    return QuotaSnapshot(
        **{
            **{key: value for key, value in raw.items() if key in {f.name for f in fields(QuotaSnapshot)} and key != "quota_status"},
            "primary": convert(raw.get("primary")),
            "secondary": convert(raw.get("secondary")),
        }
    )


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
