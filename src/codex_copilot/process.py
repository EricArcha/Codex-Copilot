"""Resolve Codex without depending on a particular Desktop or npm version path."""
from __future__ import annotations

import os
import shutil
import subprocess


def codex_command(args: list[str]) -> list[str]:
    executable = shutil.which("codex")
    if not executable:
        raise FileNotFoundError("codex executable not found in PATH")
    if os.name == "nt" and executable.lower().endswith((".cmd", ".bat")):
        # npm's wrapper contains a shell command, so prefer its adjacent JS entry.
        # Direct node invocation preserves argument boundaries and avoids cmd injection.
        from pathlib import Path
        entry = Path(executable).parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        node = shutil.which("node")
        if node and entry.is_file():
            return [node, str(entry), *args]
        raise OSError("Codex batch wrapper has no adjacent npm entry; install Codex CLI or expose codex.exe in PATH")
    return [executable, *args]


def run_codex(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(codex_command(args), **kwargs)
