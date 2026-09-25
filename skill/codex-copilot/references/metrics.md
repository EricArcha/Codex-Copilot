# Optional allowance measurement

Task-level measurement is off by default. `codex-copilot measure on|off|status` changes only a local preference. The existing subagent dispatch trace remains active for the delegation cap even when measurement is off. Turning measurement off does not delete history.

When `codex-copilot status --json` says `measurement_enabled: true`, generate one canonical UUID and run after the Start quota check. If quota status is unavailable, `codex-copilot measure status` reads this local preference without contacting the quota service:

```text
codex-copilot measure begin --if-enabled --run-id <uuid> --variant skill \
  --task-level L2 --task-kind bugfix --root-model gpt-6-sol --project <current-project-root>
```

Use `bugfix`, `feature`, `refactor`, or `maintenance` as a coarse task kind. Reuse this UUID for any `_delegate` calls. A skill-run begin only uses the existing 60-second CLI quota cache; it never starts an extra quota read. If the Start snapshot came from the Codex app tool instead, pass only available numeric `usedPercent` and `resetsAt` values as `--primary-used`, `--secondary-used`, `--primary-reset`, and `--secondary-reset`. Missing values make the observation incomplete and exclude it from comparisons.

At task completion, run once:

```text
codex-copilot measure end --run-id <uuid> --outcome success
```

This attempts one fresh quota read, with a five-second timeout. If the Codex app tool already supplied a completion snapshot, pass the same four numeric options and avoid the CLI read. Do not poll, retry for measurement alone, or dispatch agents to gather metrics. A measurement failure must not block the task.

For a deliberately selected task without the skill, use `measure begin --variant baseline` and `measure end` with the same metadata. Explicit one-task commands work while the global preference is off. Compare two successful, comparable runs locally with `codex-copilot measure compare --skill-run <uuid> --baseline-run <uuid>`.

Metrics save only opaque run IDs, hashed project roots, coarse task metadata, model declarations, agent routes, outcomes, and numeric allowance snapshots. Never save prompts, task summaries, source text, file names, raw project paths, commands, logs, model responses, secrets, or personal data. Window percentage changes are observations that may include concurrent activity; they are not exact task costs or proof of savings.
