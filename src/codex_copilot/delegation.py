from __future__ import annotations

import tomllib
import uuid
from dataclasses import dataclass
from typing import Any

from .metrics import record, records_for_run
from .paths import codex_home
from .profile import active_profile
from .quota import get_quota
from .routing import Profile, QuotaBand, TaskLevel, route_for


_BAND_ORDER = {
    QuotaBand.GREEN: 0,
    QuotaBand.YELLOW: 1,
    QuotaBand.UNKNOWN: 2,
    QuotaBand.RED: 3,
    QuotaBand.CRITICAL: 4,
}
_KNOWN_ROLES = {
    "copilot_scout",
    "copilot_investigator",
    "copilot_worker",
    "copilot_reviewer",
    "copilot_final_reviewer",
    "copilot_astra_final_reviewer",
}
_PHASES = {"exploration", "implementation", "final_review"}
_OUTCOMES = {"success", "failure"}
_ROLE_CONFIGURATION = {
    "copilot_scout": ("gpt-6-luna", "low"),
    "copilot_investigator": ("gpt-6-sol", "medium"),
    "copilot_worker": ("gpt-6-sol", "medium"),
    "copilot_reviewer": ("gpt-6-sol", "high"),
    "copilot_final_reviewer": ("gpt-6-sol", "high"),
    "copilot_astra_final_reviewer": ("gpt-6-astra", "high"),
}


@dataclass(frozen=True)
class DispatchSpec:
    role: str
    model: str
    effort: str


class DelegationDenied(ValueError):
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
        raw = tomllib.loads(path.read_text())
        model = raw["model"]
        effort = raw["model_reasoning_effort"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DelegationDenied(f"Missing or invalid installed agent configuration for {role}") from exc
    if not isinstance(model, str) or not isinstance(effort, str):
        raise DelegationDenied(f"Missing or invalid installed agent configuration for {role}")
    if (model, effort) != _ROLE_CONFIGURATION[role]:
        raise DelegationDenied(f"Installed agent configuration violates Copilot policy for {role}")
    return DispatchSpec(role=role, model=model, effort=effort)


def _effective_band(records: list[dict[str, Any]], current: QuotaBand) -> QuotaBand:
    observed = [current]
    for item in records:
        raw = item.get("effective_quota_band") or item.get("quota_band")
        try:
            observed.append(QuotaBand(raw))
        except (TypeError, ValueError):
            continue
    return max(observed, key=lambda band: _BAND_ORDER[band])


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


def dispatch(
    *, run_id: str, level: TaskLevel, role: str, phase: str, override: bool = False,
    astra_unavailable: bool = False, profile: Profile | None = None, read_only: bool = False
) -> dict[str, Any]:
    try:
        parsed_run_id = uuid.UUID(run_id)
    except (ValueError, AttributeError) as exc:
        raise DelegationDenied("run_id must be a canonical opaque UUID") from exc
    if str(parsed_run_id) != run_id.lower():
        raise DelegationDenied("run_id must be a canonical opaque UUID")
    if phase not in _PHASES:
        raise DelegationDenied(f"Unknown delegation phase: {phase}")
    records = records_for_run(run_id)
    selected_profile = profile or active_profile()
    prior_profiles = {item.get("profile") for item in _dispatched(records) if item.get("profile")}
    if prior_profiles and prior_profiles != {selected_profile.value}:
        raise DelegationDenied("Profile is pinned by the first subagent dispatch for this run")
    snapshot = get_quota(refresh=True)
    current = QuotaBand(snapshot.band)
    effective = _effective_band(records, current)
    prior = _dispatched(records)
    allowed = _allow_role(level, effective, role, phase, len(prior), astra_unavailable, selected_profile)
    if effective is QuotaBand.YELLOW and level in {TaskLevel.L1, TaskLevel.L2} and read_only:
        allowed = role in {"copilot_scout", "copilot_investigator"} and phase == "exploration" and not prior
    if not allowed and not override:
        route = route_for(effective, level, selected_profile)
        raise DelegationDenied(
            f"Delegation blocked: effective {effective.value} route permits no {role} dispatch "
            f"after {len(prior)} subagent(s). {route.reason}"
        )
    spec = dispatch_spec(role, selected_profile)
    ordinal = len(prior) + 1
    event = {
        "event": "subagent_dispatched",
        "run_id": run_id,
        "surface": "skill",
        "task_level": level.value,
        "quota_band": current.value,
        "quota_source": snapshot.source,
        "effective_quota_band": effective.value,
        "profile": selected_profile.value,
        "primary_used_percent": snapshot.primary.used_percent if snapshot.primary else None,
        "secondary_used_percent": snapshot.secondary.used_percent if snapshot.secondary else None,
        "subagent_role": spec.role,
        "subagent_ordinal": ordinal,
        "subagent_model": spec.model,
        "subagent_effort": spec.effort,
        "subagent_phase": phase,
        "override": override or None,
        "outcome": "dispatched",
    }
    record(event)
    return event


def complete(*, run_id: str, ordinal: int, outcome: str) -> dict[str, Any]:
    if outcome not in _OUTCOMES:
        raise DelegationDenied(f"Unknown delegation outcome: {outcome}")
    dispatched = _dispatched(records_for_run(run_id))
    matching = next((item for item in dispatched if item.get("subagent_ordinal") == ordinal), None)
    if not matching:
        raise DelegationDenied(f"No dispatched subagent #{ordinal} found for run {run_id}")
    event = {
        "event": "subagent_completed",
        "run_id": run_id,
        "surface": "skill",
        "task_level": matching.get("task_level"),
        "quota_band": matching.get("quota_band"),
        "quota_source": matching.get("quota_source"),
        "effective_quota_band": matching.get("effective_quota_band"),
        "profile": matching.get("profile"),
        "subagent_role": matching.get("subagent_role"),
        "subagent_ordinal": ordinal,
        "subagent_model": matching.get("subagent_model"),
        "subagent_effort": matching.get("subagent_effort"),
        "subagent_phase": matching.get("subagent_phase"),
        "override": matching.get("override"),
        "outcome": outcome,
    }
    record(event)
    return event


def trace(run_id: str | None = None) -> dict[str, Any]:
    from .metrics import latest_trace_run_id

    selected = run_id or latest_trace_run_id()
    if not selected:
        return {"found": False, "message": "No subagent trace found."}
    events = records_for_run(selected)
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
        "agents": agents,
    }
