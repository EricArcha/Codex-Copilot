# S01 validation plan

**State:** FROZEN
**Stage:** s01-review-followups
**Authority:** [spec.md](spec.md)
**Last governed baseline:** 720a881589aa9eb18ef5abca241520b24fd6f850

## Required regression tests (written by the executor)

| Requirement | Tests that must exist and pass |
|---|---|
| S01-REQ-1 | L3 Green balanced: final review then a fresh final review is denied with the new message; final review then a follow-up of that session is allowed; investigator then final review still allowed. L1/L2 Green: reviewer then a fresh reviewer is denied; reviewer then its follow-up is allowed. A valid grant authorizes a second fresh reviewer. |
| S01-REQ-2 | Boundary assertions 60/59.9/30/29.9/10/9.9 on `band_for_remaining`, plus a check that `routing.md` states the single-window 60/30/10 thresholds. |
| S01-REQ-4 | Fresh copy install defaults to `off` (installed policy `false`, manifest `off`); `--implicit-invocation on` writes `true` only in the installed copy and records `on`; a later install without the flag preserves `on`; switching value is not "Already installed"; legacy manifest upgrades to `off` with the legacy notice; symlink mode with `on` raises `InstallError`; dry-run actions show the setting; `doctor --json` reports `on`/`off`/`unknown`; a missing or duplicated policy line raises and rolls back. |
| S01-REQ-5 | The consistency test, plus evidence that it fails when one `agents/*.toml` model is altered in a scratch copy (record the command and output; do not commit the alteration). |

Each new behavioral test for S01-REQ-1 and S01-REQ-4 must fail on the batch baseline; record that evidence in the handoff.

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
| M-01 | After installing with default `off` and restarting Codex Desktop, typing `$codex-copilot` in a new task loads the skill (D-03 explicit-invocation risk, openai/codex#40600) | repository owner | PENDING |

M-01 does not block `ACCEPT` of the code change, but the stage cannot be marked `ACCEPTED` until M-01 is `COMPLETE`. If M-01 fails, return to Discover for D-03.
