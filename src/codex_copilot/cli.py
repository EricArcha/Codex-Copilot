from __future__ import annotations

import argparse
import builtins
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from . import VERSION
from .config_edit import parse_toml
from .delegation import DelegationDenied, complete as complete_delegation, dispatch as dispatch_delegation, trace
from .installer import (
    AGENT_FILES,
    SYMLINK_RISK_WARNING,
    InstallError,
    artifact_matches,
    install,
    load_manifest,
    uninstall,
)
from .metrics import project_hash, record, summarize
from .paths import bin_dir, codex_home, skills_home
from .profile import active_profile, set_profile
from .quota import QuotaSnapshot, get_quota
from .routing import Profile, QuotaBand, TaskLevel, launch_level, route_for


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-copilot", description="Quota-aware Codex orchestration")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    install_parser = sub.add_parser("install", help="Install the skill, agents, CLI, and managed config")
    install_parser.add_argument("--mode", choices=("symlink", "copy"), default="copy")
    install_parser.add_argument("--dry-run", action="store_true")
    install_parser.add_argument("--yes", action="store_true", help="Confirm the displayed installation plan")

    uninstall_parser = sub.add_parser("uninstall", help="Remove managed installation artifacts")
    uninstall_parser.add_argument("--dry-run", action="store_true")

    doctor_parser = sub.add_parser("doctor", help="Check installation and quota integration")
    doctor_parser.add_argument("--json", action="store_true")

    status_parser = sub.add_parser("status", help="Read current ChatGPT rate-limit windows")
    status_parser.add_argument("--json", action="store_true")
    status_parser.add_argument("--refresh", action="store_true")

    launch_parser = sub.add_parser("launch", help="Start Codex after quota-aware model selection")
    launch_parser.add_argument("--level", choices=("routine", "complex", "critical"), default="routine")
    launch_parser.add_argument("--dry-run", action="store_true")
    launch_parser.add_argument("--override-quota", action="store_true")
    launch_parser.add_argument("--profile", choices=tuple(profile.value for profile in Profile))
    launch_parser.add_argument("codex_args", nargs=argparse.REMAINDER)

    metrics_parser = sub.add_parser("metrics", help="Summarize local privacy-preserving route metrics")
    metrics_parser.add_argument("--days", type=int, default=30)
    metrics_parser.add_argument("--json", action="store_true")

    trace_parser = sub.add_parser("trace", help="Show the retained declared subagent trace")
    trace_parser.add_argument("--run")
    trace_parser.add_argument("--json", action="store_true")

    profile_parser = sub.add_parser("profile", help="Show or select a Codex-Copilot routing profile")
    profile_parser.add_argument("action", choices=("list", "show", "set"))
    profile_parser.add_argument("profile", nargs="?", choices=tuple(profile.value for profile in Profile))

    hidden = sub.add_parser("_record", help=argparse.SUPPRESS)
    hidden.add_argument("--event", required=True)
    hidden.add_argument("--run-id")
    hidden.add_argument("--surface", default="skill")
    hidden.add_argument("--project")
    hidden.add_argument("--task-level")
    hidden.add_argument("--quota-band")
    hidden.add_argument("--primary-used-percent", type=float)
    hidden.add_argument("--secondary-used-percent", type=float)
    hidden.add_argument("--primary-delta-observed", type=float)
    hidden.add_argument("--secondary-delta-observed", type=float)
    hidden.add_argument("--root-model")
    hidden.add_argument("--root-effort")
    hidden.add_argument("--subagent-count", type=int)
    hidden.add_argument("--outcome")
    hidden.add_argument("--elapsed-seconds", type=float)
    hidden.add_argument("--error-category")

    delegate = sub.add_parser("_delegate", help=argparse.SUPPRESS)
    delegate.add_argument("action", choices=("dispatch", "complete"))
    delegate.add_argument("--run-id", required=True)
    delegate.add_argument("--task-level", choices=tuple(level.value for level in TaskLevel))
    delegate.add_argument("--role")
    delegate.add_argument("--phase")
    delegate.add_argument("--ordinal", type=int)
    delegate.add_argument("--outcome")
    delegate.add_argument("--override", action="store_true")
    delegate.add_argument("--astra-unavailable", action="store_true")
    delegate.add_argument("--profile", choices=tuple(profile.value for profile in Profile))
    delegate.add_argument("--read-only", action="store_true")
    return parser


def _print_result(result: dict[str, Any]) -> None:
    for action in result.get("actions", []):
        print(action)
    for warning in result.get("warnings", []):
        print(f"warning: {warning}", file=sys.stderr)
    if result.get("dry_run"):
        print("Dry run: no changes made.")
    elif result.get("changed"):
        print("Done.")


def _config_value(change: dict[str, Any], key: str) -> str:
    if key == "previous_value" and not change["previous_present"]:
        return "<unset>"
    return json.dumps(change[key])


def _print_install_plan(result: dict[str, Any]) -> None:
    print("Installation plan:")
    for action in result.get("actions", []):
        print(f"  {action}")
    changes = result.get("config_changes", [])
    if changes:
        print(f"Managed settings in {result['config_path']}:")
        for change in changes:
            previous = _config_value(change, "previous_value")
            installed = _config_value(change, "installed_value")
            suffix = " (unchanged)" if previous == installed else ""
            print(f"  {change['path']}: {previous} -> {installed}{suffix}")
    print(f"Configuration backup directory: {result['config_backup_dir']}")
    for warning in result.get("warnings", []):
        print(f"warning: {warning}", file=sys.stderr)


def _confirm_install() -> bool:
    if not sys.stdin.isatty():
        print("error: refusing non-interactive installation without --yes", file=sys.stderr)
        return False
    try:
        return builtins.input("Proceed with this installation? [y/N] ").strip().lower() in {"y", "yes"}
    except EOFError:
        return False


def _format_reset(timestamp: int | None) -> str:
    if timestamp is None:
        return "unknown"
    return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="minutes")


def _status_text(snapshot: QuotaSnapshot) -> str:
    lines = [f"Quota band: {snapshot.band}"]
    lines.append(f"Quota source: {snapshot.source}")
    if snapshot.effective_remaining_percent is not None:
        lines.append(f"Effective remaining: {snapshot.effective_remaining_percent:g}%")
    for label, window in (("Primary", snapshot.primary), ("Secondary", snapshot.secondary)):
        if window:
            lines.append(
                f"{label}: {window.remaining_percent:g}% remaining; resets {_format_reset(window.resets_at)}"
            )
    if snapshot.plan_type:
        lines.append(f"Plan: {snapshot.plan_type}")
    if snapshot.reset_credits_available:
        lines.append(f"Available reset credits: {snapshot.reset_credits_available} (never redeemed automatically)")
    if snapshot.error:
        lines.append(f"Quota unavailable: {snapshot.error}")
    return "\n".join(lines)


def _version_tuple(text: str) -> tuple[int, ...] | None:
    for token in text.split():
        if token[0:1].isdigit():
            try:
                return tuple(int(part) for part in token.split(".")[:3])
            except ValueError:
                continue
    return None


def doctor() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str, severity: str = "ok") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail, "severity": severity})

    if os.name == "nt":
        add("platform", False, "Windows is not supported in v0.1")
    else:
        add("platform", True, sys.platform)

    codex = shutil.which("codex")
    if not codex:
        add("codex", False, "codex executable not found")
    else:
        completed = subprocess.run([codex, "--version"], capture_output=True, text=True, timeout=5)
        version_text = (completed.stdout or completed.stderr).strip()
        version = _version_tuple(version_text)
        add("codex", bool(version and version >= (0, 147, 0)), version_text)

        login = subprocess.run([codex, "login", "status"], capture_output=True, text=True, timeout=30)
        login_text = (login.stdout or login.stderr).strip()
        add("chatgpt_login", login.returncode == 0 and "ChatGPT" in login_text, login_text)

    config_path = codex_home() / "config.toml"
    try:
        parse_toml(config_path.read_text() if config_path.exists() else "")
        add("config", True, str(config_path))
    except (OSError, ValueError) as exc:
        add("config", False, str(exc))

    manifest = load_manifest()
    add("manifest", manifest is not None, str(manifest and manifest.get("version") or "not installed"))
    if manifest:
        mismatches = []
        for artifact in manifest.get("artifacts", []):
            if not artifact_matches(artifact):
                mismatches.append(str(artifact["target"]))
        add(
            "installation_integrity",
            not mismatches,
            "all recorded links/copies match" if not mismatches else f"mismatch: {', '.join(mismatches)}",
        )
    skill = skills_home() / "codex-copilot" / "SKILL.md"
    add("skill", skill.exists(), str(skill))
    symlinked_agents = []
    for name in AGENT_FILES:
        target = codex_home() / "agents" / name
        if target.is_symlink():
            symlinked_agents.append(str(target))
            detail = f"{target} (symlink)"
        elif target.exists():
            detail = f"{target} (regular file)"
        else:
            detail = str(target)
        add(name, target.exists(), detail)
    warnings = []
    if symlinked_agents:
        warnings.append(
            f"{SYMLINK_RISK_WARNING}. Detected: {', '.join(symlinked_agents)}"
        )
    executable = bin_dir() / "codex-copilot"
    add("launcher", executable.exists(), str(executable))
    path_entries = {str(Path(item).expanduser()) for item in os.environ.get("PATH", "").split(os.pathsep)}
    add("path", str(bin_dir()) in path_entries, f"{bin_dir()} in PATH")
    quota = get_quota(refresh=True)
    profile = active_profile()
    add("profile", True, profile.value)
    astra_agent = codex_home() / "agents" / "copilot-astra-final-reviewer.toml"
    add(
        "astra_profile",
        astra_agent.exists(),
        "configuration installed; account entitlement is checked when premium is launched"
        if astra_agent.exists() else "premium profile unavailable: Astra agent is not installed",
        severity="ok" if astra_agent.exists() else "warning",
    )
    quota_detail = quota.error or _status_text(quota).splitlines()[0]
    if quota.band == QuotaBand.UNKNOWN.value:
        warnings.append(f"Quota check unavailable: {quota_detail}")
        add("quota", True, quota_detail, severity="warning")
    else:
        add("quota", True, quota_detail)
    if manifest and not skill.exists():
        warnings.append(
            "Codex-Copilot installation residue detected: the Skill is missing, but managed settings may remain. "
            "Run 'codex-copilot uninstall' to remove managed artifacts and restore eligible settings."
        )
    return {"ok": all(check["ok"] for check in checks), "checks": checks, "warnings": warnings}


def _human_doctor(result: dict[str, Any]) -> None:
    for check in result["checks"]:
        marker = "WARNING" if check.get("severity") == "warning" else "OK" if check["ok"] else "FAIL"
        print(f"[{marker}] {check['name']}: {check['detail']}")
    for warning in result.get("warnings", []):
        print(f"warning: {warning}", file=sys.stderr)


def _human_trace(result: dict[str, Any]) -> None:
    if not result["found"]:
        print(result["message"])
        return
    print(f"Run: {result['run_id']}")
    print(
        "Policy: "
        f"{result['task_level']}; profile {result.get('profile', 'balanced')}; effective quota band {result['effective_quota_band']}; "
        f"{result['dispatched']} dispatched; {result['compliance']}"
    )
    print("Configuration: declared (not backend billing telemetry)")
    for agent in result["agents"]:
        suffix = "; USER-APPROVED OVERRIDE" if agent["override"] else ""
        print(
            f"#{agent['ordinal']} {agent['role']} | {agent['model']} {agent['effort']} | "
            f"{agent['phase']} | {agent['status']}{suffix}"
        )


def _launch(args: argparse.Namespace) -> int:
    snapshot = get_quota(refresh=True)
    level = launch_level(args.level)
    profile = Profile(args.profile) if args.profile else active_profile()
    if args.profile:
        set_profile(profile)
    if profile is Profile.PREMIUM and not (codex_home() / "agents" / "copilot-astra-final-reviewer.toml").exists():
        print("Premium profile unavailable: install the Astra reviewer or switch to balanced.", file=sys.stderr)
        return 2
    route = route_for(QuotaBand(snapshot.band), level, profile)
    if route.pause and not args.override_quota:
        print(_status_text(snapshot), file=sys.stderr)
        print(f"Launch paused: {route.reason}", file=sys.stderr)
        print("Re-run after reset, or pass --override-quota to make the exception explicit.", file=sys.stderr)
        return 2
    model = route.root_model
    effort = route.root_effort
    if route.pause and args.override_quota and level.value in {"L2", "L3"}:
        model, effort = "gpt-6-sol", "medium"
    extra = list(args.codex_args)
    if extra and extra[0] == "--":
        extra = extra[1:]
    command = ["codex", "--model", model, "-c", f'model_reasoning_effort="{effort}"', *extra]
    record(
        {
            "event": "launch",
            "surface": "cli",
            "project_hash": project_hash(os.getcwd()),
            "task_level": level.value,
            "quota_band": snapshot.band,
            "primary_used_percent": snapshot.primary.used_percent if snapshot.primary else None,
            "secondary_used_percent": snapshot.secondary.used_percent if snapshot.secondary else None,
            "root_model": model,
            "root_effort": effort,
            "profile": profile.value,
            "subagent_count": 0,
            "outcome": "planned",
        }
    )
    if args.dry_run:
        print(json.dumps({"command": command, "quota": snapshot.to_dict(), "route": route.to_dict()}, indent=2))
        return 0
    os.execvp(command[0], command)
    return 127


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "install":
            preview = install(mode=args.mode, dry_run=True)
            _print_install_plan(preview)
            if args.dry_run:
                print("Dry run: no changes made.")
                return 0
            if not preview.get("needs_confirmation"):
                return 0
            if not args.yes and not _confirm_install():
                print("Installation cancelled. No changes made.", file=sys.stderr)
                return 2
            _print_result(install(mode=args.mode, expected_plan_token=preview["plan_token"]))
            return 0
        if args.command == "uninstall":
            _print_result(uninstall(dry_run=args.dry_run))
            return 0
        if args.command == "status":
            snapshot = get_quota(refresh=args.refresh)
            print(json.dumps(snapshot.to_dict(), indent=2) if args.json else _status_text(snapshot))
            return 0 if snapshot.band != QuotaBand.UNKNOWN.value else 1
        if args.command == "profile":
            if args.action == "set":
                if not args.profile:
                    raise ValueError("profile set requires conservative, balanced, or premium")
                set_profile(Profile(args.profile))
            if args.action == "list":
                print("conservative\nbalanced\npremium")
            else:
                print(active_profile().value)
            return 0
        if args.command == "doctor":
            result = doctor()
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                _human_doctor(result)
            return 0 if result["ok"] else 1
        if args.command == "launch":
            return _launch(args)
        if args.command == "metrics":
            result = summarize(args.days)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Records ({args.days} days): {result['records']}")
                for route, count in sorted(result["routes"].items()):
                    print(f"  {route}: {count}")
                print(result["note"])
            return 0
        if args.command == "trace":
            result = trace(args.run)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                _human_trace(result)
            return 0 if result["found"] else 1
        if args.command == "_record":
            event = {
                "event": args.event,
                "run_id": args.run_id,
                "surface": args.surface,
                "project_hash": project_hash(args.project),
                "task_level": args.task_level,
                "quota_band": args.quota_band,
                "primary_used_percent": args.primary_used_percent,
                "secondary_used_percent": args.secondary_used_percent,
                "primary_delta_observed": args.primary_delta_observed,
                "secondary_delta_observed": args.secondary_delta_observed,
                "root_model": args.root_model,
                "root_effort": args.root_effort,
                "subagent_count": args.subagent_count,
                "outcome": args.outcome,
                "elapsed_seconds": args.elapsed_seconds,
                "error_category": args.error_category,
            }
            record(event)
            return 0
        if args.command == "_delegate":
            if args.action == "dispatch":
                if not args.task_level or not args.role or not args.phase:
                    raise DelegationDenied("dispatch requires --task-level, --role, and --phase")
                event = dispatch_delegation(
                    run_id=args.run_id,
                    level=TaskLevel(args.task_level),
                    role=args.role,
                    phase=args.phase,
                    override=args.override,
                    astra_unavailable=args.astra_unavailable,
                    profile=Profile(args.profile) if args.profile else None,
                    read_only=args.read_only,
                )
            else:
                if args.ordinal is None or not args.outcome:
                    raise DelegationDenied("complete requires --ordinal and --outcome")
                event = complete_delegation(run_id=args.run_id, ordinal=args.ordinal, outcome=args.outcome)
            print(json.dumps(event, indent=2))
            return 0
    except (InstallError, DelegationDenied, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1
