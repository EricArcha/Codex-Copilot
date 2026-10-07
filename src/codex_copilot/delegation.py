from __future__ import annotations

import tomllib
import uuid
from dataclasses import dataclass, replace
from typing import Any

from .metrics import record, records_for_run
from .paths import codex_home
from .profile import active_profile
from .quota import get_quota, unknown_snapshot
from .routing import Profile, QuotaBand, TaskLevel, route_for
from .config_policy import require_dispatch_config
from . import execution


_KNOWN_ROLES = {
    "copilot_scout",
    "copilot_investigator",
    "copilot_worker",
    "copilot_reviewer",
    "copilot_final_reviewer",
    "copilot_astra_final_reviewer",
}
_PHASES = {"exploration", "implementation", "final_review"}
_ROLE_CONFIGURATION = {
    "copilot_scout": ("gpt-6-luna", "low"),
    "copilot_investigator": ("gpt-6.1-sol", "medium"),
    "copilot_worker": ("gpt-6.1-sol", "medium"),
    "copilot_reviewer": ("gpt-6.1-sol", "high"),
    "copilot_final_reviewer": ("gpt-6.1-sol", "high"),
    "copilot_astra_final_reviewer": ("gpt-6-astra", "high"),
}


@dataclass(frozen=True)
class DispatchSpec:
    role: str
    model: str
    effort: str


class DelegationDenied(execution.ExecutionDenied):
    pass


def _agent_path(role: str):
    return codex_home() / "agents" / f"{role.replace('_', '-')}.toml"


def dispatch_spec(role: str, profile: Profile) -> DispatchSpec:
    if role not in _KNOWN_ROLES:
        raise DelegationDenied(f"Unknown Copilot role: {role}")
    if role == "copilot_astra_final_reviewer" and profile is not Profile.PREMIUM:
        raise DelegationDenied("Astra final review requires the premium profile")
    path = _agent_path(role)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        model = raw["model"]
        effort = raw["model_reasoning_effort"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DelegationDenied(f"Missing or invalid installed agent configuration for {role}") from exc
    if not isinstance(model, str) or not isinstance(effort, str):
        raise DelegationDenied(f"Missing or invalid installed agent configuration for {role}")
    if (model, effort) != _ROLE_CONFIGURATION[role]:
        raise DelegationDenied(f"Installed agent configuration violates Copilot policy for {role}")
    from .installer import InstallError, artifact_matches, load_manifest
    try:
        manifest = load_manifest()
        if manifest:
            item = next((a for a in manifest["artifacts"] if a["target"] == str(path)), None)
            if not item or not artifact_matches(item):
                raise DelegationDenied(f"Installed agent artifact is missing or modified for {role}")
    except (OSError, InstallError):
        raise DelegationDenied(f"Cannot verify installed agent artifact for {role}") from None
    return DispatchSpec(role=role, model=model, effort=effort)


def _dispatched(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in records if item.get("event") == "subagent_dispatched"]


def _valid_role_phase(level: TaskLevel, role: str, phase: str) -> bool:
    if role in {"copilot_scout", "copilot_investigator"}:
        return phase == "exploration"
    if role == "copilot_worker":
        return level is not TaskLevel.L3 and phase == "implementation"
    return phase == "final_review"


def _allow_role(
    level: TaskLevel, band: QuotaBand, role: str, phase: str, count: int, astra_unavailable: bool, profile: Profile
) -> bool:
    if not _valid_role_phase(level, role, phase):
        return False
    if level is TaskLevel.L0 or band in {QuotaBand.RED, QuotaBand.CRITICAL}:
        return False
    if level is TaskLevel.L3:
        if band is QuotaBand.GREEN:
            if role in {"copilot_scout", "copilot_investigator"}:
                return count == 0
            if role == "copilot_final_reviewer" and profile is not Profile.PREMIUM:
                return count <= 1
            if role == "copilot_astra_final_reviewer" and profile is Profile.PREMIUM:
                return count <= 1
            return role == "copilot_reviewer" and astra_unavailable and profile is Profile.PREMIUM and count <= 1
        if band is QuotaBand.YELLOW:
            return count == 0 and (
                (role == "copilot_final_reviewer" and profile is not Profile.PREMIUM)
                or (role == "copilot_astra_final_reviewer" and profile is Profile.PREMIUM)
                or (role == "copilot_reviewer" and astra_unavailable and profile is Profile.PREMIUM)
            )
        if band is QuotaBand.UNKNOWN:
            return count == 0 and role == "copilot_reviewer"
        return False
    # L1/L2 reserve the final slot for the standard independent reviewer.
    if band is QuotaBand.GREEN:
        if role == "copilot_reviewer":
            return count < 2
        return role in {"copilot_scout", "copilot_investigator", "copilot_worker"} and count == 0
    return count == 0 and role == "copilot_reviewer"


def validate_role(level: TaskLevel, role: str, phase: str, profile: Profile,
                  *, astra_unavailable: bool = False, band: str | None = None) -> None:
    if role not in _KNOWN_ROLES or level is TaskLevel.L0 or not _valid_role_phase(level, role, phase):
        raise DelegationDenied("Role and phase violate the task policy; grants cannot override this")
    if level is not TaskLevel.L3 and role in {"copilot_final_reviewer", "copilot_astra_final_reviewer"}:
        raise DelegationDenied("Reserved final-review roles require L3")
    if role == "copilot_final_reviewer" and profile is Profile.PREMIUM:
        raise DelegationDenied("Premium L3 uses its dedicated final reviewer")
    if level is TaskLevel.L3 and role == "copilot_reviewer" and not (
            band == "unknown" or (profile is Profile.PREMIUM and astra_unavailable)):
        raise DelegationDenied("L3 standard reviewer is only an unknown-route or premium fallback")


def _record_best_effort(event: dict[str, Any]) -> None:
    try:
        record(event)
    except (OSError, ValueError):
        pass


def dispatch(
    *, run_id: str, level: TaskLevel, role: str, phase: str, override: bool = False,
    astra_unavailable: bool = False, profile: Profile | None = None, read_only: bool = False,
    request_id: str | None = None, grant_id: str | None = None, followup_id: str | None = None,
) -> dict[str, Any]:
    if override:
        raise DelegationDenied("Bare --override is no longer accepted; use a scoped, expiring grant")
    try:
        execution.opaque_id(run_id)
    except execution.ExecutionDenied as exc:
        raise DelegationDenied(str(exc)) from None
    if phase not in _PHASES:
        raise DelegationDenied("Unknown delegation phase")
    try:
        require_dispatch_config()
    except ValueError as exc:
        raise DelegationDenied(str(exc)) from None
    selected_profile = profile or active_profile()
    spec = dispatch_spec(role, selected_profile)
    # Structural checks precede acquisition; the unknown-route fallback is checked below.
    validate_role(level, role, phase, selected_profile, astra_unavailable=astra_unavailable, band="unknown")
    state = execution.status(run_id)
    prior = next((c for c in state["calls"] if c["request_id"] == request_id), None)
    if prior:
        snapshot = replace(unknown_snapshot("Request replay"), band=prior["current_band"], source=prior["quota_source"])
    else:
        snapshot = get_quota(refresh=True)
    try:
        call = execution.reserve(
            run_id=run_id, request_id=request_id or str(uuid.uuid4()), kind="subagent",
            category="review" if phase == "final_review" else "subagent", phase=phase,
            snapshot=snapshot, role=spec.role, model=spec.model, effort=spec.effort,
            level=level.value, profile=selected_profile.value, grant_id=grant_id,
            followup_id=followup_id, astra_unavailable=astra_unavailable, read_only=read_only,
        )
    except execution.ExecutionDenied as exc:
        raise DelegationDenied(str(exc)) from None
    event = _dispatch_event(run_id, call)
    event["replayed"] = call["replayed"]
    event["outcome"] = call["outcome"] or "dispatched"
    if not call["replayed"]:
        _record_best_effort({k: v for k, v in event.items() if k != "replayed"})
    return event


def _dispatch_event(run_id: str, call: dict[str, Any]) -> dict[str, Any]:
    return dict(event="subagent_dispatched", run_id=run_id, surface="skill",
                task_level=call["level"], quota_band=call["current_band"],
                quota_source=call["quota_source"], effective_quota_band=call["effective_band"],
                profile=call["profile"], subagent_role=call["role"], subagent_ordinal=call["child_ordinal"],
                subagent_model=call["model"], subagent_effort=call["effort"], subagent_phase=call["phase"],
                override=bool(call["grant_id"]), request_id=call["request_id"], grant_id=call["grant_id"],
                configuration_label="declared", outcome="dispatched")


def complete(*, run_id: str, ordinal: int, outcome: str, session_id: str | None = None) -> dict[str, Any]:
    try:
        state = execution.status(run_id)
        call = next((c for c in state["calls"] if c["kind"] == "subagent" and c["child_ordinal"] == ordinal), None)
        if call is None:
            raise execution.ExecutionDenied("No durable subagent reservation found")
        already = call["outcome"] is not None
        finished = execution.complete(run_id=run_id, request_id=call["request_id"], outcome=outcome, session_id=session_id)
    except execution.ExecutionDenied as exc:
        raise DelegationDenied(str(exc)) from None
    event = _dispatch_event(run_id, finished)
    event.update(event="subagent_completed", outcome=outcome)
    if not already:
        _record_best_effort(event)
    return event


def trace(run_id: str | None = None) -> dict[str, Any]:
    from .metrics import latest_trace_run_id

    selected = run_id or execution.latest_trace_run_id() or latest_trace_run_id()
    if not selected:
        return {"found": False, "message": "No subagent trace found."}
    events = records_for_run(selected)
    state = None
    try:
        state = execution.status(selected)
    except execution.ExecutionDenied:
        pass
    if state is not None:
        events = [e for e in events if state["legacy_consumed"] and
                  type(e.get("subagent_ordinal")) is int and
                  0 < e["subagent_ordinal"] <= state["legacy_consumed"] and
                  e.get("event") in {"subagent_dispatched", "subagent_completed"}]
        for call in state["calls"]:
            if call["kind"] != "subagent":
                continue
            event = _dispatch_event(selected, call)
            events.append(event)
            if call["outcome"] is not None:
                events.append(dict(event, event="subagent_completed", outcome=call["outcome"]))
    dispatched = _dispatched(events)
    if not dispatched:
        return {"found": False, "run_id": selected, "message": "No subagent trace found for this run."}
    completed = {
        item.get("subagent_ordinal"): item for item in events if item.get("event") == "subagent_completed"
    }
    agents = []
    for item in dispatched:
        finished = completed.get(item.get("subagent_ordinal"))
        agents.append(
            {
                "ordinal": item.get("subagent_ordinal"),
                "role": item.get("subagent_role"),
                "model": item.get("subagent_model"),
                "effort": item.get("subagent_effort"),
                "phase": item.get("subagent_phase"),
                "quota_source": item.get("quota_source"),
                "status": finished.get("outcome") if finished else "dispatched",
                "override": bool(item.get("override")),
            }
        )
    return {
        "found": True,
        "run_id": selected,
        "task_level": dispatched[0].get("task_level"),
        "effective_quota_band": dispatched[-1].get("effective_quota_band"),
        "profile": dispatched[0].get("profile", "balanced"),
        "dispatched": len(agents),
        "compliance": "OVERRIDDEN BY USER" if any(agent["override"] for agent in agents) else "COMPLIANT",
        "configuration_label": "declared",
        "legacy": state is None or bool(state["legacy_consumed"]),
        "agents": agents,
    }
