# Bounded Desktop execution

The execution owner enforces cumulative authorized starts, finite route exceptions and
small evidence stages. It is not a billing service or a general workflow engine. Only
managed entry points are enforced; the CLI cannot control Desktop parent turns or other
processes. Run and request IDs are canonical lowercase UUIDs, never task text or filenames.

## Begin once, keep the same run

For ordinary development, budget the native route's allowed children and reserve its
review slot. For example, Yellow L3 normally permits only one final reviewer:

```text
codex-copilot run begin --run-id <uuid> --task-level L3 --profile balanced --normal-calls 1 --worst-calls 1 \
  --call-limit 1 --reserve-calls 1
```

Pin `--task-level` and `--profile` when beginning a mixed model/native run; otherwise the
first call pins them (data-plane defaults to L2 and the active profile).

A model comparison must first expand research, generation, internal validation, repair,
refinement, scoring, probes and review into normal/worst totals. Supply explicit
`--call-limit` and `--reserve-calls`. Stage caps default to 3 model calls each; choose
`--smoke-calls`, `--pilot-calls`, `--batch-calls` to cover the actual minimal pipeline.
Set `--comparison` for paired evaluations. Missing all budget fields creates an offline-only
run; partial budgets are refused. The worst-case plan may exceed the authorized limit:
that means partial delivery/checkpointing, never authorization to consume the worst case.

Optional `--quota-limit-pp <n> --quota-reserve-pp <n>` enables an account-observation guard
for this run only and emits a notice. It reuses a successful Start cache from the last
60 seconds. It neither changes the measurement preference nor fetches quota. Delta is
measured in the primary window from that cached baseline; a different/reset window is
not comparable and blocks the guard. Neither grants nor Green quota raise either limit.
The next turn can consume more than predicted: this is not exact per-task billing.

`run status --run-id <uuid> --json` reads local state only. It shows consumption, current
and strictest bands, reservations, grants, stage and separate engineering/effect/review
acceptance. Raw domain artifacts and hashes stay with the caller.

## Call once, resume honestly

Use the native `_delegate` gate in [routing.md](routing.md) for engineering subagents.
For data-plane calls, supply the prompt on stdin:

```text
codex-copilot model exec --run-id <uuid> --request-id <uuid> --category generation
```

Categories are research, generation, validation, repair, scoring and probe. This entry
uses GPT-6.1 Sol Medium, fixed read-only isolation, an empty stable working directory,
no user-config inheritance, and disabled shell, delegation, apps/plugins/hooks and other
host tools. It refuses a CLI missing the required feature flags. Do not pass model/config
or sandbox overrides. Standard output is model JSONL for the caller; stderr contains only
safe execution metadata. Timeout defaults to 120 seconds, maximum 1200 seconds. Native
Codex session persistence is used for explicit follow-ups; Copilot stores only opaque IDs,
not session contents. Backend-internal retries are not separately observable starts.

Every started attempt remains consumed, including timeout, failure, cancellation and an
uncertain interruption. Replaying a request returns its stored state without generation
or reconstructed output; never treat replay as permission to spawn. Keep original results
and failed receipts in caller-owned checkpoints. `_call reserve/complete` exposes the same
fixed data-plane policy for adapters; external completion/configuration remains declared,
not verified backend telemetry. Adapters must not spawn on a replay or overwrite receipts.

A follow-up uses a new request UUID and `--followup-id <previous-request-id>`. The completed
parent must have a bound session; kind, role/model/effort, phase and category cannot change.
Unresolved turns prevent overlapping resumes. Each continuation consumes another slot.

## Evidence before expansion

Record offline synthetic-protocol verification with a new opaque evidence UUID:

```text
codex-copilot run checkpoint --run-id <uuid> --stage offline \
  --outcome success --evidence-id <uuid>
```

Then run the bounded smoke stage to completion and checkpoint `--stage smoke`. A comparison
smoke must execute a successful independent `scoring` call and add `--scored`. It is interface
and pipeline evidence only, never formal effect acceptance. The pilot and each batch also
require `--paired --scored`, a successful scoring call and a new caller-owned evidence
reference. Only then may the next bounded tranche start. The caller verifies actual pair
identity, independence, protocol correctness and domain quality; boolean declarations and
opaque references do not let Copilot inspect those artifacts.

Two consecutive `--outcome blocked --blocker <protocol|interface|quality|runtime|budget>`
checkpoints of the same category pause model calls. Diagnose offline, then submit a new
offline success evidence UUID to resume the same stage. This never refunds calls or resets
the stage cap. A fresh batch checkpoint must include new successful calls, not prior evidence.

Update `--engineering passed|failed`, `--effect passed|failed`, `--review passed|failed`
with a successful checkpoint. A comparison cannot mark effect not_required; passed effect
requires formal paired scoring. `run close --outcome completed` refuses missing acceptance
or unresolved calls. Use paused/failed to deliver an honest checkpoint. Publication eligibility
is only an acceptance declaration, not publishing approval or a replacement for repo gates.

## Finite exceptions and recovery

Only when the user explicitly authorizes the particular exception:

```text
codex-copilot grant --run-id <uuid> --grant-id <uuid> --phase final_review \
  --category review --count 1 --expires-in 600 --user-authorized
```

Pass `--grant-id` on the intended dispatch. It is scoped to the current stage, phase and
category; replaying grant creation does not refill or extend it. It cannot broaden model,
effort or writer policy, raise the total budget, consume a closing reserve for ordinary
work, or bypass missing quota/evidence gates. Do not interpret a general “continue” as
unlimited exceptions. An unavailable grant requires a checkpoint or a specific new grant.

Old traces remain legacy declarations. To recover one, explicitly confirm at least the
retained maximum ordinal/consumed count using `run begin --resume-consumed <n>` with a
budget covering previous consumption. Missing history is never automatically assumed zero.
For a paused durable run, repeat its original budget with `--resume-consumed` equal to the
stored count; it resumes without changing caps, strictest band or call receipts. Unknown,
corrupt, unsupported or unwritable state is preserved and fails closed. Do not delete it
to regain capacity; no destructive recovery is provided.
