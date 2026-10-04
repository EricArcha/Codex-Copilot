# Codex-Copilot

[![Codex Desktop](https://img.shields.io/badge/Codex-Desktop-412991?logo=openai&logoColor=white)](https://openai.com/codex/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-f59e0b)](LICENSE)

**A friendly air-traffic controller for big Codex tasks.** It helps Codex decide what deserves a subagent, what should stay focused, and when to save tokens for the final check.

[简体中文](README.zh-CN.md)

> Made for **Codex Desktop** on Windows, macOS and Linux. Requires Python 3.11+ and Codex CLI 0.147.0+.

## Project demo

<p align="center">
  <a href="https://github.com/EricArcha/Codex-Copilot/raw/refs/heads/main/videos/codex-copilot-demo/exports/codex-copilot-intro-web.mp4">
    <img src="videos/codex-copilot-demo/exports/codex-copilot-intro.gif" width="800" alt="Codex-Copilot workflow: allowance-aware routing, bounded delegation and independent verification">
  </a>
</p>
<p align="center">
  <a href="https://github.com/EricArcha/Codex-Copilot/raw/refs/heads/main/videos/codex-copilot-demo/exports/codex-copilot-intro-web.mp4"><strong>Watch with sound · MP4</strong></a>
  &nbsp; · &nbsp;
  <a href="https://github.com/EricArcha/Codex-Copilot/raw/refs/heads/main/videos/codex-copilot-demo/exports/codex-copilot-intro-master.mp4">1080p · 60fps</a>
</p>
<p align="center"><sub>24 seconds. A clear route from request to evidence. The GIF preview is silent.</sub></p>

## Current source version: 1.0.0

Codex-Copilot 1.0.0 establishes stable installation, CLI/JSON compatibility and release boundaries. The GitHub Release has been withdrawn; the source version and tag remain available. See [CHANGELOG](CHANGELOG.md), [compatibility](docs/compatibility.md), [release policy](docs/releasing.md) and [contributing](CONTRIBUTING.md).

Codex-Copilot now routes work across the GPT-6 family: **Luna** handles focused exploration and is the default subagent, **GPT-6.1 Sol** handles normal development and review, and **Astra** is reserved for premium L3 high-risk work and final review. Existing full-install users should update their source checkout to this version, then run `./bin/codex-copilot install` again, then restart Codex Desktop and open a new task.

## Project milestones

Source-history milestones; 0.1.x were source versions, not tagged GitHub releases.

| Date | Milestone | What changed |
| --- | --- | --- |
| 2026-09-05 | Initial foundation | Quota-aware orchestration, managed roles and installation. |
| 2026-09-07 | Delegation guardrails | Executable dispatch checks and bounded subagent work. |
| 2026-09-12 | Routing profiles | Conservative, balanced and premium routes. |
| 2026-09-16 | Guided installation | Preview and confirmation for managed installation. |
| 2026-09-25 | Optional measurement | Opt-in local allowance observations and GPT-6 routing. |
| 2026-09-30 | Standard-route update | Normal development and review moved to GPT-6.1 Sol. |
| 2026-10-02 | Native Windows support | Cross-platform installation, process handling and CI. |
| 2026-10-02 | [Source version: 1.0.0](https://github.com/EricArcha/Codex-Copilot/tree/v1.0.0) | Compatibility contract, upgrade verification and release boundaries. |

See [CHANGELOG](CHANGELOG.md) for version details.

## Start in 30 seconds

Want to try the Skill with **zero settings changes**? Install just the instructions:

```bash
npx skills add EricArcha/Codex-Copilot --skill codex-copilot -g --copy -y
```

Then ask Codex:

```text
$codex-copilot help me build this feature end to end.
```

That is it. No agents, CLI files, or Codex settings are added.

Skill-only provides workflow instructions. Actual CLI quota reads, managed roles and the executable delegation gate require the full installation below.

## Want the full cockpit?

The optional full install adds six custom agents, the `codex-copilot` command, and a few managed Codex settings for multi-agent work. Copy mode is the default and needs no administrator rights. On macOS/Linux:

```bash
git clone https://github.com/EricArcha/Codex-Copilot.git
cd Codex-Copilot
git checkout v1.0.0
./bin/codex-copilot install --dry-run  # look first
./bin/codex-copilot install            # confirm in the terminal
```

On Windows PowerShell:

```powershell
git clone https://github.com/EricArcha/Codex-Copilot.git
cd Codex-Copilot
git checkout v1.0.0
.\bin\codex-copilot.cmd install --dry-run
.\bin\codex-copilot.cmd install
& "$HOME\.local\bin\codex-copilot.cmd" doctor --json
```

The Windows launcher discovers `py -3` or `python`; no version-specific interpreter path is embedded. Keep a Python 3.11+ installation available. Codex is discovered on PATH; native executables and standard npm wrappers with Node/the adjacent JS entry are supported. Quote shell metacharacters in arguments.

Default installation does not edit PATH. Use the displayed full launcher path, or set `$env:PATH = "$HOME\.local\bin;$env:PATH"` for a PowerShell session. Add `--add-to-path` to both preview and install to manage persistent **Windows user PATH** explicitly; open a new terminal afterward. It never changes system PATH. Configure your shell PATH yourself on macOS/Linux.

An existing `$CODEX_HOME/skills/codex-copilot` registration is reused; otherwise the default is `~/.agents/skills`. Verified current/known release instructions can be backed up and adopted. Unknown files, edited managed artifacts and duplicate registrations block installation. Resolve conflicts after backing them up. `CODEX_COPILOT_SKILLS_HOME`, `CODEX_COPILOT_BIN_DIR`, `CODEX_COPILOT_SHARE_DIR` and `CODEX_COPILOT_STATE_DIR` override their respective locations; `CODEX_HOME` selects Codex configuration. Custom runtime locations are supported. Uninstall before changing configuration/Skill directories or a bin directory with owned persistent PATH; resolve any restored original Skill registration before moving it.

Before changing anything, the installer shows every file action and all six settings it manages. For scripts or CI, review the dry run and add `--yes` to confirm.

<details>
<summary>Which Codex settings change?</summary>

- Enable multi-agent work
- Allow up to 3 concurrent subagent tasks
- Set a lightweight default subagent (`gpt-6-luna`, low reasoning)
- Use the standard service tier and disable fast mode

The original values are recorded for safe restoration.
</details>

## What happens inside?

```text
Understand the task → choose the smallest useful team → protect the token budget → verify independently → ship with evidence
```

Codex-Copilot is intentionally a little stubborn: it would rather finish one well-checked change than send a crowd of agents chasing tiny edits.

## Remove it safely

Use this when you want to uninstall the complete workflow:

```bash
codex-copilot uninstall
```

Preview with `uninstall --dry-run`. Uninstall removes unchanged managed artifacts and restores a setting only while it still equals the installed value. An unchanged adopted Skill is restored from backup. Modified artifacts remain with a recovery manifest; resolve them and rerun uninstall from a source checkout. Backups and measurement records are retained.

**Deleting `~/.agents/skills/codex-copilot` by hand only removes the Skill. It does not restore Codex settings.** Run `codex-copilot uninstall` instead. If that command is gone too, clone this repository again and run:

```bash
./bin/codex-copilot uninstall
```

On Windows use `.\bin\codex-copilot.cmd uninstall`. Upgrade by updating the source checkout and using the same platform's `install --dry-run` and `install` commands. Upgrades preserve the original restoration records. Unique backups and staging allow rollback on caught errors; file locks may also prevent rollback, in which case preserve the reported backup directory and recover from its `recovery.json`. An interrupted process may require manual recovery.

Keep `~/.codex-copilot` until recovery is finished—it contains the safe, per-setting restoration record.

`doctor --json` distinguishes `skill-only`, `complete` and `incomplete` installations. It checks configuration and artifacts, but installed agent files do not prove runtime model entitlement. Quota errors use a recent successful cache only within the existing TTL; otherwise the route is `unknown`. Reads time out and reap their subprocess. See the [installation reference](skill/codex-copilot/references/installation.md) for recovery and platform commands.

## Handy commands

```bash
codex-copilot doctor       # Is everything ready?
codex-copilot status       # How much allowance is left?
codex-copilot profile show # Which routing style is active?
codex-copilot measure status # Is optional allowance measurement on?
codex-copilot measure on     # Opt in to task-level measurement
codex-copilot measure off    # Stop new automatic measurement
```

Allowance measurement is off by default. New installs and upgrades show the one-time opt-in command; enabling it once persists locally. When enabled, a skill task briefly notes that recording is on, reuses its start quota check, and makes at most one extra read at completion. Turning it off preserves prior records. Percentages are observations, not exact bills or proven savings. Codex-Copilot never redeems usage reset credits. Its GPT-6 routing uses Luna for focused exploration, GPT-6.1 Sol for standard coding and review, and Astra only for premium L3 work. It keeps local routing notes private: no prompts, code, command output, or raw project paths are stored.

## For contributors

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

PowerShell: `$env:PYTHONPATH = 'src'`, then `python -m unittest discover -s tests -v`. Also run the Skill Creator `quick_validate.py` as specified in [AGENTS.md](AGENTS.md). Product code uses only the standard library; PyYAML is only for the external validator. CI covers Python 3.11–3.14 on all three platforms. Symlink tests probe actual capability; ordinary-user Windows copy installation remains fully tested.

See [verification evidence and remaining limits](docs/verification.md) for the actual local results; consult PR checks for executed CI results.


## Verify and upgrade

For an existing source checkout, fetch tags and select the desired source tag after preserving local work. Review the platform installer dry-run, install, then restart Desktop and open a fresh chat. Verify the installed version is 1.0.0 and `doctor --json` reports complete. Use the displayed full launcher path if it is not on PATH.

`status --refresh --json` must return real windows with source=app-server. A complete installation alone does not certify live quota or model access. For permission/state errors use command-scoped host-approved execution described in [quota access](skill/codex-copilot/references/quota.md). Unknown is temporary degradation; Desktop percentages do not replace the executable gate. A live cache-write warning preserves the observation but state access must be resolved before trace-writing commands.

Detailed platform, upgrade, conflict and recovery instructions: [installation reference](skill/codex-copilot/references/installation.md).
