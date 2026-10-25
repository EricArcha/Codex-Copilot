# Confirmed decisions

**State:** FROZEN
**Decision owner:** repository owner (EricArcha)
**Source review:** 2026-10-25 review of Codex-Copilot follow-ups (items #6–#10)
**Discover route:** built-in Cross-Agent Delivery Discover procedure; questions asked in a Claude Code session before the skill was formally loaded, then recorded here when Plan invoked `cross-agent-delivery`. Companion skills: grilling `not required`, domain-modeling `not required` (no terminology or module-boundary change).

Planning that implements these decisions: [stage s01](../implementation/stages/s01-review-followups/README.md).

## D-01 Final-review slot per run (follow-up #6)

- **Question:** Green runs have two child slots. Docs say "one exploration + one final review"; code (`execution.py` → `delegation._allow_role`, `child_consumed`) lets the second slot dispatch a second, fresh reviewer.
- **Evidence:** `count` is the run-wide child total, so `count <= 1` / `count < 2` admit final→final. `SKILL.md` "Recheck only findings and affected paths after fixes" relies on a follow-up of the reviewer session, which also consumes a slot.
- **Confirmed answer (2026-10-26):** one final-review session per run. After a final-review-phase child exists in the run, a new (non-follow-up) final-review dispatch is denied; a follow-up of that same reviewer session remains allowed within the existing cumulative budget. A bounded user grant may still authorize an extra reviewer.
- **Rejected:** strict single review call (would forbid the documented recheck); keeping the current code (allows two independent reviewers, contradicting docs).
- **Consequences:** stricter delegation policy; compatibility note required. Affects S01-REQ-1.

## D-02 Single-window thresholds (follow-up #7)

- **Question:** `routing.band_for_remaining` uses 60/30/10 for a single quota window; `routing.md` documents only the two-window 50/35 rule.
- **Confirmed answer (2026-10-26):** document the existing 60/30/10 single-window behavior; do not change thresholds. Add a test that keeps code and documentation aligned.
- **Rejected:** unifying thresholds (silently changes bands for single-window plans).
- **Consequences:** documentation only. Affects S01-REQ-2.

## D-03 Implicit invocation policy (follow-up #9)

- **Question:** `skill/codex-copilot/agents/openai.yaml` sets `allow_implicit_invocation: true`; an implicit trigger creates run state and reads quota, which can waste the allowance the skill exists to protect.
- **Evidence:** Codex reads this policy only from `agents/openai.yaml` (default `true`). User config `[[skills.config]] enabled = false` disables a skill entirely; there is no user-level "explicit only" override yet (openai/codex issues #36248, #40874, open). Issue #40600 reports that `false` may also block explicit `$skill` outside the TUI; not reproduced locally (`codex debug prompt-input` does not expand `$skill` for any skill on codex-cli 0.160.1).
- **Confirmed answer (2026-10-26):** repository default becomes `false`. The installer gains `--implicit-invocation on|off` (default `off`) that writes the installed copy's policy, records the choice in the manifest, preserves it on upgrade, and reports it in `doctor --json`. Users must get clear guidance on what the setting does, why it is off by default, the cost of turning it on, and how to change or check it (CLI output, installation reference, both READMEs).
- **Rejected:** only flipping to `false` (no user choice); keeping `true` with an opt-out (misfire risk stays with default users).
- **Consequences:** installed-artifact and managed-setting change; L3 independent final review and compatibility note required. Explicit invocation in Codex Desktop must be verified manually. Affects S01-REQ-4.

## D-04 Model ID duplication (follow-up #10)

- **Question:** model IDs appear in `agents/*.toml`, `delegation.py`, `config_policy.py`, `routing.md` and other sources; AGENTS.md requires explicit, validated model/effort policy.
- **Confirmed answer (2026-10-26):** keep the explicit copies; add a consistency test that fails and names the drifting source.
- **Rejected:** a single generated source (larger change to agent configuration).
- **Consequences:** test only. Affects S01-REQ-5.

## D-05 Non-decisions recorded for scope

- Follow-up #8 (split `SKILL.md` Start step 2) needs no decision: restructure only, no rule change. S01-REQ-3.
- CHANGELOG `[Unreleased]` calls 1.0.0 "published" after the Release was withdrawn to draft; reword. S01-REQ-6.
