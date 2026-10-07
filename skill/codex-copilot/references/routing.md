# Routing policy

## Task level

- **L0**: Clear, local, low-risk micro-change with an obvious verification command. Use GPT-6.1 Sol Medium in the existing parent session, no subagent, and no independent review. New behavior or an ordinary feature is at least L1 even when it touches one module.
- **L1**: Normal change within one module. Use GPT-6.1 Sol Medium; add `copilot_scout` only when location or existing coverage is unclear; finish with `copilot_reviewer`.
- **L2**: Cross-module change or unclear root cause. Use `copilot_scout` and/or `copilot_investigator` within the quota cap, one writer, then `copilot_reviewer`.
- **L3**: Authentication, payment, permissions, migration, concurrency, security-sensitive, or otherwise high-blast-radius work. Reserve GPT-6.1 Sol High for one key decision or final review when the quota band permits it; the premium profile may instead reserve GPT-6 Astra High.

Classify from actual blast radius and uncertainty, not prompt length. A large mechanical change can be L1; a one-line permission change can be L3.

## Model policy

Pin normal coding and review to `gpt-6.1-sol`; use Medium for standard implementation
routes, Low for conservative Green and Red routes, and High for independent review. Luna remains the focused exploration tier and Astra the
premium L3 tier. GPT-6.1 Sol does not support `none` or `minimal`; this skill permits
only its declared Low/Medium/High routes, never Max or Ultra. Account availability
must be checked in Codex Desktop; do not silently substitute an older model in an
installed role. Upgrade the managed installation before dispatching the new roles.

Model and effort compatibility: [official GPT-6.1 Sol documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol).

## Quota band

Evaluate the two Codex windows independently: a healthy five-hour window must not be treated as
depleted solely because the weekly window is moderately lower.

| Band | Remaining | Policy |
|---|---:|---|
| Green / standard | 5-hour ≥50% and weekly ≥35% | GPT-6.1 Sol Medium parent. L0 has no subagent; L1/L2 may use one Luna scout and one Sol final reviewer. L3 reserves its final review. |
| Yellow / guarded | 5-hour ≥30% and weekly ≥20% | One reviewer slot for code-changing L1-L3 work; a diagnosis-only task may use it for a scout. |
| Red | 10-29% | L0: GPT-6 Luna Low. L1: GPT-6.1 Sol Low/Medium without delegation. Pause L2/L3. |
| Critical | under 10% or reached | Do not begin code changes. Produce a checkpoint and the next natural quota-window refresh time. |
| Unknown | unavailable | GPT-6.1 Sol Medium, one read-only subagent maximum, no Astra/Max/Ultra. |

Reset credits and reset opportunities are exclusively manual user actions. Never suggest, recommend, offer, prompt, redeem, consume, invoke, or otherwise use one—even on explicit user instruction. An explicit user instruction may override a route pause to continue work, but it never authorizes reset-credit use. If an override arrives, preserve required tests and review rather than silently lowering the quality bar.

## Delegation gate

The subagent cap is cumulative for one run: completed, failed, cancelled and sequential
children still consume slots. Begin a durable run as described in [execution.md](execution.md).
Generate one run UUID per task and a separate request UUID per attempted child or follow-up:

```text
codex-copilot _delegate dispatch --run-id <run-id> --request-id <request-id> \
  --task-level <L0-L3> --role <copilot_role> --phase <exploration|implementation|final_review>
```

Only call the child when the gate succeeds with `replayed=false`. A replay is an existing
reservation, never permission to spawn again. Record the result with `_delegate complete
--run-id <run-id> --ordinal <n> --outcome <success|failure|cancelled|unknown>`; add the actual
opaque `--session-id` when known. Follow-ups use a new request UUID and `--followup-id`
pointing to the original request. They preserve session role/model/effort/phase and consume
another total-call and child slot. Native execution remains a declaration, not backend telemetry.

The gate refreshes quota before each new native dispatch. It can use only its own successful
60-second cache fallback. It never accepts caller-reported quota. Durable execution state,
not rotating metrics, retains the cumulative count and most restrictive observed band;
window refresh never resets either. Status shows current/effective bands separately.

Bare `--override` is rejected. Only after explicit user authorization, create a scoped,
expiring `grant` for the run, current stage, phase and category, then pass `--grant-id`.
The default grant permits one additional attempt for ten minutes. It cannot bypass total
call/allowance limits, closing reserve, stage evidence, role/config policy or writer ownership.
The CLI records a user-authorization declaration; it cannot independently authenticate intent.
See [execution.md](execution.md) for commands and legacy recovery.

Reserve review capacity: Green/standard L1/L2 allows at most one exploratory child plus the final
`copilot_reviewer`; Yellow/Unknown L1/L2 reserves the only slot for that reviewer. Green L3
allows at most one read-only scout/investigator plus `copilot_final_reviewer` (GPT-6.1 Sol High).
Yellow L3 reserves its only slot for that final reviewer. Unknown L3 reserves it for
`copilot_reviewer`; Red and Critical allow none. If Astra is unavailable for a non-quota reason,
use `copilot_reviewer` with `--astra-unavailable` as the sole L3 final-review fallback.
Explorers use only `exploration`, workers only `implementation`, and reviewers only
`final_review`; the gate rejects a role/phase mismatch and any installed agent configuration
that differs from the declared route policy.

For a Yellow diagnosis with no code change, pass `--read-only` with a scout or investigator;
that consumes the guarded slot and makes a later reviewer dispatch unavailable.

When Red pauses L2/L3, perform only the Start section's narrow read-only triage. Do not delegate, modify code or configuration, or start review. Immediately return a checkpoint with the task level, quota band, known evidence, zero changed files, next natural quota-window refresh time, and next action. A user override may resume work, but never permits reset-credit use.

For Green/standard L3, use at most one read-only investigator before implementation and reserve the other agent slot for the final review. The premium profile uses the dedicated GPT-6 Astra final reviewer; balanced and conservative use GPT-6.1 Sol High. Keep exactly one writer. The definition of done must cover the relevant permission matrix, migration compatibility, failure rollback or retry behavior, and representative existing data.

## Delegation economy

- Subagents are not free. Do not delegate work the primary agent can complete faster than it can describe and integrate.
- Prefer parallel agents for independent read-heavy work. Avoid one agent per file or multiple agents reading the same area.
- Every delegated prompt must name its bounded question, read/write authority, completion condition, and compact output shape.
- Start subagents with the narrowest available context (`fork_turns: none` for a fresh bounded child) unless the task genuinely depends on recent parent turns.
- Do not let subagents recursively delegate.

For sandbox permission or local-state failures, use the command-scoped host
approval procedure in [quota.md](quota.md). Desktop observations never replace
the CLI gate. A rejected approval does not authorize a dispatch.
