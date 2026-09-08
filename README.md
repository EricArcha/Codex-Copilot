# Codex-Copilot

Codex-Copilot is a quota-aware development orchestrator for Codex. It keeps the primary task focused, delegates bounded work to stable custom agents, and uses the remaining ChatGPT plan allowance as a conservative guardrail.

## Install

Requires Python 3.11+ and a recent Codex CLI on macOS or Linux.

```bash
./bin/codex-copilot install
```

The default installation uses regular copied files for stable Codex compatibility. Re-run the
installer after changing this source checkout to deploy those changes. Use `--dry-run` to preview
the installation.

```bash
./bin/codex-copilot doctor
./bin/codex-copilot status
```

For local development only, `--mode symlink` keeps this checkout live:

```bash
./bin/codex-copilot install --mode symlink
```

**Warning:** Codex can reject symlinked custom-agent configuration files and report
`agent type is currently not available`. Prefer the default copied installation. To migrate back,
run `codex-copilot install --mode copy`, restart Codex Desktop, and open a new task. See the
[tracked Codex compatibility issue](https://github.com/openai/codex/issues/40131).

The installer adds the skill to `~/.agents/skills`, installs five custom agents under `~/.codex/agents`, exposes `~/.local/bin/codex-copilot`, and safely merges a small set of managed settings into `~/.codex/config.toml`.

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
codex-copilot install [--mode copy|symlink] [--dry-run]
codex-copilot uninstall [--dry-run]
codex-copilot doctor [--json]
codex-copilot status [--json] [--refresh]
codex-copilot launch [--level routine|complex|critical] [--dry-run] [--override-quota] [-- <codex args>]
codex-copilot metrics [--days N] [--json]
codex-copilot trace [--run RUN_ID] [--json]
```

Runtime state is stored in `~/.codex-copilot`. Metrics are local and exclude prompts, code, raw paths, commands, logs, and model responses.

`trace` shows the declared configuration and observed lifecycle of subagents dispatched by
the Skill. It is not backend billing telemetry.

## Delegation governance

Every child dispatch passes a local quota gate. The gate refreshes allowance, treats the run's
subagent cap as cumulative, and retains the most restrictive quota band observed during that
run. It reserves the required final-review slot before allowing exploratory work. A trace stores
only declared agent policy and generic lifecycle state, using an opaque UUID run ID; it never
stores task content or agent output. Exceeding the budget requires explicit user authorization
and is labeled in the trace.

## Uninstall

```bash
codex-copilot uninstall
```

Uninstall removes only artifacts recorded in the install manifest. Managed config values are restored only when the current value still matches the installed value; later user edits are preserved.
