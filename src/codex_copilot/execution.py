"""Durable, privacy-safe authorization for one Desktop orchestration run.

This is execution state, not optional measurement or a model billing ledger.
Only opaque identifiers, policy enums and numeric counters belong here.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

from .paths import state_dir
from .quota import QuotaSnapshot, cached_quota
from .routing import QuotaBand

APPLICATION_ID = 0x43435045
SCHEMA = 1
STAGES = ("offline", "smoke", "pilot", "batch")
CATEGORIES = {"research", "generation", "validation", "repair", "scoring", "probe", "review", "subagent"}
PHASES = {"exploration", "implementation", "final_review", "evaluation"}
BAND_ORDER = {"green": 0, "yellow": 1, "unknown": 2, "red": 3, "critical": 4}
OUTCOMES = {"success", "failure", "cancelled", "unknown"}


class ExecutionDenied(ValueError):
    """A safe fixed diagnostic; never include raw SQLite or child output."""


def opaque_id(value: str) -> str:
    try:
        canonical = str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError):
        raise ExecutionDenied("Identifier must be a canonical opaque UUID") from None
    if canonical != value:
        raise ExecutionDenied("Identifier must be a canonical opaque UUID")
    return canonical


def _integer(value: int, minimum: int = 0) -> bool:
    return type(value) is int and minimum <= value <= 1_000_000


def _number(value: float, maximum: float = 100) -> bool:
    return type(value) in (float, int) and math.isfinite(value) and 0 <= value <= maximum


@contextmanager
def _database(*, create: bool = False, read_only: bool = False) -> Iterator[sqlite3.Connection]:
    path = state_dir() / "execution.sqlite3"
    connection = None
    created = False
    try:
        if path.is_symlink():
            raise ExecutionDenied("Execution state is an unexpected symlink")
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(fd)
                created = True
        if not path.is_file():
            raise ExecutionDenied("Execution state unavailable; explicitly begin or recover the run")
        mode = "ro" if read_only else "rw"
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=" + mode, uri=True, timeout=5)
        if not read_only:
            connection.execute("BEGIN IMMEDIATE")
        app_id = connection.execute("PRAGMA application_id").fetchone()[0]
        if created:
            connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version={SCHEMA}")
            connection.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        elif app_id != APPLICATION_ID or connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA:
            raise ExecutionDenied("Unrecognized execution state; preserve it and recover explicitly")
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ExecutionDenied("Execution state failed integrity checks")
        yield connection
        connection.commit()
    except ExecutionDenied:
        # Observed restrictive bands and blockers must survive a denied call.
        if connection is not None:
            connection.commit()
        raise
    except (sqlite3.Error, OSError, ValueError, KeyError, TypeError):
        if connection is not None:
            connection.rollback()
        raise ExecutionDenied("Execution state unavailable or invalid; no call authorized") from None
    finally:
        if connection is not None:
            connection.close()


def _load(db: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    row = db.execute("SELECT payload FROM runs WHERE run_id=?", (opaque_id(run_id),)).fetchone()
    if not row:
        raise ExecutionDenied("Run not found; explicitly begin or recover it")
    data = json.loads(row[0])
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or data.get("run_id") != run_id:
        raise ExecutionDenied("Invalid run state; no call authorized")
    if (not _integer(data["consumed"]) or not _integer(data["legacy_consumed"]) or
            data["consumed"] != data["legacy_consumed"] + len(data["calls"]) or
            data["child_consumed"] != data["legacy_consumed"] + sum(c["kind"] == "subagent" for c in data["calls"]) or
            data["effective_band"] not in {None, *BAND_ORDER} or data["status"] not in {"active", "paused", "failed", "completed"}):
        raise ExecutionDenied("Invalid run counters or policy state; no call authorized")
    return data


def _save(db: sqlite3.Connection, data: dict[str, Any]) -> None:
    db.execute("UPDATE runs SET payload=? WHERE run_id=?", (json.dumps(data, sort_keys=True), data["run_id"]))


def begin(*, run_id: str, normal_calls: int | None = None, worst_calls: int | None = None,
          call_limit: int | None = None, reserve_calls: int = 0, comparison: bool = False,
          quota_limit_pp: float | None = None, quota_reserve_pp: float = 0,
          resume_consumed: int | None = None, smoke_calls: int = 3,
          pilot_calls: int = 3, batch_calls: int = 3,
          task_level: str | None = None, profile: str | None = None) -> dict[str, Any]:
    run_id = opaque_id(run_id)
    if task_level not in {None, "L0", "L1", "L2", "L3"} or profile not in {None, "balanced", "conservative", "premium"}:
        raise ExecutionDenied("Invalid initial task level or profile")
    planned = all(v is not None for v in (normal_calls, worst_calls, call_limit))
    if any(v is not None for v in (normal_calls, worst_calls, call_limit)) and not planned:
        raise ExecutionDenied("Budget requires normal calls, worst calls and a total call limit")
    if not all(_integer(v, 1) for v in (smoke_calls, pilot_calls, batch_calls)):
        raise ExecutionDenied("Stage call limits must be positive integers")
    if not _integer(reserve_calls) or type(comparison) is not bool:
        raise ExecutionDenied("Invalid budget reserve or comparison flag")
    if planned and (not all(_integer(v) for v in (normal_calls, worst_calls, call_limit)) or
                    not 0 < normal_calls <= worst_calls or not reserve_calls <= call_limit or call_limit < 1):
        raise ExecutionDenied("Invalid call budget")
    if not planned and reserve_calls:
        raise ExecutionDenied("Offline-only runs cannot reserve model calls")
    if quota_limit_pp is not None and (not _number(quota_limit_pp) or quota_limit_pp <= 0):
        raise ExecutionDenied("Invalid observed quota limit")
    if not _number(quota_reserve_pp) or (quota_limit_pp is None and quota_reserve_pp) or (
            quota_limit_pp is not None and quota_reserve_pp >= quota_limit_pp):
        raise ExecutionDenied("Invalid observed quota reserve")
    if resume_consumed is not None and not _integer(resume_consumed):
        raise ExecutionDenied("Invalid confirmed recovery count")
    policy = dict(normal_calls=normal_calls, worst_calls=worst_calls, call_limit=call_limit or 0,
                  reserve_calls=reserve_calls, comparison=comparison, quota_limit_pp=quota_limit_pp,
                  quota_reserve_pp=quota_reserve_pp, resume_consumed=resume_consumed,
                  smoke_calls=smoke_calls, pilot_calls=pilot_calls, batch_calls=batch_calls,
                  initial_task_level=task_level, initial_profile=profile)
    with _database(create=True) as db:
        row = db.execute("SELECT payload FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row:
            data = _load(db, run_id)
            expected = dict(data["policy"], resume_consumed=resume_consumed)
            resuming = data["status"] == "paused" and resume_consumed is not None
            if data["policy"] != policy and (expected != policy or not resuming):
                raise ExecutionDenied("Run already exists with a different budget; it cannot be reset")
            if resuming:
                if resume_consumed != data["consumed"]:
                    raise ExecutionDenied("Recovery count must equal the durable consumed count")
                data["status"] = "active"
                _save(db, data)
            return _summary(data)
        # Retained logs are relevant only when importing a legacy run. Failure
        # to inspect them must never be silently treated as zero consumption.
        from .metrics import records_for_run
        try:
            legacy = [e for e in records_for_run(run_id) if e.get("event") == "subagent_dispatched"]
        except (OSError, ValueError, AttributeError, TypeError):
            raise ExecutionDenied("Legacy evidence unavailable; no new run authorized") from None
        minimum = max([len(legacy), *(e.get("subagent_ordinal", 0) for e in legacy)])
        if legacy and resume_consumed is None:
            raise ExecutionDenied("Legacy run requires an explicit confirmed consumed count")
        if resume_consumed is not None and resume_consumed < minimum:
            raise ExecutionDenied("Confirmed recovery count is below retained legacy evidence")
        consumed = resume_consumed or 0
        if consumed and (not planned or consumed > call_limit):
            raise ExecutionDenied("Recovery requires a budget covering already consumed calls")
        baseline = None
        if quota_limit_pp is not None:
            snapshot = cached_quota(ttl=60)
            if snapshot is None or snapshot.primary is None or snapshot.primary.resets_at is None:
                raise ExecutionDenied("Observed allowance guard requires the recent trusted Start quota snapshot")
            baseline = dict(used=snapshot.primary.used_percent, resets_at=snapshot.primary.resets_at)
        effective = max([e.get("effective_quota_band", e.get("quota_band", "unknown")) for e in legacy],
                        key=lambda b: BAND_ORDER.get(b, 2), default=None)
        data = dict(schema=SCHEMA, run_id=run_id, policy=policy, status="active", calls=[], grants=[],
                    consumed=consumed, legacy_consumed=consumed, child_consumed=consumed,
                    current_band=None, effective_band=effective, quota_source=None, quota_baseline=baseline,
                    quota_delta_pp=0 if baseline else None, quota_guard_blocked=False, stage="offline", passed=[],
                    evidence=[], blocker=None, blocker_count=0, paused=False,
                    batch_start=0, engineering="pending", effect="pending" if comparison else "not_required", review="pending",
                    task_level=legacy[0].get("task_level") if legacy else task_level,
                    profile=legacy[0].get("profile", "balanced") if legacy else profile)
        db.execute("INSERT INTO runs VALUES (?,?)", (run_id, json.dumps(data, sort_keys=True)))
        return _summary(data)


def _summary(data: dict[str, Any]) -> dict[str, Any]:
    return {k: data[k] for k in ("schema", "run_id", "policy", "status", "consumed", "child_consumed",
            "legacy_consumed", "current_band", "effective_band", "quota_source", "quota_delta_pp",
            "quota_guard_blocked", "stage", "passed", "blocker", "blocker_count", "paused",
            "engineering", "effect", "review", "task_level", "profile")} | {
        "publication_eligible": data["status"] == "completed" and data["engineering"] == "passed"
        and data["effect"] in {"passed", "not_required"} and data["review"] == "passed",
        "configuration_label": "declared", "calls": data["calls"], "grants": data["grants"]}


def status(run_id: str) -> dict[str, Any]:
    with _database(read_only=True) as db:
        return _summary(_load(db, run_id))


def grant(*, run_id: str, grant_id: str, phase: str, category: str, count: int = 1,
          expires_in: int = 600, user_authorized: bool = False) -> dict[str, Any]:
    opaque_id(grant_id)
    if not user_authorized:
        raise ExecutionDenied("A grant requires an explicit user authorization declaration")
    if phase not in PHASES or category not in CATEGORIES or not _integer(count, 1) or not (
            type(expires_in) is int and 1 <= expires_in <= 86400):
        raise ExecutionDenied("Invalid bounded grant")
    with _database() as db:
        data = _load(db, run_id)
        if data["status"] != "active":
            raise ExecutionDenied("Run is closed")
        prior = next((g for g in data["grants"] if g["grant_id"] == grant_id), None)
        identity = dict(phase=phase, category=category, count=count, expires_in=expires_in, stage=data["stage"])
        if prior:
            if any(prior[k] != v for k, v in identity.items()):
                raise ExecutionDenied("Grant ID conflicts with existing authorization")
            return prior
        entry = dict(grant_id=grant_id, **identity, remaining=count, expires_at=time.time() + expires_in,
                     authorization="user_declared")
        data["grants"].append(entry)
        _save(db, data)
        return entry


def checkpoint(*, run_id: str, stage: str, outcome: str, evidence_id: str | None = None,
               paired: bool = False, scored: bool = False, blocker: str | None = None,
               engineering: str | None = None, effect: str | None = None,
               review: str | None = None) -> dict[str, Any]:
    if stage not in STAGES or outcome not in {"success", "blocked"}:
        raise ExecutionDenied("Invalid checkpoint")
    if evidence_id is not None:
        opaque_id(evidence_id)
    if blocker not in {None, "protocol", "interface", "quality", "runtime", "budget"}:
        raise ExecutionDenied("Invalid blocker category")
    if any(v not in {None, "pending", "passed", "failed"} for v in (engineering, review)) or (
            effect not in {None, "pending", "passed", "failed", "not_required"}):
        raise ExecutionDenied("Invalid acceptance status")
    with _database() as db:
        data = _load(db, run_id)
        if data["status"] != "active":
            raise ExecutionDenied("Run is closed")
        index = STAGES.index(stage)
        recovering = data["paused"] and stage == "offline" and outcome == "success"
        if not recovering and stage != data["stage"]:
            raise ExecutionDenied("Checkpoint must match the current stage")
        if any(s not in data["passed"] for s in STAGES[:index]):
            raise ExecutionDenied("Previous stage has no accepted evidence")
        if outcome == "success":
            if evidence_id is None or evidence_id in data["evidence"]:
                raise ExecutionDenied("Successful checkpoint requires a new opaque evidence reference")
            stage_calls = [c for c in data["calls"] if c["stage"] == stage and c["kind"] == "model"]
            if stage == "batch":
                stage_calls = stage_calls[data["batch_start"]:]
            if data["paused"] and not recovering:
                raise ExecutionDenied("Paused stage requires new offline diagnosis evidence before success")
            if stage != "offline":
                if not stage_calls or not any(c["outcome"] == "success" for c in stage_calls) or any(c["outcome"] in {None, "unknown"} for c in stage_calls):
                    raise ExecutionDenied("Real stage requires new successful calls and no unresolved model turns")
                if data["policy"]["comparison"]:
                    if not scored or not any(c["category"] == "scoring" and c["outcome"] == "success" for c in stage_calls):
                        raise ExecutionDenied("Comparison stage requires an executed independent scoring call and evidence")
                    if stage in {"pilot", "batch"} and not paired:
                        raise ExecutionDenied("Comparison expansion requires paired results and independent scoring")
            if data["policy"]["comparison"] and effect == "not_required":
                raise ExecutionDenied("Comparison effect acceptance is required")
            if effect == "passed" and data["policy"]["comparison"] and (stage not in {"pilot", "batch"} or not (paired and scored)):
                raise ExecutionDenied("Effect acceptance requires formal paired scoring")
            data["evidence"].append(evidence_id)
            if stage not in data["passed"]:
                data["passed"].append(stage)
            data.update(stage=data["stage"] if recovering else STAGES[min(index + 1, len(STAGES) - 1)],
                        blocker=None, blocker_count=0, paused=False)
            if stage == "batch":
                data["batch_start"] = sum(c["kind"] == "model" and c["stage"] == "batch" for c in data["calls"])
            for key, value in (("engineering", engineering), ("effect", effect), ("review", review)):
                if value is not None:
                    data[key] = value
        else:
            if blocker is None:
                raise ExecutionDenied("Blocked checkpoint requires a coarse blocker category")
            data["blocker_count"] = data["blocker_count"] + 1 if data["blocker"] == blocker else 1
            data["blocker"] = blocker
            data["paused"] = data["paused"] or data["blocker_count"] >= 2
        _save(db, data)
        return _summary(data)


def close(*, run_id: str, outcome: str) -> dict[str, Any]:
    if outcome not in {"completed", "paused", "failed"}:
        raise ExecutionDenied("Invalid run close outcome")
    with _database() as db:
        data = _load(db, run_id)
        if data["status"] != "active":
            if data["status"] != outcome:
                raise ExecutionDenied("Run already closed with a different outcome")
            return _summary(data)
        if outcome == "completed" and (data["engineering"] != "passed" or data["effect"] not in {"passed", "not_required"}
                                       or data["review"] != "passed" or any(c["outcome"] in {None, "unknown"} for c in data["calls"])):
            raise ExecutionDenied("Engineering, effect, review or call completion evidence is incomplete")
        data["status"] = outcome
        _save(db, data)
        return _summary(data)


def _observe(data: dict[str, Any], snapshot: QuotaSnapshot) -> None:
    current = snapshot.band if snapshot.band in BAND_ORDER else "unknown"
    data.update(current_band=current, quota_source=snapshot.source)
    data["effective_band"] = max([current, data["effective_band"] or current], key=BAND_ORDER.__getitem__)
    if data["policy"]["quota_limit_pp"] is None:
        return
    primary = snapshot.primary
    if snapshot.source not in {"app-server", "cache-fallback", "cache"} or primary is None or primary.resets_at is None:
        data["quota_guard_blocked"] = True
        return
    baseline = data["quota_baseline"]
    if baseline is None:
        data["quota_baseline"] = dict(used=primary.used_percent, resets_at=primary.resets_at)
        data["quota_delta_pp"] = 0
    elif baseline["resets_at"] != primary.resets_at or primary.used_percent < baseline["used"]:
        data["quota_guard_blocked"] = True
    else:
        data["quota_guard_blocked"] = False
        data["quota_delta_pp"] = max(data["quota_delta_pp"] or 0, primary.used_percent - baseline["used"])


def reserve(*, run_id: str, request_id: str, kind: str, category: str, phase: str,
            snapshot: QuotaSnapshot, role: str, model: str, effort: str, level: str, profile: str,
            grant_id: str | None = None, followup_id: str | None = None,
            astra_unavailable: bool = False, read_only: bool = False) -> dict[str, Any]:
    opaque_id(request_id)
    if grant_id is not None:
        opaque_id(grant_id)
    if followup_id is not None:
        opaque_id(followup_id)
    if kind not in {"subagent", "model"} or category not in CATEGORIES or phase not in PHASES:
        raise ExecutionDenied("Invalid call kind, category or phase")
    # Role/config validation happens at the entry point, before any quota override.
    from .delegation import _allow_role, validate_role, _ROLE_CONFIGURATION
    from .routing import Profile, TaskLevel
    if kind == "subagent":
        validate_role(TaskLevel(level), role, phase, Profile(profile), astra_unavailable=astra_unavailable, band="unknown")
        if _ROLE_CONFIGURATION.get(role) != (model, effort) or category != ("review" if phase == "final_review" else "subagent"):
            raise ExecutionDenied("Subagent configuration or category violates role policy")
    elif (role, model, effort, phase) != ("data_model", "gpt-6.1-sol", "medium", "evaluation") or category in {"subagent", "review"}:
        raise ExecutionDenied("Invalid data-plane model configuration")
    with _database() as db:
        data = _load(db, run_id)
        identity = dict(kind=kind, category=category, phase=phase, role=role, model=model, effort=effort,
                        level=level, profile=profile, grant_id=grant_id, followup_id=followup_id,
                        astra_unavailable=astra_unavailable, read_only=read_only)
        prior = next((c for c in data["calls"] if c["request_id"] == request_id), None)
        if prior:
            if any(prior[k] != v for k, v in identity.items()):
                raise ExecutionDenied("Request ID conflicts with an existing reservation")
            return dict(prior, replayed=True)
        if data["status"] != "active":
            raise ExecutionDenied("Run is closed")
        if data["task_level"] not in {None, level} or data["profile"] not in {None, profile}:
            raise ExecutionDenied("Task level and profile are pinned for the run")
        _observe(data, snapshot)
        _save(db, data)
        if kind == "subagent":
            validate_role(TaskLevel(level), role, phase, Profile(profile), astra_unavailable=astra_unavailable, band=data["effective_band"])
        policy = data["policy"]
        if not policy["call_limit"]:
            raise ExecutionDenied("No model budget: only offline preflight is permitted")
        if data["paused"] and kind == "model":
            raise ExecutionDenied("Repeated blocker: offline diagnosis and new evidence required")
        final = phase == "final_review" and category == "review"
        ceiling = policy["call_limit"] if final else policy["call_limit"] - policy["reserve_calls"]
        if data["consumed"] >= ceiling:
            raise ExecutionDenied("Total call limit or closing reserve reached")
        if policy["quota_limit_pp"] is not None:
            threshold = policy["quota_limit_pp"] - (0 if final else policy["quota_reserve_pp"])
            if data["quota_guard_blocked"] or data["quota_delta_pp"] >= threshold:
                raise ExecutionDenied("Observed allowance guard reached or window is no longer comparable")
        if kind == "model":
            if snapshot.source not in {"app-server", "cache-fallback", "cache"} or snapshot.band == "unknown":
                raise ExecutionDenied("Bulk model work requires trusted available quota")
            if "offline" not in data["passed"]:
                raise ExecutionDenied("Offline preflight evidence is required before a real model call")
            stage = data["stage"]
            used = sum(c["kind"] == "model" and c["stage"] == stage for c in data["calls"])
            if stage == "batch":
                used -= data["batch_start"]
            if used >= policy[stage + "_calls"]:
                raise ExecutionDenied("Stage call limit reached; checkpoint evidence is required before expansion")
        parent = None
        if followup_id:
            parent = next((c for c in data["calls"] if c["request_id"] == followup_id), None)
            if not parent or parent["outcome"] is None or not parent.get("session_id"):
                raise ExecutionDenied("Follow-up requires a completed bound session")
            if any(c["session_id"] == parent["session_id"] and c["outcome"] in {None, "unknown"} for c in data["calls"]):
                raise ExecutionDenied("Session has an unresolved turn; overlapping follow-ups are forbidden")
            if any(parent[k] != identity[k] for k in ("kind", "role", "model", "effort", "level", "profile", "phase", "category")):
                raise ExecutionDenied("Follow-up cannot change the session role, phase, model or effort")
        # A writing child cannot overlap any unresolved writing child.
        if role == "copilot_worker" and any(c["role"] == "copilot_worker" and c["outcome"] in {None, "unknown"} for c in data["calls"]):
            raise ExecutionDenied("An unresolved writing child already owns the writer slot")
        effective = QuotaBand(data["effective_band"])
        if kind == "subagent":
            allowed = _allow_role(TaskLevel(level), effective, role, phase, data["child_consumed"], astra_unavailable, Profile(profile))
            if effective is QuotaBand.YELLOW and level in {"L1", "L2"} and read_only:
                allowed = role in {"copilot_scout", "copilot_investigator"} and phase == "exploration" and not data["child_consumed"]
        else:
            allowed = effective in {QuotaBand.GREEN, QuotaBand.YELLOW}
        if grant_id:
            authorization = next((g for g in data["grants"] if g["grant_id"] == grant_id), None)
            if not authorization or authorization["phase"] != phase or authorization["category"] != category or authorization["stage"] != data["stage"] or (
                    authorization["remaining"] <= 0 or authorization["expires_at"] <= time.time()):
                raise ExecutionDenied("Grant is missing, expired, exhausted or outside this call scope")
        elif not allowed:
            raise ExecutionDenied("Route paused or cumulative child cap reached; a bounded user grant is required")
        if grant_id:
            authorization["remaining"] -= 1
        data.update(task_level=level, profile=profile, consumed=data["consumed"] + 1)
        if kind == "subagent":
            data["child_consumed"] += 1
        entry = dict(request_id=request_id, ordinal=data["consumed"], **identity,
                     child_ordinal=data["child_consumed"] if kind == "subagent" else None,
                     stage=data["stage"], current_band=data["current_band"], effective_band=data["effective_band"],
                     quota_source=snapshot.source, outcome=None, session_id=parent["session_id"] if parent else None,
                     execution_claimed=False, configuration_label="declared")
        data["calls"].append(entry)
        _save(db, data)
        return dict(entry, replayed=False)


def claim_model(*, run_id: str, request_id: str) -> bool:
    """Claim spawn once. A crash after claiming stays consumed and is never replayed."""
    with _database() as db:
        data = _load(db, run_id)
        call = next((c for c in data["calls"] if c["request_id"] == opaque_id(request_id)), None)
        if not call or call["kind"] != "model":
            raise ExecutionDenied("No model reservation")
        if call["execution_claimed"] or call["outcome"] is not None:
            return False
        call["execution_claimed"] = True
        call["configuration_label"] = "constructed"
        _save(db, data)
        return True


def complete(*, run_id: str, request_id: str, outcome: str, session_id: str | None = None) -> dict[str, Any]:
    if outcome not in OUTCOMES:
        raise ExecutionDenied("Invalid call outcome")
    if session_id is not None:
        opaque_id(session_id)
    with _database() as db:
        data = _load(db, run_id)
        call = next((c for c in data["calls"] if c["request_id"] == opaque_id(request_id)), None)
        if not call:
            raise ExecutionDenied("No call reservation found")
        if call["outcome"] is not None:
            if call["outcome"] != outcome or (session_id is not None and session_id != call["session_id"]):
                raise ExecutionDenied("Completion conflicts with the existing receipt")
            return call
        if call["session_id"] and session_id is not None and call["session_id"] != session_id:
            raise ExecutionDenied("Follow-up returned a different session")
        if session_id and any(c["session_id"] == session_id and c["request_id"] != call["request_id"] for c in data["calls"]) and not call["followup_id"]:
            raise ExecutionDenied("Session is already bound; reserve an explicit follow-up")
        call.update(outcome=outcome, session_id=session_id or call["session_id"])
        _save(db, data)
        return call


def latest_trace_run_id() -> str | None:
    try:
        with _database(read_only=True) as db:
            for (run_id,) in db.execute("SELECT run_id FROM runs ORDER BY rowid DESC").fetchall():
                data = _load(db, run_id)
                if any(c["kind"] == "subagent" for c in data["calls"]):
                    return run_id
    except ExecutionDenied:
        pass
    return None
