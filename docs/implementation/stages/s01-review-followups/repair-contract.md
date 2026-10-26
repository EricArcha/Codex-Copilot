# S01-R01 — Installed launcher implicit-invocation setting repair

**Status:** READY
**Packet type:** REPAIR
**Stage:** s01-review-followups, [README.md](README.md)
**Parent suite:** [spec.md](spec.md), [execution-plan.md](execution-plan.md), [validation-plan.md](validation-plan.md), [evidence-matrix.md](evidence-matrix.md)
**Source finding:** [stage-review.md](stage-review.md), F-01 / P1, COMPLEX_REPAIR_PLAN
**Planner:** codex/01a17938-a39d-7bb3-8dba-66bf2c51e4bb (agent and context identity)
**Executor:** UNASSIGNED
**Independent reviewer:** REQUIRED_DIFFERENT_AGENT_BEFORE_ACCEPT (L3)
**Baseline:** 88ff1c44d5d70e6b715e3b80c7ba7678adf2d193 (source/review parent; resolve the planning commit by path history below)
**Current branch/worktree:** main; /Users/eric/Documents/Vibe Coding/Codex-Copilot
**Dependencies accepted:** none; this packet repairs the exact NEEDS_REPAIR delivery 4a9f93c733cd9a22b71cee13cdbdb5b174ba8afe, not an accepted dependency
**Accepted baseline changes:** entry contained only untracked tests/test_installed_launcher.py; preserved byte-for-byte, SHA256 92795bdf36db33b3dcc73e5a4dedb1eed7ce2ae466721ab80cec06de5ef6eed2. Its header attributes prior experiments to a Claude Code planning session; those claims are not inherited as evidence. This planner added tests/test_installed_launcher_safety.py and the three documentation paths in the planning allowlist below. No production edits.
**Planned capability check:** 2026-10-27 Asia/Shanghai; local Git, Python, Skill/reference reads and scoped writes available; eight real-launcher subprocess tests independently run with five temporary path overrides. Windows/Linux unverified. Future executor capabilities UNVERIFIED.
**Decision readiness:** READY; D-03 and S01-REQ-4 already require the existing CLI setting switch. No new interface, schema or product choice.
**Companion route:** grilling and domain-modeling not required; no new decision or domain boundary. No skill/provider artifact edits and no unexplained failure; no other companion required. No subagent dispatch.
**Plan readiness check:** `python3 '/Users/eric/Documents/Vibe Coding/Cross-Agent-Delivery/scripts/validate_ready_contract.py' docs/implementation/stages/s01-review-followups/repair-contract.md` → exit 0 (2026-10-27; recheck after planning commit).
**Acceptance baseline check:** `PYTHONDONTWRITEBYTECODE=1 python3 '/Users/eric/Documents/Vibe Coding/Cross-Agent-Delivery/scripts/validate_acceptance.py' --baseline docs/implementation/stages/s01-review-followups/repair-contract.md` → exit 0 (2026-10-27; all nine rows match). Every unittest command unsets PYTHONDONTWRITEBYTECODE; recheck after planning commit.

## Goal

Make the documented installed `codex-copilot install --implicit-invocation on|off`
command switch the current copy installation's setting in both directions, with
normal confirmation and rollback, without treating it as a distribution upgrade.

## Ordered sources of truth

1. AGENTS.md, CONTRIBUTING.md, docs/compatibility.md and docs/releasing.md.
2. docs/decisions/confirmed-decisions.md, D-03.
3. [spec.md](spec.md), S01-REQ-4 and Invariants; all other requirements stay frozen.
4. [stage-review.md](stage-review.md), F-01, at exact reviewed implementation 06177bd939a60790eff04c5d0643b17316a5d281 and delivery 4a9f93c733cd9a22b71cee13cdbdb5b174ba8afe.
5. [validation-plan.md](validation-plan.md), S01-REQ-4, final gates, Independent Review and M-01; this contract supplies the bounded repair execution and locked tests.

The original delivery and review remain immutable history. The old index/manifest
READY execution route is superseded by this repair route only. No parent behavior
or acceptance rule is relaxed.

## Requirements and acceptance

| ID | Requirement (one line) | Acceptance test IDs | Manual check and verifier |
|---|---|---|---|
| REQ-F01-SWITCH | S01-REQ-4 / F-01: installed launcher switches off→on and on→off, preserves source/distribution and valid artifact fingerprints | A01, A02 | Independent L3 reviewer checks setting-only write scope |
| REQ-F01-CONFIRM | S01-REQ-4: dry-run and unconfirmed plan are non-mutating; same setting remains idempotent | A03, A04, A06, R01 | None |
| REQ-F01-SAFETY | S01-REQ-4 / F-01: malformed policy and partial manifest-write failure preserve prior state; real upgrades retain overlap guard | A05, A07, A08, R01 | Independent L3 reviewer checks eligibility, token binding, transaction and unknown-file protection |

| Test ID | Requirement IDs | Command | Baseline expectation (FAIL/PASS) | Locked paths |
|---|---|---|---|---|
| A01 | REQ-F01-SWITCH | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_installed_launcher.InstalledLauncherSettingTests.test_a01_installed_launcher_turns_implicit_invocation_on` | FAIL | tests/test_installed_launcher.py |
| A02 | REQ-F01-SWITCH | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_installed_launcher.InstalledLauncherSettingTests.test_a02_installed_launcher_turns_implicit_invocation_off` | FAIL | tests/test_installed_launcher.py |
| A03 | REQ-F01-CONFIRM | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_installed_launcher.InstalledLauncherSettingTests.test_a03_dry_run_previews_setting_only_change` | FAIL | tests/test_installed_launcher.py |
| A04 | REQ-F01-CONFIRM | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_installed_launcher.InstalledLauncherSettingTests.test_a04_unconfirmed_setting_change_shows_plan_and_changes_nothing` | FAIL | tests/test_installed_launcher.py |
| A05 | REQ-F01-SAFETY | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_installed_launcher.InstalledLauncherSettingTests.test_a05_invalid_installed_policy_rolls_back_setting_change` | FAIL | tests/test_installed_launcher.py |
| A06 | REQ-F01-CONFIRM | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_installed_launcher.InstalledLauncherSettingTests.test_a06_same_setting_is_already_installed` | PASS | tests/test_installed_launcher.py |
| A07 | REQ-F01-SAFETY | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_installed_launcher.InstalledLauncherSettingTests.test_a07_upgrade_from_installed_copy_is_still_refused` | PASS | tests/test_installed_launcher.py |
| A08 | REQ-F01-SAFETY | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_installed_launcher_safety` | FAIL | tests/test_installed_launcher_safety.py, tests/test_installed_launcher.py |
| R01 | REQ-F01-CONFIRM, REQ-F01-SAFETY | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_installer tests.test_cli tests.test_native tests.test_diagnostics` | PASS | tests/test_installer.py, tests/test_cli.py, tests/test_native.py, tests/test_diagnostics.py, tests/platform_support.py |

### Baseline evidence (2026-10-27)

- `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_installed_launcher tests.test_installed_launcher_safety -v`: exit 1; 8 tests, 6 failures (A01–A05 and A08); A06/A07 pass. All six failures encounter the existing source-checkout guard before setting mutation. A08 asserts the injected failure message after policy write, so an early rejection cannot masquerade as successful rollback.
- Full required discovery: exit 1; 213 tests, the same 6 failures, 7 Windows-only skips. No other failure/error. No symlink privilege/copy-mode/business failures skipped.
- Skill validator: exit 0, `Skill is valid!`; release check: exit 0, `Release metadata valid: 1.1.0`; `git diff --check`: exit 0 before planning documentation edits.
- `validate_independent_review.py` against the original stage handoff/review: exit 0 at committed review HEAD. Review commit direct parent and sole review path inspected.
- R01 independently run: exit 0, 92 tests, 7 Windows-only skips. Final planning `git diff --check`: exit 0. The existing acceptance file's SHA256 was rechecked unchanged.
- Initial pre-authorization checks were blocked by untracked tests and the BLOCKED contract state. After the user authorized the scoped planning commit and requested environment normalization, the tests were staged and all unittest commands gained `env -u PYTHONDONTWRITEBYTECODE`. Formal baseline validation with outer PYTHONDONTWRITEBYTECODE=1 exited 0: A01–A05/A08 FAIL; A06/A07/R01 PASS. Revised full discovery: 213 tests, the same six F-01 failures and seven Windows-only skips; exit 1 as expected. Readiness validation exits 0. No implementation changes or acceptance weakening.
- Supplemental logs: /tmp/s01-f01-acceptance-baseline.log and /tmp/s01-f01-full-baseline.log. Relevant results are persisted here; logs are not required for handoff.

## Locked decisions and interfaces

Keep `installer.install(implicit_invocation: str | None = None)` and the existing
CLI flags/exit codes. A setting-only update is eligible only for an otherwise
current, intact managed copy install at the existing targets, with valid required
configuration, unchanged source/distribution content and no requested PATH change.
Use current-install integrity checks against the recorded setting to distinguish
this from an upgrade; a missing legacy field, mode/version/source difference,
modified artifact, required configuration repair or target relocation must not
qualify. Preserve the existing real-upgrade overlap guard. `_is_current_install`
must still be false for the newly requested differing setting as specified by
S01-REQ-4; separate eligibility checking may use the recorded choice.

The setting-only plan includes the exact action `set implicit invocation: on` or
`set implicit invocation: off`. Preserve notices, dry-run, no-op and confirmation
semantics. Bind the token to requested choice and inspected state and recheck it
before mutation. Reuse managed transaction/backup machinery; validate exactly one
policy line at the recorded value, write only the installed policy and manifest,
refresh the Skill fingerprint, preserve other manifest ownership/recovery metadata,
and restore both files on failure. Backup/recovery journals are permitted inside
the isolated managed state directory. No distribution rewrite, new schema/CLI,
quota read, PATH write or Codex configuration rewrite in this setting-only path.
Local private-helper structure is the executor's implementation choice.

## Scope and ownership

- Allowed paths: executor implementation `src/codex_copilot/installer.py`; additive executor tests `tests/test_installer_setting_change.py` if needed for token/eligibility edge cases; `CHANGELOG.md` for the compatible F-01 fix note; evidence output `docs/implementation/stages/s01-review-followups/handoff-r01.md` only. No other implementation/test/doc edits.
- Prohibited paths: all locked acceptance/regression paths above; all other `src/`, `tests/`, `skill/`, `agents/`, `bin/`, `VERSION`, `pyproject.toml`, historical fixtures, `known_skills.py`, `docs/verification.md`, governance, original handoff/review and frozen suite. Do not edit this contract or the acceptance criteria during Execute.
- Read-only sources: ordered sources above; `src/codex_copilot/cli.py`, `src/codex_copilot/paths.py`, `bin/codex-copilot`, `bin/codex-copilot.py`, and existing installer tests.
- Interface owner: installer; CLI/bootstrap public interface unchanged. One writer; no parallel implementation. New optional executor test file belongs to installer regression verification for the current F-01 requirement only.
- Non-goals: release/version bump, real user install, M-01 completion, pushes, branch/worktree changes, delegation/model/quota/metrics changes. No external write.

### Planning commit allowlist and baseline lock

Only these five paths belong in the requested planning commit:
`docs/implementation/README.md`,
`docs/implementation/stages/s01-review-followups/README.md`,
`docs/implementation/stages/s01-review-followups/repair-contract.md`,
`tests/test_installed_launcher.py`, `tests/test_installed_launcher_safety.py`.
Planning commit authority is AUTHORIZED by the current user on 2026-10-27: revise all unittest commands to unset PYTHONDONTWRITEBYTECODE, rerun baseline expectations, then commit only these five paths on main without pushing. Implementation/handoff/review commits are not included in that planning-only Git grant.

Planning authorization is granted and the staged baseline/readiness checks pass. Commit only the allowlist as a direct child of the source/review parent above, then rerun both validators against the committed planning baseline. If either fails, do not dispatch Execute. No implementation is included. The current user also requested completion of F-01; this authorizes bounded implementation and verification after this planning boundary, but grants no additional Git commit, push or branch authority.

The executor resolves the final planning baseline with
`git log -n 1 --format=%H -- docs/implementation/stages/s01-review-followups/repair-contract.md`,
requires its direct parent to equal the Baseline field above, and verifies the
planning commit contains only the five allowed paths, with no production change.
Record the resolved full SHA in the handshake and use it for the delivery
acceptance check. Entry status must be clean; any new dirty state or baseline
drift returns to Plan. This path-history resolution avoids a self-referential SHA.

## Runtime capability handshake

| Capability | Required for | Required state | Evidence to record | Fallback |
|---|---|---|---|---|
| Skill, repository and Git access | Exact baseline and ownership | available | New platform/context identity, branch/worktree, HEAD, status, planning parent and path checks with timestamp | BLOCKED |
| Python 3.11+ and subprocesses | Locked acceptance and existing tests | available | Python/OS, independent baseline results, all five overrides, cleared child PYTHONPATH | BLOCKED; no real-user install substitute |
| Scoped installer/test/evidence writes | Repair | available | Exact allowlist and preserved unrelated state | BLOCKED |
| Git mutations | Authorized commits only | restricted until user grant | Separate implementation/handoff/review/push/branch authorities | Leave changes uncommitted; cannot claim committed delivery |
| Independent L3 review | Installation acceptance | unverified at planning | Different fresh context and no implementation participation; validity check | Stop at REVIEW_READY |
| Desktop manual M-01 | Eventual stage acceptance | unverified | Repository owner evidence under parent validation plan | Keep M-01 PENDING; code review may proceed |

All future runtime capabilities begin UNVERIFIED. Record a fresh handshake after
execution confirmation and before any implementation edit. No permission is
inherited from prior batch/session grants.

## Execution and verification

1. Pass execution-confirmation.md, resolve and verify the committed planning baseline, clean status, locked test digest and ownership. Run the acceptance baseline check; its FAIL/PASS expectations must match. Existing final G1 intentionally has six new red tests before repair, not six waived delivery failures.
2. Implement the bounded setting-only transaction in installer.py; add focused edge-case tests in the one permitted executor test file if necessary. Include a user-facing CHANGELOG fix note. Do not modify locked tests to make them green.
3. Run `python3 '/Users/eric/Documents/Vibe Coding/Cross-Agent-Delivery/scripts/validate_acceptance.py' --delivery docs/implementation/stages/s01-review-followups/repair-contract.md --baseline-sha "$S01_REPAIR_BASELINE"`, where S01_REPAIR_BASELINE is the verified full planning commit SHA. All rows must PASS, locked paths unchanged and clean. Independently verify stale-token rejection and refusal of modified/config-incomplete installs; do not bypass checks to enable a setting change.
4. Run final gates: `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest discover -s tests -v`; `python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skill/codex-copilot`; `python3 scripts/check_release.py`; `git diff --check "$S01_REPAIR_BASELINE" HEAD` plus `git diff --check` for pending edits. All exit 0. Probe symlinks; only platform/privilege skips permitted, never copy/business failures. Use all five overrides, temporary installs and no persistent PATH change.
5. Append authorized implementation and evidence commits, capture exact implementation/delivery heads and final evidence in the new handoff, and stop at REVIEW_READY. The handoff/evidence commit must directly follow implementation head and contain only handoff-r01.md. No self-ACCEPT.

- Internal implementation commits: UNVERIFIED; request one scoped repair commit at Execute confirmation.
- Handoff/evidence commit: UNVERIFIED; request separately at Execute confirmation.
- Review commit: NOT_AUTHORIZED; future reviewer verifies separate authority.
- Push: NOT_AUTHORIZED.
- Branch/worktree operations: NOT_AUTHORIZED; stay on main in the existing worktree. Release workflow remains outside this repair packet.
- History rewrite: NOT_AUTHORIZED. Preserve original delivery/review and planning commits.
- Rollback boundary: one appended repair implementation commit, reverted only with separate authority; temporary experiments leave no persistent installation. Do not delete or rewrite prior evidence.

## Handoff and next role

- Initial handoff path: `docs/implementation/stages/s01-review-followups/handoff-r01.md` (must not already exist).
- Initial review path: `docs/implementation/stages/s01-review-followups/review-r01.md` (must not already exist).
- Required evidence: actual planning/implementation/delivery SHAs and parents, branch/worktree/status, changed paths, separate Git authorities, runtime handshake, commands/exit codes, locked-test delivery result, requirement mapping, partial-failure rollback, token/eligibility controls, unknown-file preservation, remaining manual/platform gaps and rollback boundary.
- Next legal role after REVIEW_READY: fresh independent L3 Review of the repair range and preserved stage invariants, acceptance delivery check and `validate_independent_review.py` against the matched repair handoff/review pair. Original F-01 remains NEEDS_REPAIR until independently verified. M-01 remains PENDING; do not mark the stage ACCEPTED.
- Stop and report `BLOCKED` on: missing planning commit/authority; unexpected baseline/status/path/digest drift; changed locked tests; readiness/baseline/delivery mismatch; failure of final gates; need for a new interface/schema/decision or path outside the allowlist; inability to preserve transaction/unknown-file/self-copy protection; unavailable required capability or independent reviewer. Return to Plan rather than broadening this contract.
