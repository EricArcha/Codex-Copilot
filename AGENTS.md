# Codex-Copilot repository guidance

## Purpose

This repository is the source of truth for the Codex-Copilot skill, custom agents, and installer. User-level installations are derived artifacts.

## Development rules

- Support Python 3.11+ on Windows, macOS and Linux using only the standard library.
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
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skill/codex-copilot
```

On Windows PowerShell, use `$env:PYTHONPATH = 'src'`, then `python -m unittest discover -s tests -v` and `python -X utf8 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" skill/codex-copilot` (respect `CODEX_HOME` when set). PyYAML is needed only by the external Skill validator. Probe symlink capability; skip only tests requiring unavailable privilege, never copy-mode or business failures. Perform installation experiments with all five path overrides in isolated directories and no persistent user PATH changes.

## Governance

Follow [CONTRIBUTING.md](CONTRIBUTING.md), [release policy](docs/releasing.md) and
[compatibility contract](docs/compatibility.md). `VERSION` is authoritative; run
`python3 scripts/check_release.py` before completion and with `--tag v<version>`
before release. Update CHANGELOG for user-facing changes. Permission, installation
/migration and delegation changes require L3 independent final review.

## Responsibility boundaries and change fences

- Product scope is Codex Desktop development orchestration: allowance-aware routing,
  bounded delegation, safe managed installation and privacy-safe measurement.
  Do not expand it into a general agent framework, billing service, credential
  manager, global sandbox configurator or telemetry collector.
- `skill/codex-copilot/SKILL.md` is the short workflow entry point; references contain
  conditional operator guidance. Instructions cannot grant host permissions or
  bypass runtime validation. Do not make every task load every reference.
- `src/` owns executable enforcement. Quota owns trusted acquisition/diagnostics,
  routing owns policy, delegation owns role policy and native dispatch authorization, execution owns durable
  call budgets, scoped grants and evidence-stage gates, model owns fixed data-plane
  invocation and at-most-once spawn claims,
  installer owns managed artifact transactions, metrics/measurement own opt-in
  privacy-safe observations. Diagnostics and measurements never authorize dispatch.
- Repository governance stays in AGENTS/CONTRIBUTING and docs, not in the runtime
  dependency graph. Only src, skill, agents, bin and VERSION enter the copied
  distribution; repository-root docs, scripts, tests, fixtures and user files
  outside those trees do not. Their contents are copied recursively: keep those
  trees product-only, and reject uncommitted/untracked product content at release.
- Document owners: AGENTS = mandatory contributor fences; CONTRIBUTING = workflow
  entry; compatibility = supported/stable behavior; releasing = publication gates;
  CHANGELOG = user-visible version history; verification = dated evidence, never
  new policy. README summarizes and links. Keep each rule in its owner's document.
- Every PR states its responsibility owner, interfaces/trust boundaries touched
  and explicit exclusions. New files must have a current requirement and owner;
  amend an existing owner document before creating another governance document.
- Changes to trust sources, sandbox access, installed artifacts/settings, schema,
  model/effort permissions, delegation budget or data collection need explicit
  requirements, compatibility impact, relevant regressions and L3 final review.
  No silent automatic install/escalation, caller-provided quota authorization,
  periodic quota polling, extra telemetry or destructive recovery.

See [release-source checks](docs/releasing.md) for ignored-file exclusions.
