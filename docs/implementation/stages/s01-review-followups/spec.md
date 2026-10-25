# S01 spec — review follow-ups

**State:** FROZEN
**Stage:** s01-review-followups
**Authority:** [confirmed-decisions.md](../../../decisions/confirmed-decisions.md) D-01 to D-05; AGENTS.md change fences
**Last governed baseline:** 720a881589aa9eb18ef5abca241520b24fd6f850

## Requirements

### S01-REQ-1 One final-review session per run (D-01)

- In `execution.py`, where the subagent role gate is evaluated (the `_allow_role(...)` call in the reservation path), add: when `kind == "subagent"`, `phase == "final_review"`, the request is not a follow-up (`parent is None`), and `data["calls"]` already contains a call with `kind == "subagent"` and `phase == "final_review"`, the request is not allowed.
- A follow-up (`followup_id` bound to that reviewer session) stays allowed when the existing cumulative budget allows it. Existing follow-up identity checks are unchanged.
- A valid bounded user grant still authorizes the request, exactly as grants work today.
- Without a grant, raise `ExecutionDenied("This run already used its final-review session; recheck with a follow-up of that reviewer session or obtain a bounded user grant")`.
- Do not change `delegation._allow_role` counting, band rules, role/phase validation, or any other band's behavior. Legacy runs (`legacy_consumed`) keep their current limits.
- Docs: `skill/codex-copilot/references/routing.md` Green row and the Green/standard L3 paragraph state that the second slot after a final review may only be a follow-up recheck of that reviewer session. `skill/codex-copilot/SKILL.md` recheck guidance names the follow-up mechanism.

### S01-REQ-2 Single-window thresholds documented (D-02)

- `routing.md`, directly below the band table, adds: when only one quota window is reported, Green ≥60%, Yellow 30–59%, Red 10–29%, Critical under 10% or reached.
- Thresholds in `routing.band_for_remaining` are unchanged.

### S01-REQ-3 SKILL.md Start step 2 split (follow-up #8)

- Replace Start step 2 with three or four short numbered steps: (a) find the launcher and run `doctor --json`, with what each `installation_state` means and that missing PATH alone is not Skill-only; (b) when unavailable, state degraded mode once, continue, install or change configuration only on request, and use `installation.md`; (c) for a complete workflow, read `status --json` and `profile show` (balanced default), use `quota.md` for permission/state failures, and take the unknown route when unresolved; (d) model choice in one line.
- Every rule in the current step 2 survives, either in a new step or as an existing statement in `installation.md` / `quota.md`. No new rule, no reference becomes mandatory for every task. Renumber later steps.

### S01-REQ-4 Implicit invocation off by default with installer switch (D-03)

- `skill/codex-copilot/agents/openai.yaml` sets `allow_implicit_invocation: false`.
- CLI: `codex-copilot install --implicit-invocation {on,off}`; no default value at the argparse level.
- Resolution: the flag when given; else the current manifest's `implicit_invocation`; else `off`.
- Copy mode with `on`: after placing the skill target and before fingerprinting it, rewrite the single line `  allow_implicit_invocation: false` in the installed `agents/openai.yaml` to `true`. If that line does not occur exactly once, raise `InstallError` and roll back. The repository source and the copied distribution are never modified.
- Symlink mode with `on`: raise `InstallError` explaining that symlink installs use the repository default (`off`) and that copy mode is required to enable it.
- Manifest gains `"implicit_invocation": "on" | "off"`. `load_manifest` accepts manifests without the field (legacy) and rejects any other value.
- `_is_current_install` is false when the resolved value differs from the manifest value, so changing the setting produces a reviewable plan.
- Plan actions include `set implicit invocation: <on|off>`; the plan token therefore covers the choice.
- Install output (dry run and real) always includes one notice explaining: explicit invocation is `$codex-copilot`; with `on`, Codex may start the skill by itself, which loads its instructions and can read quota and create run state; the default is `off` to avoid spending allowance on misfires; how to change it (`install --implicit-invocation on|off`, then restart Codex Desktop) and check it (`doctor --json`).
- Upgrading a legacy manifest (no field) adds a second notice: the previous release allowed implicit invocation; this upgrade turns it off unless `--implicit-invocation on` is given.
- `doctor --json` adds top-level `"implicit_invocation"`: `"on"`, `"off"`, or `"unknown"` when no manifest or the field is missing.
- Docs: `references/installation.md` (Install or upgrade section), `README.md` ("Want the full cockpit?") and `README.zh-CN.md` ("想开启完整驾驶舱？") explain the setting with the same content as the notice; `docs/compatibility.md` "User data and upgrades" records default `off`, preservation on upgrade, and legacy installs switching to `off` with a notice.

### S01-REQ-5 Model/effort consistency test (D-04)

- Add a test in `tests/test_delegation.py` that, for every role in `delegation._ROLE_CONFIGURATION`, reads `agents/<role with "_" replaced by "-">.toml` with `tomllib` and asserts `model` and `model_reasoning_effort` equal the configured pair; asserts `config_policy` `agents.default_subagent_model` equals the `copilot_scout` model; and asserts `routing.md` mentions every distinct configured model ID. Each failure message names the drifting file and role.

### S01-REQ-6 CHANGELOG (D-05)

- In `[Unreleased]`, change "the published 1.0.0 workflow" to "the 1.0.0 workflow".
- Add `[Unreleased]` entries for S01-REQ-1, S01-REQ-2 and S01-REQ-4 in the file's existing style.

## Invariants

- Python 3.11+ standard library only; Windows, macOS and Linux behavior unchanged except as listed.
- No change to quota acquisition, measurement, metrics privacy, model/effort permissions, or the cumulative delegation budget beyond S01-REQ-1.
- Installer stays transactional: any failure rolls back; unknown or modified user files are never overwritten.

## Non-goals

- Version bump, release, tag, push, or GitHub Release changes.
- `README.md` "Current source version: 1.0.1" heading mismatch with `VERSION` 1.1.0.
- Editing `known_skills.py`, `VERSION`, `agents/*.toml`, `config_policy.py`, `delegation.py`, or `docs/verification.md`.

## Completion

All six requirements pass their acceptance in [validation-plan.md](validation-plan.md), final gates G1–G4 pass at implementation head, and an L3 independent stage Review concludes `ACCEPT`.
