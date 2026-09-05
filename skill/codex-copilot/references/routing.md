# Routing policy

## Task level

- **L0**: Clear, local, low-risk micro-change with an obvious verification command. Use Terra Medium in the existing parent session, no subagent, and no independent review. New behavior or an ordinary feature is at least L1 even when it touches one module.
- **L1**: Normal change within one module. Use Terra Medium; add `copilot_scout` only when location or existing coverage is unclear; finish with `copilot_reviewer`.
- **L2**: Cross-module change or unclear root cause. Use `copilot_scout` and/or `copilot_investigator` within the quota cap, one writer, then `copilot_reviewer`.
- **L3**: Authentication, payment, permissions, migration, concurrency, security-sensitive, or otherwise high-blast-radius work. Reserve Sol High for one key decision or final review when the quota band permits it.

Classify from actual blast radius and uncertainty, not prompt length. A large mechanical change can be L1; a one-line permission change can be L3.

## Quota band

Use the lower remaining percentage across the primary and secondary Codex windows.

| Band | Remaining | Policy |
|---|---:|---|
| Green | 60-100% | Terra Medium parent. L0 has no subagent; L1-L3 may use up to two read-heavy subagents. L3 uses one Sol High final-review phase. |
| Yellow | 30-59% | Terra Medium parent. One subagent maximum for L1-L3. No Max or Ultra. Reserve Sol for the L3 final review. |
| Red | 10-29% | L0: Luna Low. L1: Terra Low/Medium without delegation. Pause L2/L3. |
| Critical | under 10% or reached | Do not begin code changes. Produce a checkpoint and reset time. |
| Unknown | unavailable | Terra Medium, one read-only subagent maximum, no Sol/Max/Ultra. |

Never redeem resets automatically. An explicit user instruction is required to override a pause. If an override arrives, preserve required tests and review rather than silently lowering the quality bar.

When Red pauses L2/L3, perform only the Start section's narrow read-only triage. Do not delegate, modify code or configuration, or start review. Immediately return a checkpoint with the task level, quota band, known evidence, zero changed files, reset time, and next action.

For Green L3, use at most one read-only investigator before implementation and reserve the other agent slot for the final Sol High review. Keep exactly one writer. The definition of done must cover the relevant permission matrix, migration compatibility, failure rollback or retry behavior, and representative existing data.

## Delegation economy

- Subagents are not free. Do not delegate work the primary agent can complete faster than it can describe and integrate.
- Prefer parallel agents for independent read-heavy work. Avoid one agent per file or multiple agents reading the same area.
- Every delegated prompt must name its bounded question, read/write authority, completion condition, and compact output shape.
- Start subagents with the narrowest available context (`fork_turns: none` for a fresh bounded child) unless the task genuinely depends on recent parent turns.
- Do not let subagents recursively delegate.
