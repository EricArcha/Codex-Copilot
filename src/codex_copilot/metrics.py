from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .paths import state_dir


MAX_BYTES = 5 * 1024 * 1024
ROTATIONS = 3
ALLOWED_FIELDS = {
    "schema",
    "timestamp",
    "event",
    "run_id",
    "surface",
    "project_hash",
    "task_level",
    "quota_band",
    "quota_source",
    "primary_used_percent",
    "secondary_used_percent",
    "primary_delta_observed",
    "secondary_delta_observed",
    "root_model",
    "root_effort",
    "subagent_count",
    "outcome",
    "elapsed_seconds",
    "error_category",
    "effective_quota_band",
    "subagent_role",
    "subagent_ordinal",
    "subagent_model",
    "subagent_effort",
    "subagent_phase",
    "override",
    "profile",
    "variant",
    "task_kind",
    "primary_resets_at",
    "secondary_resets_at",
}


def metrics_path() -> Path:
    return state_dir() / "metrics" / "runs.jsonl"


def _salt() -> str:
    path = state_dir() / "metrics" / ".salt"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(32))
        path.chmod(0o600)
    return path.read_text().strip()


def project_hash(path: str | None) -> str | None:
    if not path:
        return None
    resolved = str(Path(path).expanduser().resolve())
    return hashlib.sha256(f"{_salt()}:{resolved}".encode()).hexdigest()[:16]


def _rotate(path: Path) -> None:
    if not path.exists() or path.stat().st_size < MAX_BYTES:
        return
    oldest = path.with_name(f"{path.name}.{ROTATIONS}")
    oldest.unlink(missing_ok=True)
    for index in range(ROTATIONS - 1, 0, -1):
        source = path.with_name(f"{path.name}.{index}")
        if source.exists():
            source.replace(path.with_name(f"{path.name}.{index + 1}"))
    path.replace(path.with_name(f"{path.name}.1"))


def record(event: dict[str, Any]) -> None:
    unknown = set(event) - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"Metrics rejected unapproved fields: {', '.join(sorted(unknown))}")
    run_id = event.get("run_id")
    if run_id is not None:
        try:
            parsed = uuid.UUID(str(run_id))
        except (ValueError, AttributeError) as exc:
            raise ValueError("Metrics rejected non-opaque run_id") from exc
        if str(parsed) != str(run_id).lower():
            raise ValueError("Metrics rejected non-canonical run_id")
    clean = {key: value for key, value in event.items() if key in ALLOWED_FIELDS and value is not None}
    clean.setdefault("schema", 1)
    clean.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    path = metrics_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _rotate(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(clean, sort_keys=True, separators=(",", ":")) + "\n")


def records_for_run(run_id: str) -> list[dict[str, Any]]:
    """Return privacy-safe events for one retained run, in write order."""
    records: list[dict[str, Any]] = []
    for path in _retained_paths():
        for line in path.read_text().splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if item.get("run_id") == run_id:
                records.append(item)
    return records


def _retained_paths() -> list[Path]:
    path = metrics_path()
    return [candidate for candidate in
            [*(path.with_name(f"{path.name}.{index}") for index in range(ROTATIONS, 0, -1)), path]
            if candidate.exists()]


def retained_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in _retained_paths():
        for line in path.read_text().splitlines():
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
    return records


def latest_trace_run_id() -> str | None:
    """Find the most recently dispatched retained subagent run."""
    latest: str | None = None
    for item in retained_records():
        if item.get("event") == "subagent_dispatched" and isinstance(item.get("run_id"), str):
            latest = item["run_id"]
    return latest


def summarize(days: int) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    counts: Counter[str] = Counter()
    planned_routes: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    elapsed: defaultdict[str, list[float]] = defaultdict(list)
    primary_deltas: defaultdict[str, list[float]] = defaultdict(list)
    secondary_deltas: defaultdict[str, list[float]] = defaultdict(list)
    recent: list[dict[str, Any]] = []
    for item in retained_records():
        try:
            timestamp = datetime.fromisoformat(item["timestamp"])
        except (ValueError, KeyError, TypeError):
            continue
        if timestamp.tzinfo is not None and timestamp >= cutoff:
            recent.append(item)
    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    legacy_without_id = 0
    for item in recent:
        if item.get("run_id"):
            groups[item["run_id"]].append(item)
        else:
            legacy_without_id += 1
            if item.get("event") == "launch":
                planned_routes[f"{item.get('root_model', 'unknown')}:{item.get('root_effort', 'unknown')}"] += 1
    complete_samples = 0
    for events in groups.values():
        begin = next((e for e in events if e.get("event") == "measurement_begin"), None)
        end = next((e for e in events if e.get("event") == "measurement_end"), None)
        root = begin or next((e for e in events if e.get("root_model")), events[0])
        route = f"{root.get('root_model', 'unknown')}:{root.get('root_effort', 'unknown')}"
        counts[route] += 1
        final = end or next((e for e in events if e.get("event") == "complete"), None)
        outcomes[final.get("outcome", "unknown") if final else "unknown"] += 1
        if final and isinstance(final.get("elapsed_seconds"), (int, float)):
            elapsed[route].append(float(final["elapsed_seconds"]))
        if begin and end and end.get("outcome") == "success" and all(begin.get(k) is not None and end.get(k) is not None for k in
                                 ("primary_used_percent", "secondary_used_percent", "primary_resets_at", "secondary_resets_at")):
            if (begin["primary_resets_at"] == end["primary_resets_at"] and
                begin["secondary_resets_at"] == end["secondary_resets_at"] and
                end["primary_used_percent"] >= begin["primary_used_percent"] and
                end["secondary_used_percent"] >= begin["secondary_used_percent"]):
                complete_samples += 1
                primary_deltas[route].append(end["primary_used_percent"] - begin["primary_used_percent"])
                secondary_deltas[route].append(end["secondary_used_percent"] - begin["secondary_used_percent"])
    return {
        "days": days,
        "records": len(recent),
        "tasks": len(groups),
        "complete_samples": complete_samples,
        "legacy_incomplete": len(groups) - complete_samples + legacy_without_id,
        "subagent_dispatches": sum(e.get("event") == "subagent_dispatched" for e in recent),
        "routes": dict(counts),
        "planned_launches": sum(planned_routes.values()),
        "planned_routes": dict(planned_routes),
        "outcomes": dict(outcomes),
        "average_elapsed_seconds": {
            route: round(sum(values) / len(values), 2) for route, values in elapsed.items()
        },
        "average_primary_delta_observed": {
            route: round(sum(values) / len(values), 3) for route, values in primary_deltas.items()
        },
        "average_secondary_delta_observed": {
            route: round(sum(values) / len(values), 3) for route, values in secondary_deltas.items()
        },
        "note": "Quota changes are observational and are not exact per-task costs.",
    }
