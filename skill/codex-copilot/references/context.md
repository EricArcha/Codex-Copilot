# Context and checkpoint policy

Keep one primary thread per coherent, reviewable outcome rather than per project.

After planning, retain the goal, constraints, affected modules, risks, and definition of done. Do not copy raw exploration into the primary thread.

After implementation, retain changed files, decisions, verification commands and results, open findings, and remaining risks. Ask for `/compact` after a tool-heavy milestone when the client has not already compacted the task.

Fork only when exploring a genuinely different direction; a fork preserves history and is not a substitute for a clean handoff.

When pausing or starting a new task, return this checkpoint:

```markdown
## Goal
## Current state
## Decisions
## Changed files
## Verification
## Known risks
## Next quota-window refresh time
## Next action
```

Reference existing plans, diffs, ADRs, or commits instead of duplicating them. Redact secrets and personal data.
