# Codex-Copilot repository guidance

## Purpose

This repository is the source of truth for the Codex-Copilot skill, custom agents, and installer. User-level installations are derived artifacts.

## Development rules

- Support Python 3.11+ on macOS and Linux using only the standard library.
- Never overwrite unknown user files or replace an entire Codex configuration.
- Keep prompts, source code, paths, command output, and secrets out of metrics.
- Keep allowance measurement opt-in and off by default. Store its preference locally, preserve
  existing records when it is turned off, and do not add polling or per-turn quota reads.
- Treat allowance percentages as observations, not exact task costs or proven savings. Give users
  a concise notice when measurement is enabled or recording starts, without extra quota reads.
- Keep the main skill concise; conditional detail belongs in `references/`.
- Preserve one writer by default. Parallel work should be read-heavy and bounded.
- Treat delegation limits as a run-wide cumulative budget. Every child dispatch must pass the
  delegation gate; do not bypass it because an earlier child completed or quota later improved.
- Keep agent model/effort policy explicit and validated. A custom agent configuration must not
  silently widen its permitted model, reasoning effort, role, or phase.
- Record only canonical opaque UUID run IDs in local trace events. User-provided task content
  must never become a trace identifier.

## Verification

Run before considering a change complete:

```bash
python3 -m unittest discover -s tests -v
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skill/codex-copilot
```
