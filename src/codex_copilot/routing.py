from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class QuotaBand(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class Profile(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    PREMIUM = "premium"


class TaskLevel(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


@dataclass(frozen=True)
class Route:
    band: str
    level: str
    profile: str
    root_model: str
    root_effort: str
    max_subagents: int
    allow_sol: bool
    allow_astra: bool
    allow_max_or_ultra: bool
    pause: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def band_for_remaining(
    effective_remaining: float | None,
    *,
    reached: bool = False,
    spend_control_reached: bool = False,
) -> QuotaBand:
    if reached or spend_control_reached:
        return QuotaBand.CRITICAL
    if effective_remaining is None:
        return QuotaBand.UNKNOWN
    if effective_remaining >= 60:
        return QuotaBand.GREEN
    if effective_remaining >= 30:
        return QuotaBand.YELLOW
    if effective_remaining >= 10:
        return QuotaBand.RED
    return QuotaBand.CRITICAL


def band_for_windows(
    primary_remaining: float | None,
    secondary_remaining: float | None,
    *,
    reached: bool = False,
    spend_control_reached: bool = False,
) -> QuotaBand:
    """Classify collaboration capacity without treating the weekly window as a 5-hour cap."""
    if reached or spend_control_reached:
        return QuotaBand.CRITICAL
    if primary_remaining is None:
        return QuotaBand.UNKNOWN
    # Some plans expose only one applicable usage window. Preserve the prior
    # single-window behavior instead of needlessly disabling delegation.
    if secondary_remaining is None:
        return band_for_remaining(
            primary_remaining, reached=reached, spend_control_reached=spend_control_reached
        )
    if primary_remaining < 10 or secondary_remaining < 10:
        return QuotaBand.CRITICAL
    if primary_remaining < 30 or secondary_remaining < 20:
        return QuotaBand.RED
    # Green is the standard two-read-only-child budget. Yellow is guarded and
    # reserves its single slot for review.
    if primary_remaining >= 50 and secondary_remaining >= 35:
        return QuotaBand.GREEN
    return QuotaBand.YELLOW


def route_for(band: QuotaBand, level: TaskLevel, profile: Profile = Profile.BALANCED) -> Route:
    base = dict(
        band=band.value,
        level=level.value,
        profile=profile.value,
    )

    if band is QuotaBand.GREEN:
        root_model = "gpt-6-astra" if profile is Profile.PREMIUM and level is TaskLevel.L3 else "gpt-6-sol"
        root_effort = "low" if profile is Profile.CONSERVATIVE else "medium"
        return Route(
            **base,
            root_model=root_model,
            root_effort=root_effort,
            max_subagents=0 if level is TaskLevel.L0 else 2,
            allow_sol=level is TaskLevel.L3 and profile is not Profile.PREMIUM,
            allow_astra=level is TaskLevel.L3 and profile is Profile.PREMIUM,
            allow_max_or_ultra=False,
            pause=False,
            reason="Normal quota guardrails; use bounded delegation only when it adds value.",
        )
    if band is QuotaBand.YELLOW:
        return Route(
            **base,
            root_model="gpt-6-sol",
            root_effort="medium",
            max_subagents=0 if level is TaskLevel.L0 else 1,
            allow_sol=level is TaskLevel.L3 and profile is not Profile.PREMIUM,
            allow_astra=level is TaskLevel.L3 and profile is Profile.PREMIUM,
            allow_max_or_ultra=False,
            pause=False,
            reason="Preserve allowance: one subagent maximum and no Max or Ultra.",
        )
    if band is QuotaBand.RED:
        paused = level in {TaskLevel.L2, TaskLevel.L3}
        return Route(
            **base,
            root_model="gpt-6-luna" if level is TaskLevel.L0 else "gpt-6-sol",
            root_effort="low",
            max_subagents=0,
            allow_sol=False,
            allow_astra=False,
            allow_max_or_ultra=False,
            pause=paused,
            reason=(
                "Complex work is paused until reset so testing and review are not sacrificed."
                if paused
                else "Continue without parallel delegation using the lowest safe effort."
            ),
        )
    if band is QuotaBand.CRITICAL:
        return Route(
            **base,
            root_model="gpt-6-luna",
            root_effort="low",
            max_subagents=0,
            allow_sol=False,
            allow_astra=False,
            allow_max_or_ultra=False,
            pause=True,
            reason="Do not begin code changes; produce a checkpoint and wait for reset or explicit override.",
        )
    return Route(
        **base,
        root_model="gpt-6-sol",
        root_effort="medium",
        max_subagents=0 if level is TaskLevel.L0 else 1,
        allow_sol=False,
        allow_astra=False,
        allow_max_or_ultra=False,
        pause=False,
        reason="Quota is unavailable; use a conservative GPT-6 Sol route and no premium escalation.",
    )


def launch_level(value: str) -> TaskLevel:
    return {
        "routine": TaskLevel.L1,
        "complex": TaskLevel.L2,
        "critical": TaskLevel.L3,
    }[value]
