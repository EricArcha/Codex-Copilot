# Codex-Copilot

[![Codex Desktop](https://img.shields.io/badge/Codex-Desktop-412991?logo=openai&logoColor=white)](https://openai.com/codex/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-f59e0b)](LICENSE)

**A friendly air-traffic controller for big Codex tasks.** It helps Codex decide what deserves a subagent, what should stay focused, and when to save tokens for the final check.

[简体中文](README.zh-CN.md)

> Made for **Codex Desktop** on macOS or Linux.

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

## Want the full cockpit?

The optional full install adds six custom agents, the `codex-copilot` command, and a few managed Codex settings for multi-agent work.

```bash
git clone https://github.com/EricArcha/Codex-Copilot.git
cd Codex-Copilot
./bin/codex-copilot install --dry-run  # look first
./bin/codex-copilot install            # confirm in the terminal
```

Before changing anything, the installer shows every file action and all six settings it manages. For scripts or CI, review the dry run and add `--yes` to confirm.

<details>
<summary>Which Codex settings change?</summary>

- Enable multi-agent work
- Allow up to 3 concurrent subagent tasks
- Set a lightweight default subagent (`gpt-5.6-luna`, low reasoning)
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

It removes only the files it installed and restores a setting only if you have not changed it since installation.

**Deleting `~/.agents/skills/codex-copilot` by hand only removes the Skill. It does not restore Codex settings.** Run `codex-copilot uninstall` instead. If that command is gone too, clone this repository again and run:

```bash
./bin/codex-copilot uninstall
```

Keep `~/.codex-copilot` until recovery is finished—it contains the safe, per-setting restoration record.

## Handy commands

```bash
codex-copilot doctor       # Is everything ready?
codex-copilot status       # How much allowance is left?
codex-copilot profile show # Which routing style is active?
```

Codex-Copilot never redeems usage reset credits. It keeps local routing notes private: no prompts, code, command output, or raw project paths are stored.

## For contributors

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
