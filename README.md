# Codex-Copilot

[![Runtime](https://img.shields.io/badge/runtime-Codex%20Desktop-412991?logo=openai&logoColor=white)](https://openai.com/codex/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Standard library](https://img.shields.io/badge/dependencies-standard%20library-0f766e)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-f59e0b)](LICENSE)

**A calmer cockpit for complex Codex work.** Codex-Copilot keeps implementation, delegation, allowance, and independent verification in one deliberate flight path—so “go build it” does not turn into “where did the context go?”

[简体中文](README.zh-CN.md)

> **Codex Desktop only.** This release is designed for Codex Desktop on macOS or Linux. Its usage-aware routing and custom-agent workflow rely on the Desktop environment; standalone CLI use is not a supported deployment target yet.

## Description

**English:** A Codex Desktop-only skill and CLI that orchestrates substantial development with quota-aware routing, bounded subagents, and independent verification.

**中文：** 一个仅供 Codex Desktop 使用的 Skill 与 CLI：通过配额感知路由、边界明确的子代理和独立验证，编排复杂开发工作。

## Why Codex-Copilot?

- **Protects the finish line** — reserves the evidence and review needed to know a change is actually done.
- **Uses context deliberately** — delegates only bounded work that benefits from a fresh set of eyes.
- **Treats allowance as a guardrail** — scales the route to the available budget without silently skipping required checks.
- **Keeps telemetry private** — local metrics omit prompts, code, paths, commands, logs, and model responses.

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

The installer adds the skill to `~/.agents/skills`, installs six custom agents under `~/.codex/agents`, exposes `~/.local/bin/codex-copilot`, and safely merges a small set of managed settings into `~/.codex/config.toml`.

## The flight path

```text
Understand scope  →  Check allowance  →  Route the work  →  Build  →  Verify independently
```

Codex-Copilot is intentionally opinionated about the last step: a passing implementation is not the same thing as a reviewed delivery.

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
codex-copilot profile set premium
codex-copilot launch --profile premium --level critical
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
codex-copilot profile list|show|set <conservative|balanced|premium>
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

If an app-server refresh transiently fails, the gate can reuse only its own most recent successful
app-server snapshot (60-second TTL). This degraded result is labeled `cache-fallback`; callers
cannot supply a quota band or snapshot.

## Profiles and allowance

`balanced` is the default: when the 5-hour window has at least 50% remaining and the weekly
window at least 35%, L1/L2 work can use one Luna scout and one independent Terra reviewer.
Guarded capacity (30%/20%) reserves its one slot for review. `conservative` keeps the
low-cost route; `premium` uses Astra only for L3 root work and its reserved final review.
Premium is explicit and never silently selected.

## Uninstall

```bash
codex-copilot uninstall
```

Uninstall removes only artifacts recorded in the install manifest. Managed config values are restored only when the current value still matches the installed value; later user edits are preserved.
