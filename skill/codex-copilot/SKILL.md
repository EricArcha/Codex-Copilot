---
name: codex-copilot
description: Codex Desktop-only development orchestration with quota-aware model and subagent routing, bounded context, verification, and independent review. / 仅供 Codex Desktop 使用的配额感知开发编排技能，适用于端到端开发、复杂修复与多代理协作。Do not use for simple edits, questions, or review-only work unless explicitly invoked.
metadata:
  short-description: Quota-aware development orchestration
---

# Codex Copilot

Complete the requested development outcome while preserving quality and included Codex allowance.

> **Environment:** This version supports Codex Desktop only. Do not rely on its quota-aware routing or custom-agent workflow in a standalone CLI-only environment.

## Reset-credit prohibition

Only the user may manually redeem a reset credit or reset opportunity. Never suggest, recommend, offer, or prompt them to do so. The Skill must never redeem, consume, invoke, or otherwise use one, even if the user asks. If available allowance is insufficient, follow the applicable low-quota route: reduce optional work, return a checkpoint, or pause for the next natural quota-window refresh.

## Start

1. Read applicable `AGENTS.md` files and inspect the target repository narrowly enough to understand its state, commands, and constraints.
2. Find `codex-copilot` using the current shell and platform's launcher; run `doctor --json` when available. Its `installation_state` identifies **skill-only** (instructions only), **complete** (managed files/settings intact), or **incomplete** (managed installation needs repair). Missing PATH alone does not mean Skill-only.
3. If unavailable, inspect known launcher/manifest locations using [installation.md](references/installation.md). State degraded mode once and continue with available guidance; install or change configuration only when requested. Read that reference when installation, upgrade, diagnostics or recovery is needed.
4. For a complete workflow, obtain `codex-copilot status --json` and `codex-copilot profile show` (balanced by default). For permission/state failures, use [quota.md](references/quota.md) for command-scoped host-approved execution; unresolved failures use the unknown route.
5. Use Terra for Green/Yellow L0 work and bounded L1 fixes, Luna for focused exploration, GPT-6.1 Sol for complex implementation/review, and Astra for explicit premium L3 work. Follow [routing.md](references/routing.md); Desktop parent-model selection is a recommendation, not an automatic switch of this chat.
6. Classify the task as L0-L3 and choose the route in [routing.md](references/routing.md). If quota cannot be read, use the `unknown` route.
7. State the task level, quota band, chosen route, and definition of done in one short update. If measurement is enabled, mention in that update that optional local allowance measurement is enabled. Treat the route as a guardrail, not an exact cost prediction.
8. Begin one bounded execution run using [execution.md](references/execution.md). Reuse its canonical UUID for all calls and any optional measurement. Budget normal/worst calls, a total limit and closing reserve; bulk model work additionally requires stage evidence.
9. If `status --json` reports `measurement_enabled: true`, start one optional measurement using [metrics.md](references/metrics.md) and the same UUID for any later subagent dispatch. Do not add a quota read just for a skill-run start snapshot.

## Execute

- Keep requirements, decisions, and final evidence in the primary thread. Move bounded exploration, diagnosis, test-output triage, or review to subagents.
- Do not delegate L0. For L1-L3, delegate only independent work that materially improves speed, evidence, or context quality.
- Use the installed `copilot_scout`, `copilot_investigator`, `copilot_worker`, optional L1-only `copilot_terra_worker`, `copilot_reviewer`, and reserved final-review role. In premium L3 routes, use `copilot_astra_final_reviewer`; otherwise use `copilot_final_reviewer`.
- Before every subagent dispatch or follow-up, run the delegation gate described in [routing.md](references/routing.md). Do not dispatch when it rejects the request. It counts the entire run, refreshes quota, and applies the most restrictive band observed so far. Use `copilot_final_reviewer` only for the permitted L3 Sol High final-review slot.
- Route batch generation, evaluation, repair and scoring through the managed `model exec` entry point and evidence stages in [execution.md](references/execution.md). Do not disguise data-plane work as investigator dispatches.
- Maintain exactly one writer. The primary agent should normally implement; use one worker only when implementation itself is the bounded delegated unit. Sol and Terra workers share one writer slot. Do not use the multi-writer exception for L3 work.
- Use GPT-6.1 Terra for eligible small fixes, GPT-6.1 Sol for complex implementation and all normal review, and GPT-6 Astra only for the explicit premium L3 route. Never use Max or Ultra under this skill.
- Apply relevant installed specialist skills only when their own trigger matches. They are optional; do not fail because one is absent.

## Verify and finish

- Run the repository's required checks. Quota pressure may narrow optional exploration but must not remove verification needed for the definition of done.
- For L1-L3 code changes, reserve capacity for an independent review unless the quota route requires pausing. For Green/Yellow L3, use GPT-6 Astra High for the premium final review; balanced and conservative profiles use GPT-6.1 Sol High. The installed GPT-6.1 Sol High reviewer is the premium fallback when Astra is unavailable for reasons other than quota. If the required L3 review cannot run, pause rather than weaken the quality gate.
- Keep engineering checks, effect acceptance and publication eligibility separate. Missing required effect evidence means an incomplete checkpoint, even when engineering tests pass. Before a release-candidate commit, run `codex-copilot release-check --json`; confirm missing project identity before committing and never change global Git identity.
- Recheck findings and affected paths after fixes through a follow-up of the same reviewer session (`--followup-id`), within the cumulative budget, unless new evidence justifies a full review. A fresh second reviewer requires a bounded user grant.
- Follow [context.md](references/context.md) when the thread grows or work must pause. Return a compact checkpoint when the remaining quota cannot safely carry the task through testing and review.
- Record privacy-safe route metadata on a best-effort basis using [metrics.md](references/metrics.md); failure to record metrics must not fail the task.
- If an optional measurement was started, end it once after the work finishes; allow at most one additional quota read. Measurement failure never blocks delivery.
- When any subagent was dispatched, include one short `codex-copilot trace --run <run-id>` summary in the final response; do not expand it unless asked.
