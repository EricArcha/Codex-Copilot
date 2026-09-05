from __future__ import annotations

import hashlib
import json
import secrets
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
    clean = {key: value for key, value in event.items() if key in ALLOWED_FIELDS and value is not None}
    clean.setdefault("schema", 1)
    clean.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    path = metrics_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _rotate(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(clean, sort_keys=True, separators=(",", ":")) + "\n")


def summarize(days: int) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    counts: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    elapsed: defaultdict[str, list[float]] = defaultdict(list)
    primary_deltas: defaultdict[str, list[float]] = defaultdict(list)
    secondary_deltas: defaultdict[str, list[float]] = defaultdict(list)
    records = 0
    path = metrics_path()
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                item = json.loads(line)
                timestamp = datetime.fromisoformat(item["timestamp"])
            except (ValueError, KeyError, TypeError):
                continue
            if timestamp < cutoff:
                continue
            records += 1
            route = f"{item.get('root_model', 'unknown')}:{item.get('root_effort', 'unknown')}"
            counts[route] += 1
            outcomes[item.get("outcome", "unknown")] += 1
            if isinstance(item.get("elapsed_seconds"), (int, float)):
                elapsed[route].append(float(item["elapsed_seconds"]))
            if isinstance(item.get("primary_delta_observed"), (int, float)):
                primary_deltas[route].append(float(item["primary_delta_observed"]))
            if isinstance(item.get("secondary_delta_observed"), (int, float)):
                secondary_deltas[route].append(float(item["secondary_delta_observed"]))
    return {
        "days": days,
        "records": records,
        "routes": dict(counts),
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
