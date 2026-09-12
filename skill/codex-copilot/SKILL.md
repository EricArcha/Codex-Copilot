---
name: codex-copilot
description: Orchestrate substantial software implementation and complex fixes in Codex with quota-aware model and subagent routing, bounded context, verification, and independent review. Use for end-to-end development, multi-stage changes, explicit subagent orchestration, or requests to optimize Codex allowance. Do not take over simple edits, questions, or review-only requests unless explicitly invoked.
metadata:
  short-description: Quota-aware development orchestration
---

# Codex Copilot

Complete the requested development outcome while preserving quality and included Codex allowance.

> **Environment:** This version supports Codex Desktop only. Do not rely on its quota-aware routing or custom-agent workflow in a standalone CLI-only environment.

## Start

1. Read applicable `AGENTS.md` files and inspect the target repository narrowly enough to understand its state, commands, and constraints.
2. Obtain a quota snapshot. Prefer a native usage-limit tool when available; otherwise run `codex-copilot status --json`. Never redeem a reset credit.
   Read the active profile with `codex-copilot profile show`; balanced is the default. Premium is explicit and uses Astra only for L3 key work or final review.
3. Classify the task as L0-L3 and choose the route in [routing.md](references/routing.md). If quota cannot be read, use the `unknown` route.
4. State the task level, quota band, chosen route, and definition of done in one short update. Treat the route as a guardrail, not an exact cost prediction.

## Execute

- Keep requirements, decisions, and final evidence in the primary thread. Move bounded exploration, diagnosis, test-output triage, or review to subagents.
- Do not delegate L0. For L1-L3, delegate only independent work that materially improves speed, evidence, or context quality.
- Use the installed `copilot_scout`, `copilot_investigator`, `copilot_worker`, `copilot_reviewer`, and reserved final-review role. In premium L3 routes, use `copilot_astra_final_reviewer`; otherwise use `copilot_final_reviewer`.
- Before every subagent dispatch, run the delegation gate described in [routing.md](references/routing.md). Do not dispatch when it rejects the request. It counts the entire run, refreshes quota, and applies the most restrictive band observed so far. Use `copilot_final_reviewer` only for the permitted L3 Sol High final-review slot.
- Maintain exactly one writer. The primary agent should normally implement; use `copilot_worker` only when implementation itself is the bounded delegated unit. Do not use the multi-writer exception for L3 work.
- Use Sol only when the route permits it, and only for an L3 decision or critical review. Never use Max or Ultra under this skill.
- Apply relevant installed specialist skills only when their own trigger matches. They are optional; do not fail because one is absent.

## Verify and finish

- Run the repository's required checks. Quota pressure may narrow optional exploration but must not remove verification needed for the definition of done.
- For L1-L3 code changes, reserve capacity for an independent review unless the quota route requires pausing. For Green/Yellow L3, spend the single permitted Sol High phase on the final review; the installed Terra High reviewer remains the fallback when Sol is unavailable for reasons other than quota. If the required L3 review cannot run, pause rather than weaken the quality gate.
- Recheck only findings and affected paths after fixes unless new evidence justifies a full review.
- Follow [context.md](references/context.md) when the thread grows or work must pause. Return a compact checkpoint when the remaining quota cannot safely carry the task through testing and review.
- Record privacy-safe route metadata on a best-effort basis using [metrics.md](references/metrics.md); failure to record metrics must not fail the task.
- When any subagent was dispatched, include one short `codex-copilot trace --run <run-id>` summary in the final response; do not expand it unless asked.
