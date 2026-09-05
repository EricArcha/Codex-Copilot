# Codex-Copilot repository guidance

## Purpose

This repository is the source of truth for the Codex-Copilot skill, custom agents, and installer. User-level installations are derived artifacts.

## Development rules

- Support Python 3.11+ on macOS and Linux using only the standard library.
- Never overwrite unknown user files or replace an entire Codex configuration.
- Keep prompts, source code, paths, command output, and secrets out of metrics.
- Keep the main skill concise; conditional detail belongs in `references/`.
- Preserve one writer by default. Parallel work should be read-heavy and bounded.

## Verification

Run before considering a change complete:

```bash
python3 -m unittest discover -s tests -v
python3 ${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py skill/codex-copilot
```

