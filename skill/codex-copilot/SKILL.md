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
2. Check whether `codex-copilot` is available. If it is available, run `codex-copilot doctor --json` and treat missing required `copilot-*` agent checks as an incomplete workflow. If the CLI or a required agent is missing, state once that this is **Skill-only mode**: the orchestration guidance is available, while custom-agent routing, CLI diagnostics, and managed Codex configuration are optional enhancements. Continue with the task; do not install anything or modify configuration. If the user wants the complete workflow, offer these user-run commands:
   ```bash
   git clone https://github.com/EricArcha/Codex-Copilot.git
   cd Codex-Copilot
   ./bin/codex-copilot install --dry-run
   ./bin/codex-copilot install
   ```
   The complete installer shows every managed configuration change and requires confirmation. If a user manually deleted the Skill, explain that this does not restore Codex settings; `codex-copilot uninstall` safely removes managed artifacts and restores eligible settings. If its launcher is also gone, they can re-clone this repository and run `./bin/codex-copilot uninstall`; preserve `~/.codex-copilot` until recovery is complete. If the complete workflow is healthy, obtain a quota snapshot with `codex-copilot status --json` and read the active profile with `codex-copilot profile show`; balanced is the default. Use GPT-6 Luna for focused exploration, GPT-6 Sol for normal implementation and review, and reserve GPT-6 Astra for explicit premium L3 key work or final review. The reset-credit prohibition applies without exception.
3. Classify the task as L0-L3 and choose the route in [routing.md](references/routing.md). If quota cannot be read, use the `unknown` route.
4. State the task level, quota band, chosen route, and definition of done in one short update. If measurement is enabled, mention in that update that optional local allowance measurement is enabled. Treat the route as a guardrail, not an exact cost prediction.
5. If `status --json` reports `measurement_enabled: true`, start one optional measurement using [metrics.md](references/metrics.md) and the same UUID for any later subagent dispatch. Do not add a quota read just for a skill-run start snapshot.

## Execute

- Keep requirements, decisions, and final evidence in the primary thread. Move bounded exploration, diagnosis, test-output triage, or review to subagents.
- Do not delegate L0. For L1-L3, delegate only independent work that materially improves speed, evidence, or context quality.
- Use the installed `copilot_scout`, `copilot_investigator`, `copilot_worker`, `copilot_reviewer`, and reserved final-review role. In premium L3 routes, use `copilot_astra_final_reviewer`; otherwise use `copilot_final_reviewer`.
- Before every subagent dispatch, run the delegation gate described in [routing.md](references/routing.md). Do not dispatch when it rejects the request. It counts the entire run, refreshes quota, and applies the most restrictive band observed so far. Use `copilot_final_reviewer` only for the permitted L3 Sol High final-review slot.
- Maintain exactly one writer. The primary agent should normally implement; use `copilot_worker` only when implementation itself is the bounded delegated unit. Do not use the multi-writer exception for L3 work.
- Use GPT-6 Sol for normal coding, implementation, and review routes. Use GPT-6 Astra only for the explicit premium L3 route. Never use Max or Ultra under this skill.
- Apply relevant installed specialist skills only when their own trigger matches. They are optional; do not fail because one is absent.

## Verify and finish

- Run the repository's required checks. Quota pressure may narrow optional exploration but must not remove verification needed for the definition of done.
- For L1-L3 code changes, reserve capacity for an independent review unless the quota route requires pausing. For Green/Yellow L3, use GPT-6 Astra High for the premium final review; balanced and conservative profiles use GPT-6 Sol High. The installed GPT-6 Sol High reviewer is the premium fallback when Astra is unavailable for reasons other than quota. If the required L3 review cannot run, pause rather than weaken the quality gate.
- Recheck only findings and affected paths after fixes unless new evidence justifies a full review.
- Follow [context.md](references/context.md) when the thread grows or work must pause. Return a compact checkpoint when the remaining quota cannot safely carry the task through testing and review.
- Record privacy-safe route metadata on a best-effort basis using [metrics.md](references/metrics.md); failure to record metrics must not fail the task.
- If an optional measurement was started, end it once after the work finishes; allow at most one additional quota read. Measurement failure never blocks delivery.
- When any subagent was dispatched, include one short `codex-copilot trace --run <run-id>` summary in the final response; do not expand it unless asked.
