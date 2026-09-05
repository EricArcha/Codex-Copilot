# Privacy-safe metrics

Metrics are optional and must never block development work. Generate a random run ID locally, then record a start and completion event with the installed CLI.

Allowed values are route metadata only: run ID, event, surface, hashed project, task level, quota band, window percentages, model, effort, subagent count, outcome, elapsed time, and a generic error category.

Never pass a prompt, task summary, source text, file name, raw project path except through `--project` for local hashing, command, log, stack trace, model response, secret, or personal data.

At completion, refresh quota once. `primary_delta_observed` and `secondary_delta_observed` are the after-minus-before changes in used percentage. They may include concurrent activity and must not be presented as exact task cost.

Example shape:

```text
codex-copilot _record --event complete --run-id <random-id> --surface skill \
  --project <current-project-root> --task-level L1 --quota-band green \
  --root-model gpt-5.6-terra --root-effort medium --subagent-count 1 \
  --outcome success --elapsed-seconds 120
```

