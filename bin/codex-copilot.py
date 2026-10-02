#!/usr/bin/env python3
from pathlib import Path
import json
import sys


def _bootstrap() -> None:
    if sys.version_info < (3, 11):
        raise SystemExit("Codex-Copilot requires Python 3.11+")
    here = Path(__file__).resolve()
    pointer = Path(__file__).absolute().with_name("codex-copilot.runtime.json")
    if pointer.exists():
        try:
            runtime = Path(json.loads(pointer.read_text(encoding="utf-8"))["root"]) / "src"
            if not (runtime / "codex_copilot").is_dir():
                raise ValueError("missing runtime")
            sys.path.insert(0, str(runtime))
            return
        except (OSError, ValueError, KeyError, TypeError):
            raise SystemExit("Codex-Copilot runtime missing or invalid. Re-run the installer from a source checkout.")
    candidates = [
        here.parents[1] / "src",
        here.parents[1] / "share" / "codex-copilot" / "src",
    ]
    for candidate in candidates:
        if (candidate / "codex_copilot").is_dir():
            sys.path.insert(0, str(candidate))
            return
    raise SystemExit("Codex-Copilot runtime not found. Re-run the installer.")


_bootstrap()
from codex_copilot.cli import main  # noqa: E402

raise SystemExit(main())
