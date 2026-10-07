"""Bounded data-plane model turns; no caller-provided command/config overrides."""
from __future__ import annotations

import json
from dataclasses import replace
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, TextIO

from . import execution, process_tree
from .config_policy import require_dispatch_config
from .paths import state_dir
from .process import codex_command, run_codex
from .profile import active_profile
from .quota import cached_quota, unknown_snapshot
from .routing import TaskLevel

DISABLED_FEATURES = (
    "multi_agent", "multi_agent_v2", "apps", "plugins", "hooks", "shell_tool", "unified_exec",
    "code_mode", "code_mode_host", "browser_use", "browser_use_external", "computer_use",
    "image_generation", "view_image", "skill_search", "skill_mcp_dependency_install",
    "workspace_dependencies", "goals", "in_app_local_automation", "sleep_tool",
)
MODEL = "gpt-6.1-sol"
EFFORT = "medium"


class ModelCallError(execution.ExecutionDenied):
    def __init__(self, message: str, *, session_id: str | None, uncertain: bool = True):
        super().__init__(message)
        self.session_id = session_id
        self.uncertain = uncertain


class ModelInterrupted(KeyboardInterrupt):
    def __init__(self, session_id: str | None):
        super().__init__("Managed model interrupted; attempt remains uncertain and consumed")
        self.session_id = session_id


def reserve(*, run_id: str, request_id: str, category: str, grant_id: str | None = None,
            followup_id: str | None = None) -> dict[str, Any]:
    if category not in execution.CATEGORIES - {"subagent", "review"}:
        raise execution.ExecutionDenied("Data-plane calls cannot impersonate a subagent or independent review")
    require_dispatch_config()
    state = execution.status(run_id)
    level = state["task_level"] or TaskLevel.L2.value
    profile = state["profile"] or active_profile().value
    prior = next((c for c in state["calls"] if c["request_id"] == request_id), None)
    if prior:
        snapshot = replace(unknown_snapshot("Request replay"), band=prior["current_band"], source=prior["quota_source"])
    else:
        snapshot = cached_quota(ttl=60)
    if snapshot is None:
        raise execution.ExecutionDenied("Bulk model work needs a recent trusted quota snapshot; use the planned status checkpoint, never poll")
    return execution.reserve(run_id=run_id, request_id=request_id, kind="model", category=category,
                             phase="evaluation", snapshot=snapshot, role="data_model",
                             model=MODEL, effort=EFFORT, level=level, profile=profile,
                             grant_id=grant_id, followup_id=followup_id)


def _workspace() -> Path:
    path = state_dir() / "model-workspace"
    if path.is_symlink():
        raise execution.ExecutionDenied("Model workspace is an unexpected symlink")
    path.mkdir(parents=True, exist_ok=True)
    if any(path.iterdir()):
        raise execution.ExecutionDenied("Model workspace must remain empty")
    return path


def _check_features() -> None:
    result = run_codex(["features", "list"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                       text=True, encoding="utf-8", timeout=10)
    available = {line.split()[0] for line in result.stdout.splitlines() if line.split()}
    if result.returncode or not set(DISABLED_FEATURES + ("skip_host_skill_discovery",)) <= available:
        raise execution.ExecutionDenied("CLI lacks the managed model isolation features; upgrade before calling")


def _arguments(call: dict[str, Any], cwd: Path) -> list[str]:
    args = ["exec", "--ignore-user-config", "--enable", "skip_host_skill_discovery"]
    for feature in DISABLED_FEATURES:
        args.extend(["--disable", feature])
    args.extend(["-c", f'model_reasoning_effort="{EFFORT}"', "-c", 'web_search="disabled"',
                 "--model", MODEL, "--sandbox", "read-only", "--skip-git-repo-check", "--json",
                 "--color", "never", "--cd", str(cwd)])
    if call["followup_id"]:
        args.extend(["resume", call["session_id"], "-"])
    else:
        args.append("-")
    return args


def execute(*, run_id: str, request_id: str, category: str, prompt: str, output: TextIO,
            grant_id: str | None = None, followup_id: str | None = None,
            timeout: float = 120) -> dict[str, Any]:
    if not prompt.strip() or len(prompt.encode("utf-8")) > 4 * 1024 * 1024:
        raise execution.ExecutionDenied("Prompt must contain 1 to 4 MiB of UTF-8 input")
    if not execution._number(timeout, 1200) or timeout <= 0:
        raise execution.ExecutionDenied("Model timeout must be positive and at most 1200 seconds")
    call = reserve(run_id=run_id, request_id=request_id, category=category,
                   grant_id=grant_id, followup_id=followup_id)
    if call["replayed"]:
        # Results are owned by the caller. Never rerun a known request to recreate output.
        return dict(call, executed=False)
    if not execution.claim_model(run_id=run_id, request_id=request_id):
        return dict(call, executed=False)
    session = call["session_id"]
    outcome = "failure"
    entering_run = False
    try:
        _check_features()
        cwd = _workspace()
        entering_run = True
        session = _run(_arguments(call, cwd), prompt, output, timeout, expected_session=session)
        outcome = "success"
    except KeyboardInterrupt as exc:
        outcome = "unknown" if entering_run else "failure"
        if isinstance(exc, ModelInterrupted):
            session = exc.session_id or session
        raise
    except ModelCallError as exc:
        outcome = "unknown" if exc.uncertain else "failure"
        session = exc.session_id or session
        raise
    finally:
        finished = execution.complete(run_id=run_id, request_id=request_id, outcome=outcome, session_id=session)
    return dict(finished, executed=True)


def _run(args: list[str], prompt: str, output: TextIO, timeout: float,
         *, expected_session: str | None = None) -> str:
    proc, job = process_tree.start(codex_command(args), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="strict")
    assert proc.stdin is not None and proc.stdout is not None
    inbox: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=32)
    stopped = threading.Event()

    def deliver(kind: str, value: Any) -> None:
        while not stopped.is_set():
            try:
                inbox.put((kind, value), timeout=0.1)
                return
            except queue.Full:
                pass

    def feed() -> None:
        try:
            proc.stdin.write(prompt)
            proc.stdin.close()
        except (OSError, ValueError):
            deliver("error", None)

    def read() -> None:
        try:
            while not stopped.is_set():
                line = proc.stdout.readline(1024 * 1024 + 1)
                if not line:
                    break
                if len(line) > 1024 * 1024:
                    deliver("error", None)
                    return
                deliver("line", line)
            deliver("eof", None)
        except (OSError, ValueError):
            deliver("error", None)

    writer = threading.Thread(target=feed, daemon=True)
    reader = threading.Thread(target=read, daemon=True)
    writer.start()
    reader.start()
    deadline = time.monotonic() + timeout
    session = None
    completed = False
    explicit_failed = False
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise execution.ExecutionDenied("Managed model call timed out; attempt remains consumed")
            try:
                kind, value = inbox.get(timeout=remaining)
            except queue.Empty:
                raise execution.ExecutionDenied("Managed model call timed out; attempt remains consumed") from None
            if kind == "eof":
                break
            if kind == "error":
                raise execution.ExecutionDenied("Managed model stream failed; attempt remains consumed")
            try:
                event = json.loads(value)
            except (ValueError, TypeError):
                raise execution.ExecutionDenied("Managed model returned an invalid event") from None
            if not isinstance(event, dict):
                raise execution.ExecutionDenied("Managed model returned an invalid event")
            event_type = event.get("type")
            if event_type in {"error", "turn.failed"}:
                explicit_failed = event_type == "turn.failed"
                raise execution.ExecutionDenied("Managed model failed; attempt remains consumed")
            if event_type == "thread.started":
                found = execution.opaque_id(event.get("thread_id"))
                if (session and found != session) or (expected_session and found != expected_session):
                    raise execution.ExecutionDenied("Managed model returned a different session")
                session = found
            if event_type == "turn.completed":
                if completed:
                    raise execution.ExecutionDenied("Unexpected extra model turn")
                completed = True
            item = event.get("item", {})
            if not isinstance(item, dict) or (item and item.get("type") not in {"agent_message", "reasoning", "AgentMessage", "Reasoning"}):
                raise execution.ExecutionDenied("Unexpected tool activity in data-plane model call")
            # Forward successful model events to the caller; never put them in state/metrics.
            if event_type in {"thread.started", "turn.started", "turn.completed", "item.started", "item.completed", "item.updated"}:
                output.write(value)
                output.flush()
        try:
            code = proc.wait(timeout=max(0.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise execution.ExecutionDenied("Managed model exit timed out") from None
        if code or not completed or not session:
            raise execution.ExecutionDenied("Managed model execution incomplete")
        return session
    except KeyboardInterrupt:
        raise ModelInterrupted(session) from None
    except (execution.ExecutionDenied, OSError, ValueError) as exc:
        message = str(exc) if isinstance(exc, execution.ExecutionDenied) else "Managed model stream interrupted"
        raise ModelCallError(message, session_id=session, uncertain=not (completed or explicit_failed)) from None
    finally:
        stopped.set()
        try:
            try:
                process_tree.stop(proc, job)
            except (OSError, RuntimeError, subprocess.SubprocessError):
                raise ModelCallError("Managed model termination could not be confirmed", session_id=session) from None
        finally:
            writer.join(timeout=1)
            reader.join(timeout=1)
            try:
                proc.stdin.close()
            except (BrokenPipeError, ValueError):
                pass
            proc.stdout.close()
