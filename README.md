# Codex-Copilot

Codex-Copilot is a quota-aware development orchestrator for Codex. It keeps the primary task focused, delegates bounded work to stable custom agents, and uses the remaining ChatGPT plan allowance as a conservative guardrail.

## Install

Requires Python 3.11+ and a recent Codex CLI on macOS or Linux.

```bash
./bin/codex-copilot install
```

The default installation uses symbolic links so changes in this repository take effect immediately. Use `--mode copy` for a relocatable installation and `--dry-run` to preview changes.

```bash
./bin/codex-copilot install --mode copy
./bin/codex-copilot doctor
./bin/codex-copilot status
```

The installer adds the skill to `~/.agents/skills`, installs four custom agents under `~/.codex/agents`, exposes `~/.local/bin/codex-copilot`, and safely merges a small set of managed settings into `~/.codex/config.toml`.

## Use

Invoke the skill explicitly for the most predictable behavior:

```text
$codex-copilot implement this feature and verify it end to end.
```

For a new CLI session with a quota preflight:

```bash
codex-copilot launch
codex-copilot launch --level complex
codex-copilot launch --level critical -- --cd /path/to/project
```

Codex-Copilot never redeems rate-limit resets. If remaining allowance is too low to preserve required testing and review, it pauses expensive work and reports the reset time.

## Commands

```text
codex-copilot install [--mode symlink|copy] [--dry-run]
codex-copilot uninstall [--dry-run]
codex-copilot doctor [--json]
codex-copilot status [--json] [--refresh]
codex-copilot launch [--level routine|complex|critical] [--dry-run] [--override-quota] [-- <codex args>]
codex-copilot metrics [--days N] [--json]
```

Runtime state is stored in `~/.codex-copilot`. Metrics are local and exclude prompts, code, raw paths, commands, logs, and model responses.

## Uninstall

```bash
codex-copilot uninstall
```

Uninstall removes only artifacts recorded in the install manifest. Managed config values are restored only when the current value still matches the installed value; later user edits are preserved.

