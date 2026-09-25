"""Optional, local observations of task-level Codex allowance usage."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .metrics import project_hash, record, records_for_run
from .paths import state_dir
from .quota import QuotaSnapshot, get_quota


VARIANTS = {"skill", "baseline"}
TASK_KINDS = {"bugfix", "feature", "refactor", "maintenance"}
OUTCOMES = {"success", "failure", "paused"}


def settings_path() -> Path:
    return state_dir() / "measurement.json"


def enabled() -> bool:
    try:
        return json.loads(settings_path().read_text()).get("enabled") is True
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def set_enabled(value: bool) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if path.is_symlink():
        raise ValueError("measurement preference is an unexpected symlink")
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise ValueError("measurement preference is not a recognized JSON file") from exc
        if not isinstance(existing, dict) or not isinstance(existing.get("enabled"), bool):
            raise ValueError("measurement preference has an unrecognized format")
        data = existing
    data["enabled"] = value
    fd, name = tempfile.mkstemp(prefix=".measurement-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, sort_keys=True) + "\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _run_id(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("run ID must be a canonical opaque UUID") from exc
    canonical = str(parsed)
    if canonical != value.lower():
        raise ValueError("run ID must be a canonical opaque UUID")
    return canonical


def _fields(snapshot: QuotaSnapshot | None) -> dict[str, Any]:
    if snapshot is None:
        return {"quota_source": "unavailable"}
    return {
        "quota_source": snapshot.source,
        "primary_used_percent": snapshot.primary.used_percent if snapshot.primary else None,
        "secondary_used_percent": snapshot.secondary.used_percent if snapshot.secondary else None,
        "primary_resets_at": snapshot.primary.resets_at if snapshot.primary else None,
        "secondary_resets_at": snapshot.secondary.resets_at if snapshot.secondary else None,
    }


def _provided_fields(primary_used: float | None, secondary_used: float | None,
                     primary_reset: int | None, secondary_reset: int | None) -> dict[str, Any] | None:
    values = (primary_used, secondary_used, primary_reset, secondary_reset)
    if all(value is None for value in values):
        return None
    if any(not math.isfinite(value) or not 0 <= value <= 100
           for value in (primary_used, secondary_used) if value is not None):
        raise ValueError("usage percentages must be between 0 and 100")
    if any(value <= 0 for value in (primary_reset, secondary_reset) if value is not None):
        raise ValueError("reset times must be positive Unix timestamps")
    return {
        "quota_source": "codex-app-provided" if all(value is not None for value in values) else "codex-app-provided-partial",
        "primary_used_percent": primary_used,
        "secondary_used_percent": secondary_used,
        "primary_resets_at": primary_reset,
        "secondary_resets_at": secondary_reset,
    }


def begin(*, run_id: str, variant: str, task_level: str, task_kind: str,
          root_model: str, project: str, if_enabled: bool = False,
          primary_used: float | None = None, secondary_used: float | None = None,
          primary_reset: int | None = None, secondary_reset: int | None = None) -> dict[str, Any]:
    if if_enabled and not enabled():
        return {"recorded": False, "reason": "measurement disabled"}
    run_id = _run_id(run_id)
    if variant not in VARIANTS or task_level not in {"L0", "L1", "L2", "L3"} or task_kind not in TASK_KINDS:
        raise ValueError("invalid measurement variant, task level, or task kind")
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,63}", root_model) or not project:
        raise ValueError("root model and project are required")
    hashed_project = project_hash(project)
    prior = records_for_run(run_id)
    existing = next((e for e in prior if e.get("event") == "measurement_begin"), None)
    if existing:
        expected = {"variant": variant, "task_level": task_level, "task_kind": task_kind,
                    "root_model": root_model, "project_hash": hashed_project}
        if any(existing.get(key) != value for key, value in expected.items()):
            raise ValueError("measurement begin conflicts with the existing run")
        return {"recorded": False, "reason": "already begun", "event": existing}
    if any(e.get("event") == "measurement_end" for e in prior):
        raise ValueError("measurement already ended")
    fields = _provided_fields(primary_used, secondary_used, primary_reset, secondary_reset)
    if fields is None:
        # A skill run reuses the quota check performed by its Start step. The
        # baseline is the only variant that may make a new start-time read.
        snapshot = get_quota(refresh=True, timeout=5) if variant == "baseline" else None
        if variant == "skill":
            from .quota import cached_quota
            snapshot = cached_quota(ttl=60)
        fields = _fields(snapshot if variant == "skill" or (snapshot and snapshot.source == "app-server") else None)
    event = {
        "schema": 2,
        "event": "measurement_begin",
        "run_id": run_id,
        "surface": "measurement",
        "variant": variant,
        "task_level": task_level,
        "task_kind": task_kind,
        "root_model": root_model,
        "project_hash": hashed_project,
        **fields,
    }
    record(event)
    return {"recorded": True, "event": event}


def end(*, run_id: str, outcome: str, variant: str | None = None,
        primary_used: float | None = None, secondary_used: float | None = None,
        primary_reset: int | None = None, secondary_reset: int | None = None) -> dict[str, Any]:
    run_id = _run_id(run_id)
    if outcome not in OUTCOMES:
        raise ValueError("invalid measurement outcome")
    prior = records_for_run(run_id)
    begin_event = next((e for e in prior if e.get("event") == "measurement_begin"), None)
    if not begin_event:
        raise ValueError("measurement has no begin event")
    if variant and variant != begin_event["variant"]:
        raise ValueError("measurement variant does not match begin event")
    existing = next((e for e in prior if e.get("event") == "measurement_end"), None)
    if existing:
        if existing.get("outcome") != outcome:
            raise ValueError("measurement end conflicts with the existing outcome")
        return {"recorded": False, "reason": "already ended", "event": existing}
    fields = _provided_fields(primary_used, secondary_used, primary_reset, secondary_reset)
    if fields is None:
        snapshot = get_quota(refresh=True, timeout=5)
        fields = _fields(snapshot if snapshot.source == "app-server" else None)
    event = {
        "schema": 2,
        "event": "measurement_end",
        "run_id": run_id,
        "surface": "measurement",
        "variant": begin_event["variant"],
        "task_level": begin_event["task_level"],
        "task_kind": begin_event["task_kind"],
        "root_model": begin_event["root_model"],
        "project_hash": begin_event["project_hash"],
        "outcome": outcome,
        **fields,
    }
    record(event)
    return {"recorded": True, "event": event}


def _sample(run_id: str, expected_variant: str) -> dict[str, Any]:
    records = records_for_run(_run_id(run_id))
    begin_event = next((e for e in records if e.get("event") == "measurement_begin"), None)
    end_event = next((e for e in records if e.get("event") == "measurement_end"), None)
    if not begin_event or not end_event or begin_event.get("variant") != expected_variant:
        raise ValueError(f"{expected_variant} run has no complete measurement")
    if end_event.get("outcome") != "success":
        raise ValueError(f"{expected_variant} run did not complete successfully")
    for window in ("primary", "secondary"):
        reset_key = f"{window}_resets_at"
        usage_key = f"{window}_used_percent"
        if begin_event.get(reset_key) is None or begin_event.get(reset_key) != end_event.get(reset_key):
            raise ValueError(f"{expected_variant} run crossed or lacks a quota window")
        if begin_event.get(usage_key) is None or end_event.get(usage_key) is None:
            raise ValueError(f"{expected_variant} run lacks usage values")
        if end_event[usage_key] < begin_event[usage_key]:
            raise ValueError(f"{expected_variant} run has decreasing usage")
    return {"begin": begin_event, "end": end_event}


def compare(skill_run: str, baseline_run: str) -> dict[str, Any]:
    skill = _sample(skill_run, "skill")
    baseline = _sample(baseline_run, "baseline")
    keys = ("project_hash", "task_level", "task_kind")
    if any(skill["begin"].get(key) != baseline["begin"].get(key) for key in keys):
        raise ValueError("comparison requires the same project, task level, and task kind")
    deltas = {}
    for window in ("primary", "secondary"):
        key = f"{window}_used_percent"
        skill_delta = skill["end"][key] - skill["begin"][key]
        baseline_delta = baseline["end"][key] - baseline["begin"][key]
        deltas[window] = {
            "skill_observed_pp": skill_delta,
            "baseline_observed_pp": baseline_delta,
            "baseline_minus_skill_pp": baseline_delta - skill_delta,
        }
    return {
        "skill_run": skill_run,
        "baseline_run": baseline_run,
        "task_level": skill["begin"]["task_level"],
        "task_kind": skill["begin"]["task_kind"],
        "models_declared": {"skill": skill["begin"]["root_model"], "baseline": baseline["begin"]["root_model"]},
        "windows": deltas,
        "note": "Observational percentage-point difference; concurrent activity and task variation prevent causal attribution.",
    }
