# S01 validation plan

**State:** FROZEN
**Stage:** s01-review-followups
**Authority:** [spec.md](spec.md)
**Last governed baseline:** c540061dc989d6fb6f7c906facd218a99195d444 (revision r02 planning parent)

## Required regression tests (written by the executor)

| Requirement | Tests that must exist and pass |
|---|---|
| S01-REQ-1 | L3 Green balanced: final review then a fresh final review is denied with the new message; final review then a follow-up of that session is allowed; investigator then final review still allowed; investigator → final review → follow-up still denied by the unchanged two-child budget. L1/L2 Green: reviewer then a fresh reviewer is denied; reviewer then its follow-up is allowed. A valid grant authorizes a second fresh reviewer. |
| S01-REQ-2 | Existing `test_band_boundaries` unchanged. New check: `routing.md` states the single-window 60/30/10 thresholds, and `band_for_windows(x, None)` returns the documented band at 60/59.9/30/29.9/10/9.9. |
| S01-REQ-4 | Fresh copy install defaults to `off` (installed policy `false`, manifest `off`); `--implicit-invocation on` writes `true` only in the installed copy and records `on`; a later install without the flag preserves `on`; switching value is not "Already installed"; legacy manifest upgrades to `off` with the legacy notice; symlink mode with `on` raises `InstallError`; dry-run actions show the setting; `doctor --json` reports `on`/`off`/`unknown`; a missing or duplicated policy line raises and rolls back. |
| S01-REQ-5 | The consistency test, plus evidence that it fails when one `agents/*.toml` model is altered in a scratch copy (record the command and output; do not commit the alteration). |

Tests of new behavior must fail on the batch baseline: for S01-REQ-1, the fresh second final-review denials (L3 and L1/L2) and the new message; for S01-REQ-4, every listed installer test. Assertions of unchanged behavior (follow-up allowed, investigator → final → follow-up denied, grant authorizes) are expected to pass on the baseline. Record both in the handoff.

## Final gates

G1–G4 as defined in the [stage manifest](README.md). Skips must remain platform-only (7 on macOS at baseline).

## Independent Review (L3)

AGENTS.md requires L3 independent final review for delegation and installation changes.

- **Reviewer:** a fresh session on a different session identity than the executor, recorded as `<platform>/<session-id>` (intended: `claude-code/...`). Reviewer does not edit implementation.
- **Scope:** full diff from batch baseline to delivery head; permission matrix of S01-REQ-1 (every band × level × follow-up/grant combination touched); installer migration from a legacy manifest, upgrade preservation, rollback on failure, symlink rejection; representative existing data (current user manifest shape); documentation matches behavior.
- **Validity:** run `validate_independent_review.py` before and after the review commit.

## Manual evidence

| ID | Evidence | Owner | Status |
|---|---|---|---|
| M-01 | After installing with default `off` and restarting Codex Desktop, typing `$codex-copilot` in a new task loads the skill (D-03 explicit-invocation risk, openai/codex#40600) | repository owner | COMPLETE |

M-01 evidence (2026-10-28): chat `01a1832b-2dff-7013-b540-2c054c288bca`
records successful `codex-copilot install --implicit-invocation off --yes`
and the owner's report that Desktop had been restarted. Restart is owner-reported,
not independently observed. In new chat `01a1832e-a6a4-7ec2-bfbf-e9da31626baf`,
the owner explicitly selected `$codex-copilot`; Desktop supplied the installed
SKILL.md content and the workflow loaded successfully. `doctor --json` in that
chat reports `installation_state: complete`, `implicit_invocation: off`, and
matching managed artifacts. This verifies explicit invocation while off; it does
not test automatic skill selection while on. The installer default-off behavior
is covered separately by the required regression tests. Stage acceptance/index
updates remain separate from this manual-evidence record.

M-01 does not block `ACCEPT` of the code change, but the stage cannot be marked `ACCEPTED` until M-01 is `COMPLETE`. If M-01 fails, return to Discover for D-03.
