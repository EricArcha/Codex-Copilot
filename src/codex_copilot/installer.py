from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import VERSION
from .config_edit import MISSING, apply_updates, get_path, parse_toml, restore_updates
from .paths import bin_dir, codex_home, repo_root, share_dir, skills_home, state_dir


CONFIG_UPDATES: dict[str, Any] = {
    "service_tier": "standard",
    "features.multi_agent": True,
    "agents.max_concurrent_threads_per_session": 3,
    "agents.default_subagent_model": "gpt-5.6-luna",
    "agents.default_subagent_reasoning_effort": "low",
    "features.fast_mode": False,
}
AGENT_FILES = (
    "copilot-scout.toml",
    "copilot-investigator.toml",
    "copilot-worker.toml",
    "copilot-reviewer.toml",
    "copilot-final-reviewer.toml",
    "copilot-astra-final-reviewer.toml",
)
SYMLINK_RISK_WARNING = (
    "WARNING: Codex may reject symlinked custom-agent configuration files and report "
    "'agent type is currently not available'. Use regular copies when reliability matters: "
    "codex-copilot install --mode copy"
)
RESTART_NOTICE = "Restart Codex Desktop and open a new task before using the installed agents."
IGNORED_FINGERPRINT_FILENAMES = {".DS_Store"}


class InstallError(RuntimeError):
    pass


def manifest_path() -> Path:
    return state_dir() / "install.json"


def load_manifest() -> dict[str, Any] | None:
    path = manifest_path()
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _atomic_write(path: Path, content: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.codex-copilot.tmp")
    temporary.write_text(content)
    if mode is not None:
        temporary.chmod(mode)
    elif path.exists():
        temporary.chmod(stat.S_IMODE(path.stat().st_mode))
    os.replace(temporary, path)


def artifact_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_symlink():
        digest.update(f"link:{os.readlink(path)}".encode())
        return digest.hexdigest()
    if path.is_file():
        digest.update(path.read_bytes())
        return digest.hexdigest()
    if path.is_dir():
        for child in _fingerprint_files(path):
            digest.update(str(child.relative_to(path)).encode())
            digest.update(child.read_bytes())
        return digest.hexdigest()
    return "missing"


def _distribution_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for name in ("src", "skill", "agents", "bin", "VERSION"):
        path = root / name
        if path.is_file():
            digest.update(name.encode())
            digest.update(path.read_bytes())
            continue
        for child in _fingerprint_files(path):
            digest.update(str(child.relative_to(root)).encode())
            digest.update(child.read_bytes())
    return digest.hexdigest()


def _fingerprint_files(root: Path) -> list[Path]:
    return sorted(
        item
        for item in root.rglob("*")
        if item.is_file() and item.name not in IGNORED_FINGERPRINT_FILENAMES
    )


def artifact_fingerprint_for(item: dict[str, Any]) -> str:
    """Fingerprint an installed artifact using the algorithm recorded for its kind."""
    target = Path(item["target"])
    if item.get("kind") == "distribution":
        return _distribution_fingerprint(target)
    return artifact_fingerprint(target)


def artifact_matches(item: dict[str, Any]) -> bool:
    return artifact_fingerprint_for(item) == item.get("fingerprint")


def _is_current_install(manifest: dict[str, Any] | None, mode: str, config: dict[str, Any]) -> bool:
    if not manifest or manifest.get("mode") != mode or manifest.get("version") != VERSION:
        return False
    if any(get_path(config, path, MISSING) != value for path, value in CONFIG_UPDATES.items()):
        return False
    artifacts = manifest.get("artifacts", [])
    if not artifacts or any(not artifact_matches(item) for item in artifacts):
        return False
    expected_agent_targets = {str(codex_home() / "agents" / name) for name in AGENT_FILES}
    recorded_targets = {item.get("target") for item in artifacts}
    if not expected_agent_targets.issubset(recorded_targets):
        return False
    if mode == "copy":
        distribution = next((item for item in artifacts if item.get("kind") == "distribution"), None)
        if not distribution or _distribution_fingerprint(repo_root()) != distribution.get("fingerprint"):
            return False
    return True


def _managed_targets(manifest: dict[str, Any] | None) -> set[str]:
    return {item["target"] for item in (manifest or {}).get("artifacts", [])}


def _preflight_target(target: Path, source: Path, managed: set[str]) -> None:
    if not target.exists() and not target.is_symlink():
        return
    if str(target) in managed:
        return
    if target.is_symlink() and target.resolve() == source.resolve():
        return
    raise InstallError(f"Refusing to overwrite unmanaged path: {target}")


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def _place(source: Path, target: Path, mode: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    _remove(target)
    if mode == "symlink":
        target.symlink_to(source.resolve(), target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)


def _distribution_source(mode: str, dry_run: bool) -> tuple[Path, list[dict[str, str]]]:
    root = repo_root()
    artifacts: list[dict[str, str]] = []
    if mode == "symlink":
        return root, artifacts
    target = share_dir()
    if root.resolve() == target.resolve():
        raise InstallError("Copy-mode upgrades must be run from a source checkout, not the installed copy")
    artifacts.append({"source": str(root), "target": str(target), "kind": "distribution"})
    if not dry_run:
        _remove(target)
        target.mkdir(parents=True, exist_ok=True)
        for name in ("src", "skill", "agents", "bin"):
            shutil.copytree(root / name, target / name)
        shutil.copy2(root / "VERSION", target / "VERSION")
    return target, artifacts


def _remove_stale_distribution(
    manifest: dict[str, Any] | None, mode: str, actions: list[str], warnings: list[str]
) -> None:
    """Remove an unchanged copied distribution when changing back to symlink mode."""
    if mode != "symlink" or not manifest:
        return
    for artifact in manifest.get("artifacts", []):
        if artifact.get("kind") != "distribution":
            continue
        target = Path(artifact["target"])
        if not target.exists() and not target.is_symlink():
            continue
        if not artifact_matches(artifact):
            warnings.append(f"Preserved modified previous distribution: {target}")
            continue
        _remove(target)
        actions.append(f"remove obsolete copied distribution: {target}")


def install(*, mode: str = "copy", dry_run: bool = False) -> dict[str, Any]:
    if mode not in {"symlink", "copy"}:
        raise InstallError(f"Unsupported install mode: {mode}")
    if os.name == "nt":
        raise InstallError("Windows is not supported in Codex-Copilot v0.1")
    current = load_manifest()
    managed = _managed_targets(current)
    planned = [
        (repo_root() / "skill" / "codex-copilot", skills_home() / "codex-copilot", "skill"),
        *[
            (repo_root() / "agents" / name, codex_home() / "agents" / name, "agent")
            for name in AGENT_FILES
        ],
        (repo_root() / "bin" / "codex-copilot", bin_dir() / "codex-copilot", "executable"),
    ]
    for source, target, _ in planned:
        _preflight_target(target, source, managed)

    config_path = codex_home() / "config.toml"
    config_text = config_path.read_text() if config_path.exists() else ""
    parsed_config = parse_toml(config_text)
    updated_config, changes = apply_updates(config_text, CONFIG_UPDATES)
    actions = [f"{mode}: {source} -> {target}" for source, target, _ in planned]
    actions.append(f"merge managed settings: {config_path}")
    warnings = [RESTART_NOTICE]
    if mode == "symlink":
        warnings.insert(0, SYMLINK_RISK_WARNING)
    if dry_run:
        return {"changed": False, "dry_run": True, "actions": actions, "warnings": warnings}
    if _is_current_install(current, mode, parsed_config):
        return {
            "changed": False,
            "dry_run": False,
            "actions": ["Already installed; no changes."],
            "warnings": warnings,
        }

    _remove_stale_distribution(current, mode, actions, warnings)
    distribution_root, distribution_artifacts = _distribution_source(mode, dry_run=False)
    actual_planned = [
        (distribution_root / "skill" / "codex-copilot", skills_home() / "codex-copilot", "skill"),
        *[
            (distribution_root / "agents" / name, codex_home() / "agents" / name, "agent")
            for name in AGENT_FILES
        ],
        (distribution_root / "bin" / "codex-copilot", bin_dir() / "codex-copilot", "executable"),
    ]
    artifacts: list[dict[str, str]] = []
    if mode == "copy":
        for artifact in distribution_artifacts:
            artifacts.append({**artifact, "fingerprint": _distribution_fingerprint(Path(artifact["target"]))})
    for source, target, kind in actual_planned:
        _place(source, target, mode)
        if kind == "executable" and not target.is_symlink():
            target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        artifacts.append(
            {
                "source": str(source.resolve()),
                "target": str(target),
                "kind": kind,
                "fingerprint": artifact_fingerprint(target),
            }
        )

    state_dir().mkdir(parents=True, exist_ok=True)
    backup_path = state_dir() / "backups" / f"config.{int(time.time())}.toml"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(config_text)
    _atomic_write(config_path, updated_config)
    original_changes = (current or {}).get("config_changes") or [asdict(change) for change in changes]
    manifest = {
        "schema": 1,
        "version": VERSION,
        "mode": mode,
        "installed_at": int(time.time()),
        "repo_root": str(repo_root()),
        "artifacts": artifacts,
        "config_path": str(config_path),
        "config_backup": str(backup_path),
        "config_changes": original_changes,
    }
    _atomic_write(manifest_path(), json.dumps(manifest, indent=2, sort_keys=True) + "\n", 0o600)
    return {
        "changed": True,
        "dry_run": False,
        "actions": actions,
        "warnings": warnings,
        "manifest": str(manifest_path()),
    }


def uninstall(*, dry_run: bool = False) -> dict[str, Any]:
    manifest = load_manifest()
    if not manifest:
        return {"changed": False, "dry_run": dry_run, "actions": [], "warnings": ["Not installed"]}
    actions: list[str] = []
    warnings: list[str] = []
    removable: list[Path] = []
    for artifact in reversed(manifest.get("artifacts", [])):
        target = Path(artifact["target"])
        if not target.exists() and not target.is_symlink():
            continue
        if not artifact_matches(artifact):
            warnings.append(f"Preserved modified installed path: {target}")
            continue
        actions.append(f"remove: {target}")
        removable.append(target)

    config_path = Path(manifest["config_path"])
    config_text = config_path.read_text() if config_path.exists() else ""
    restored, config_warnings = restore_updates(config_text, manifest.get("config_changes", []))
    warnings.extend(config_warnings)
    actions.append(f"restore managed settings: {config_path}")
    if dry_run:
        return {"changed": False, "dry_run": True, "actions": actions, "warnings": warnings}

    # Remove children before the copied distribution directory.
    for target in removable:
        _remove(target)
    _atomic_write(config_path, restored)
    manifest_path().unlink(missing_ok=True)
    return {"changed": True, "dry_run": False, "actions": actions, "warnings": warnings}
