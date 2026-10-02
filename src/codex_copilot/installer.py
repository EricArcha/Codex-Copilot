from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import VERSION
from .config_edit import MISSING, apply_updates, get_path, parse_toml, restore_updates
from .paths import bin_dir, codex_home, repo_root, share_dir, skill_locations, skills_home, state_dir
from .known_skills import KNOWN_DISTRIBUTION_DIGESTS, KNOWN_SKILL_DIGESTS
from . import user_path


CONFIG_UPDATES: dict[str, Any] = {
    "service_tier": "standard",
    "features.multi_agent": True,
    "agents.max_concurrent_threads_per_session": 3,
    "agents.default_subagent_model": "gpt-6-luna",
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
MEASUREMENT_NOTICE = (
    "Optional allowance measurement is off by default. Run 'codex-copilot measure on' "
    "once for future skill tasks; 'codex-copilot measure off' stops new automatic measurements."
)
IGNORED_FINGERPRINT_FILENAMES = {".DS_Store"}


class InstallError(RuntimeError):
    pass


def manifest_path() -> Path:
    return state_dir() / "install.json"


def load_manifest() -> dict[str, Any] | None:
    path = manifest_path()
    if not path.exists():
        return None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema") not in (1, 2):
        raise InstallError("Invalid installation manifest; preserve the state directory for recovery")
    valid = isinstance(manifest.get("config_path"), str) and bool(manifest["config_path"])
    valid = valid and isinstance(manifest.get("version"), str) and isinstance(manifest.get("mode"), str) and manifest["mode"] in {"copy", "symlink"}
    valid = valid and isinstance(manifest.get("artifacts"), list) and isinstance(manifest.get("config_changes"), list)
    if valid:
        valid = all(isinstance(a, dict) and isinstance(a.get("target"), str) and bool(a["target"])
                    and isinstance(a.get("fingerprint"), str) and isinstance(a.get("kind"), str)
                    and (not a.get("previous_backup") or isinstance(a["previous_backup"], str)) for a in manifest["artifacts"])
        valid = valid and all(isinstance(c, dict) and isinstance(c.get("path"), str)
                              and isinstance(c.get("previous_present"), bool) and "previous_value" in c and "installed_value" in c
                              for c in manifest["config_changes"])
    path = manifest.get("user_path")
    if path is not None:
        valid = valid and isinstance(path, dict) and isinstance(path.get("entry"), str) and isinstance(path.get("added"), bool)
    if not valid:
        raise InstallError("Invalid installation manifest fields; preserve the state directory for recovery")
    return manifest


def _atomic_write(path: Path, content: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(content, encoding="utf-8")
    if mode is not None and os.name != "nt":
        temporary.chmod(mode)
    elif path.exists() and os.name != "nt":
        temporary.chmod(stat.S_IMODE(path.stat().st_mode))
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


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


def _fingerprint_files(root: Path, *, include_cache: bool = False) -> list[Path]:
    return sorted(
        item
        for item in root.rglob("*")
        if item.is_file() and item.name not in IGNORED_FINGERPRINT_FILENAMES
        and (include_cache or item.suffix not in {".pyc", ".pyo"})
    )


def artifact_fingerprint_for(item: dict[str, Any]) -> str:
    """Fingerprint an installed artifact using the algorithm recorded for its kind."""
    target = Path(item["target"])
    if item.get("kind") == "distribution":
        return _distribution_fingerprint(target)
    return artifact_fingerprint(target)


def artifact_matches(item: dict[str, Any]) -> bool:
    if item.get("kind") == "distribution":
        target = Path(item["target"])
        if target.exists() and any(p.name not in {"src", "skill", "agents", "bin", "VERSION", ".DS_Store"} for p in target.iterdir()):
            return False
    if artifact_fingerprint_for(item) == item.get("fingerprint"):
        return True
    if item.get("kind") == "distribution" and item.get("fingerprint_schema", 1) == 1:
        target = Path(item["target"])
        # v0.1.0 copied/fingerprinted bytecode. Verify its actual algorithm first;
        # a known release digest also permits regenerated caches to migrate safely.
        legacy = hashlib.sha256()
        portable = hashlib.sha256()
        for name in ("src", "skill", "agents", "bin", "VERSION"):
            path = target / name
            if path.is_file():
                legacy.update(name.encode())
                legacy.update(path.read_bytes())
            else:
                for child in _fingerprint_files(path, include_cache=True):
                    legacy.update(str(child.relative_to(target)).encode())
                    legacy.update(child.read_bytes())
        for child in sorted(p for name in ("src", "skill", "agents", "bin", "VERSION") for p in ([target / name] if (target / name).is_file() else _fingerprint_files(target / name))):
            portable.update(child.relative_to(target).as_posix().encode())
            portable.update(child.read_bytes().replace(b"\r\n", b"\n"))
        return legacy.hexdigest() == item.get("fingerprint") or portable.hexdigest() in KNOWN_DISTRIBUTION_DIGESTS
    return False


def _skill_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for child in _fingerprint_files(root):
        digest.update(child.relative_to(root).as_posix().encode())
        digest.update(child.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def _launcher_names() -> tuple[str, ...]:
    return ("codex-copilot", "codex-copilot.py", "codex-copilot.cmd") if os.name == "nt" else ("codex-copilot",)


def _planned() -> list[tuple[Path, Path, str]]:
    root = repo_root()
    return [
        (root / "skill" / "codex-copilot", skills_home() / "codex-copilot", "skill"),
        *[(root / "agents" / name, codex_home() / "agents" / name, "agent") for name in AGENT_FILES],
        *[(root / "bin" / name, bin_dir() / name, "executable") for name in _launcher_names()],
    ]


def _is_current_install(manifest: dict[str, Any] | None, mode: str, config: dict[str, Any]) -> bool:
    if not manifest or manifest.get("status") == "uninstall-residue" or manifest.get("mode") != mode or manifest.get("version") != VERSION:
        return False
    if any(get_path(config, path, MISSING) != value for path, value in CONFIG_UPDATES.items()):
        return False
    artifacts = manifest.get("artifacts", [])
    if not artifacts or any(not artifact_matches(item) for item in artifacts):
        return False
    targets = {item.get("target") for item in artifacts}
    expected = {str(target) for _, target, _ in _planned()} | {str(bin_dir() / "codex-copilot.runtime.json")}
    if not expected.issubset(targets):
        return False
    if mode == "copy":
        distribution = next((item for item in artifacts if item.get("kind") == "distribution"), None)
        if not distribution or str(share_dir()) != distribution["target"]:
            return False
        if _distribution_fingerprint(repo_root()) != distribution.get("fingerprint"):
            return False
    return True


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def _copy(source: Path, target: Path) -> None:
    if source.is_symlink():
        target.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True, ignore=shutil.ignore_patterns("*.pyc", "*.pyo"))
    else:
        shutil.copy2(source, target)


class _Transaction:
    """Keep recoverable originals and stage replacements on each target filesystem."""
    def __init__(self) -> None:
        self.root = state_dir() / "backups" / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.originals: dict[Path, Path | None] = {}
        self.parents: list[Path] = []
        self.staged: list[Path] = []

    def backup(self, target: Path) -> Path | None:
        if target in self.originals:
            return self.originals[target]
        previous = None
        if target.exists() or target.is_symlink():
            previous = self.root / str(len(self.originals))
            _copy(target, previous)
        self.originals[target] = previous
        _atomic_write(self.root / "recovery.json", json.dumps({str(k): str(v) if v else None for k, v in self.originals.items()}, indent=2))
        return previous

    def parent(self, target: Path) -> None:
        missing = []
        parent = target.parent
        while not parent.exists():
            missing.append(parent)
            parent = parent.parent
        target.parent.mkdir(parents=True, exist_ok=True)
        self.parents.extend(reversed(missing))

    def replace(self, source: Path, target: Path, mode: str = "copy") -> Path | None:
        previous = self.backup(target)
        self.parent(target)
        staged = target.with_name(f".{target.name}.{uuid.uuid4().hex}.stage")
        self.staged.append(staged)
        if mode == "symlink":
            staged.symlink_to(source.resolve(), target_is_directory=source.is_dir())
        else:
            _copy(source, staged)
        _remove(target)
        os.replace(staged, target)
        return previous

    def text(self, target: Path, content: str, mode: int | None = None) -> None:
        self.backup(target)
        self.parent(target)
        _atomic_write(target, content, mode)

    def remove(self, target: Path) -> None:
        self.backup(target)
        _remove(target)

    def rollback(self) -> None:
        failures = []
        for target, previous in reversed(list(self.originals.items())):
            try:
                _remove(target)
                if previous:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    _copy(previous, target)
            except OSError:
                failures.append(str(target))
        for staged in self.staged:
            try:
                _remove(staged)
            except OSError:
                failures.append(str(staged))
        for parent in reversed(self.parents):
            try:
                parent.rmdir()
            except OSError:
                pass
        if failures:
            raise InstallError(f"Rollback incomplete; preserve {self.root} and recover: {', '.join(failures)}")


def _rollback(transaction: _Transaction, path_written: bool, before, after) -> None:
    failures = []
    if path_written:
        try:
            if user_path.read() == after:
                user_path.write(before)
            else:
                failures.append("user PATH changed concurrently; preserved current value")
        except Exception as exc:
            failures.append(f"user PATH restoration: {exc}")
    try:
        transaction.rollback()
    except Exception as exc:
        failures.append(str(exc))
    if failures:
        raise InstallError(f"Rollback incomplete; preserve {transaction.root}. " + "; ".join(failures))


def _preflight(target: Path, source: Path | None, kind: str, managed: dict[str, dict[str, Any]]) -> bool:
    if not target.exists() and not target.is_symlink():
        return False
    item = managed.get(str(target))
    if item:
        if not artifact_matches(item):
            raise InstallError(f"Refusing to overwrite modified managed path: {target}. Back up and resolve the conflict first.")
        return False
    if kind == "skill" and source:
        digest = _skill_digest(target)
        if digest in KNOWN_SKILL_DIGESTS or digest == _skill_digest(source):
            return True
    if source and target.is_symlink() and target.resolve() == source.resolve():
        return True
    raise InstallError(f"Refusing to overwrite unmanaged path: {target}")


def _plan_token(config: str, current: dict[str, Any] | None, planned: list[tuple[Path | None, Path, str]], actions: list[str], path_before: dict[str, Any] | None) -> str:
    digest = hashlib.sha256()
    digest.update(config.encode())
    digest.update(json.dumps([current, actions, path_before], sort_keys=True).encode())
    for source, target, kind in planned:
        if source:
            fingerprint = _distribution_fingerprint(source) if kind == "distribution" else artifact_fingerprint(source)
            digest.update(f"{kind}:{source}:{fingerprint}".encode())
        digest.update(f"{kind}:{target}:{artifact_fingerprint(target)}".encode())
    return digest.hexdigest()


def install(*, mode: str = "copy", dry_run: bool = False, expected_plan_token: str | None = None, add_to_path: bool = False) -> dict[str, Any]:
    if mode not in {"copy", "symlink"}:
        raise InstallError(f"Unsupported install mode: {mode}")
    if add_to_path and os.name != "nt":
        raise InstallError("--add-to-path manages Windows user PATH only; configure your shell PATH on macOS/Linux")
    current = load_manifest()
    if current and current.get("status") == "uninstall-residue":
        raise InstallError("Previous uninstall preserved modified files. Resolve them and run uninstall again before installing.")
    planned = _planned()
    config_path = codex_home() / "config.toml"
    if current and Path(current["config_path"]).resolve() != config_path.resolve():
        raise InstallError("Uninstall before changing CODEX_HOME for an existing managed installation")
    old_skill = next((a for a in (current or {}).get("artifacts", []) if a["kind"] == "skill"), None)
    if old_skill and Path(old_skill["target"]).absolute() != (skills_home() / "codex-copilot").absolute():
        raise InstallError("Uninstall and resolve the existing Skill registration before changing SKILLS_HOME")
    previous_path = (current or {}).get("user_path")
    if previous_path and previous_path.get("added") and user_path.normalize(previous_path["entry"]) != user_path.normalize(str(bin_dir().resolve())):
        raise InstallError("Uninstall before changing BIN_DIR for a PATH-managed installation; this preserves PATH ownership")
    config_text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    config = parse_toml(config_text)
    updated, changes = apply_updates(config_text, CONFIG_UPDATES)
    current_install = _is_current_install(current, mode, config)
    if mode == "copy" and not current_install:
        root, destination = repo_root().resolve(), share_dir().resolve()
        if root == destination or root.is_relative_to(destination) or destination.is_relative_to(root):
            raise InstallError("Copy-mode upgrades must run from a source checkout outside the installed copy")
    managed = {item["target"]: item for item in (current or {}).get("artifacts", [])}
    duplicates = [p for p in skill_locations() if p != skills_home() / "codex-copilot" and (p.exists() or p.is_symlink())]
    if duplicates:
        raise InstallError("Duplicate Skill registrations detected; back up and resolve them first: " + ", ".join(map(str, duplicates)))
    pointer = bin_dir() / "codex-copilot.runtime.json"
    preflight = [*planned, (None, pointer, "runtime")]
    if mode == "copy":
        preflight.append((repo_root(), share_dir(), "distribution"))
    # Ensure a copied distribution cannot swallow another managed/user location.
    targets = [target.absolute() for _, target, _ in preflight]
    for index, target in enumerate(targets):
        if any(target == other or target.is_relative_to(other) or other.is_relative_to(target) for other in targets[index + 1:]):
            raise InstallError("Installation target directories overlap; choose separate skill, runtime, bin and state directories")
        if state_dir().absolute() == target or state_dir().absolute().is_relative_to(target):
            raise InstallError("State directory must be outside managed artifacts")
    adopted = {str(target) for source, target, kind in preflight if _preflight(target, source, kind, managed)}
    for item in (current or {}).get("artifacts", []):
        target = Path(item["target"])
        if (target.exists() or target.is_symlink()) and not artifact_matches(item):
            raise InstallError(f"Refusing upgrade with modified managed path: {target}")
    path_before = path_after = ownership = None
    if add_to_path:
        path_before, path_after, ownership = user_path.plan(bin_dir())
    actions = [f"{mode}: {source} -> {target}" for source, target, _ in planned]
    actions.extend([f"write runtime location: {pointer}", f"merge managed settings: {config_path}"])
    if mode == "copy":
        actions.insert(0, f"copy distribution: {repo_root()} -> {share_dir()}")
    actions.extend(f"back up and adopt verified Skill: {target}" for target in sorted(adopted))
    stale = [item for item in (current or {}).get("artifacts", []) if item["target"] not in {str(t) for _, t, _ in preflight}]
    actions.extend(f"remove obsolete copied distribution: {item['target']}" if item["kind"] == "distribution" else f"remove obsolete artifact: {item['target']}" for item in stale)
    if ownership and ownership["added"]:
        actions.append(f"append Windows user PATH: {ownership['entry']}")
    warnings = [RESTART_NOTICE, MEASUREMENT_NOTICE]
    if mode == "symlink":
        warnings.insert(0, SYMLINK_RISK_WARNING)
    if os.name == "nt":
        warnings.append(f"Launcher: {bin_dir() / 'codex-copilot.cmd'}. Open a new terminal after persistent PATH changes; default installation does not change PATH.")
    token = _plan_token(config_text, current, preflight, actions, path_before)
    if expected_plan_token is not None and expected_plan_token != token:
        raise InstallError("Installation plan changed; run 'codex-copilot install --dry-run' and review it again")
    no_changes = current_install and not (ownership and ownership["added"])
    result = {"changed": False, "dry_run": dry_run, "actions": ["Already installed; no changes."] if no_changes else actions,
              "warnings": warnings, "needs_confirmation": not no_changes, "config_changes": [] if no_changes else [asdict(c) for c in changes],
              "config_path": str(config_path), "config_backup_dir": str(state_dir() / "backups"), "plan_token": token}
    if dry_run or no_changes:
        return result
    transaction = _Transaction()
    path_written = False
    try:
        runtime_root = repo_root() if mode == "symlink" else share_dir()
        artifacts = []
        if mode == "copy":
            staged_distribution = transaction.root / "distribution"
            staged_distribution.mkdir()
            for name in ("src", "skill", "agents", "bin", "VERSION"):
                _copy(repo_root() / name, staged_distribution / name)
            transaction.replace(staged_distribution, runtime_root)
            artifacts.append({"kind": "distribution", "source": str(repo_root()), "target": str(runtime_root), "fingerprint": _distribution_fingerprint(runtime_root), "fingerprint_schema": 2})
        for source, target, kind in planned:
            actual_source = runtime_root / source.relative_to(repo_root())
            # Batch/Python entry points are always regular files, even in symlink mode.
            placement = "copy" if os.name == "nt" and kind == "executable" else mode
            previous = transaction.replace(actual_source, target, placement)
            if kind == "executable" and os.name != "nt" and not target.is_symlink():
                target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            item = {"kind": kind, "source": str(actual_source), "target": str(target), "fingerprint": artifact_fingerprint(target)}
            previous_backup = managed.get(str(target), {}).get("previous_backup")
            if previous_backup or str(target) in adopted:
                item["previous_backup"] = previous_backup or str(previous)
            artifacts.append(item)
        transaction.text(pointer, json.dumps({"root": str(runtime_root.resolve())}, indent=2) + "\n")
        artifacts.append({"kind": "runtime", "target": str(pointer), "fingerprint": artifact_fingerprint(pointer)})
        for item in stale:
            if item.get("previous_backup"):
                transaction.replace(Path(item["previous_backup"]), Path(item["target"]))
            else:
                transaction.remove(Path(item["target"]))
        transaction.text(config_path, updated)
        original_changes = (current or {}).get("config_changes", [])
        owned_paths = {change["path"] for change in original_changes}
        original_changes = [*original_changes, *[asdict(c) for c in changes if c.path not in owned_paths]]
        previous_path = (current or {}).get("user_path")
        if path_before != path_after:
            if user_path.read() != path_before:
                raise InstallError("User PATH changed after preview; review the installation again")
            path_written = True
            user_path.write(path_after)
        manifest = {"schema": 2, "version": VERSION, "mode": mode, "installed_at": int(time.time()), "repo_root": str(repo_root()),
                    "artifacts": artifacts, "config_path": str(config_path), "config_backup": str(transaction.originals.get(config_path)),
                    "config_changes": original_changes, "user_path": previous_path if previous_path and previous_path.get("added") else ownership,
                    "backup_dir": str(transaction.root)}
        transaction.text(manifest_path(), json.dumps(manifest, indent=2, sort_keys=True) + "\n", 0o600)
    except Exception as exc:
        _rollback(transaction, path_written, path_before, path_after)
        raise InstallError(f"Installation failed and was rolled back: {exc}. Backups: {transaction.root}") from exc
    return {**result, "changed": True, "needs_confirmation": False, "manifest": str(manifest_path())}


def uninstall(*, dry_run: bool = False) -> dict[str, Any]:
    manifest = load_manifest()
    if not manifest:
        return {"changed": False, "dry_run": dry_run, "actions": [], "warnings": ["Not installed"]}
    actions, warnings, removable, preserved = [], [], [], []
    for item in reversed(manifest.get("artifacts", [])):
        target = Path(item["target"])
        if not target.exists() and not target.is_symlink():
            continue
        if not artifact_matches(item):
            warnings.append(f"Preserved modified installed path: {target}")
            preserved.append(item)
            continue
        previous = item.get("previous_backup")
        if previous and not Path(previous).exists() and not Path(previous).is_symlink():
            raise InstallError(f"Original artifact backup missing; preserve installation and restore backup: {previous}")
        actions.append(f"restore original: {target}" if previous else f"remove: {target}")
        removable.append(item)
    config_path = Path(manifest["config_path"])
    config_text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    restored, config_warnings = restore_updates(config_text, manifest.get("config_changes", []))
    warnings.extend(config_warnings)
    actions.append(f"restore managed settings: {config_path}")
    path_before = path_after = None
    if os.name == "nt" and manifest.get("user_path"):
        path_before, path_after = user_path.removal(manifest["user_path"])
        if path_before != path_after:
            actions.append(f"remove owned user PATH entry: {manifest['user_path']['entry']}")
    result = {"changed": False, "dry_run": dry_run, "actions": actions, "warnings": warnings}
    if dry_run:
        return result
    transaction = _Transaction()
    path_written = False
    try:
        for item in removable:
            target = Path(item["target"])
            if item.get("previous_backup"):
                transaction.replace(Path(item["previous_backup"]), target)
            else:
                transaction.remove(target)
        transaction.text(config_path, restored)
        if path_before != path_after:
            if user_path.read() != path_before:
                raise InstallError("User PATH changed during uninstall; retry after reviewing it")
            path_written = True
            user_path.write(path_after)
        if preserved:
            residue = {**manifest, "status": "uninstall-residue", "artifacts": preserved, "config_changes": [], "user_path": None}
            transaction.text(manifest_path(), json.dumps(residue, indent=2, sort_keys=True) + "\n", 0o600)
            warnings.append("Recovery manifest retained for modified files; resolve them and rerun uninstall from a source checkout.")
        else:
            transaction.remove(manifest_path())
    except Exception as exc:
        _rollback(transaction, path_written, path_before, path_after)
        raise InstallError(f"Uninstall failed and was rolled back: {exc}. Backups: {transaction.root}") from exc
    return {**result, "changed": True}
