# Stage Review — s01-review-followups, batch r02

**Conclusion:** NEEDS_REPAIR
**Delivery granularity:** STAGE_BATCH
**Reviewer agent identity:** codex/01a17910-d4d8-7510-abd0-ba1761eca15e
**Reviewer context identity:** codex/01a17910-d4d8-7510-abd0-ba1761eca15e
**Executor agent identity checked:** codex/94b7691f-669a-43cc-8447-0b3c0529a634
**Executor context identity checked:** codex/94b7691f-669a-43cc-8447-0b3c0529a634
**Fresh context:** VERIFIED
**Fresh-context evidence:** This Codex chat started with repository instructions and the user's Review request, without executor turns or implementation reasoning. The runtime CODEX_THREAD_ID is 01a17910-d4d8-7510-abd0-ba1761eca15e; the handoff records a different executor context. Sources were reconstructed from repository artifacts and Git.
**Implementation participation:** NONE
**Non-participation evidence:** All seven delivery commits already existed at entry, HEAD was the delivery head, and git status --short was empty. This review context has made no implementation, test, specification, contract, acceptance, or Git-history changes. Its only repository write is this review. Identity validation checks self-reported provenance and consistency, not proof of context isolation.
**Independence:** INDEPENDENT
**Review commit authorization:** NOT_AUTHORIZED
**Review commit allowed paths:** docs/implementation/stages/s01-review-followups/stage-review.md
**Review-validity check:** `python3 "/Users/eric/Documents/Vibe Coding/Cross-Agent-Delivery/scripts/validate_independent_review.py" docs/implementation/stages/s01-review-followups/stage-handoff.md docs/implementation/stages/s01-review-followups/stage-review.md` → exit 0 (working-tree pre-commit validation; no review commit authorized or created)
**Review time:** 2026-10-27T00:37:15+08:00
**Current branch:** main
**Worktree:** /Users/eric/Documents/Vibe Coding/Codex-Copilot
**Batch baseline reviewed:** f9057ce5d021a226b15586aa851eb1544cc8a161
**Implementation head reviewed:** 06177bd939a60790eff04c5d0643b17316a5d281
**Handoff commit resolved from path:** 4a9f93c733cd9a22b71cee13cdbdb5b174ba8afe
**Handoff parent verified:** PASS
**Handoff paths verified:** PASS
**Delivery head reviewed:** 4a9f93c733cd9a22b71cee13cdbdb5b174ba8afe
**Accepted dirty/untracked manifest verified:** PASS
**Batch units reviewed:** U1, U2, U3, U4, U5, U6
**Repair route:** COMPLEX_REPAIR_PLAN

## Authority and scope

Read AGENTS.md, CONTRIBUTING.md, docs/compatibility.md, docs/releasing.md,
docs/decisions/confirmed-decisions.md (D-01–D-05), implementation index, the frozen
stage suite, and stage-handoff.md. Reviewed all 17 implementation paths and the
handoff-only delivery commit. The manifest/index still describe the pre-execution
READY state; the committed handoff and actual commit chain establish Review as
the next role. No acceptance/index state was advanced.

Responsibility owner: independent stage reviewer. Interfaces examined: execution
reservation authorization, installer transactions and manifest compatibility,
CLI flags/diagnostics, and Skill guidance. Exclusions: implementation repair,
actual user installation, configuration/PATH changes, release, push, branch or
worktree operations, and manual M-01 completion.

Standards and specification checks were performed by this primary reviewer.
No child was dispatched: CONTRIBUTING requires the Copilot delegation gate,
and this review did not establish a gated delegation run. There was no live
quota read, measurement start, or additional telemetry.

## Reviewer capability refresh

| Capability | State | Evidence/source and time | Limits/fallback |
|---|---|---|---|
| Repository, Git and Skill reads | available | Actual branch, full SHAs, path history, complete diff and clean entry status inspected in this context on 2026-10-27 | Same-platform independence is supported by distinct context identity and non-participation evidence |
| Python checks | available | Python 3.14.6, macOS; G1–G4 independently run | Windows/Linux and Python 3.11–3.13 not executed here; CI remains the platform verifier |
| Isolated installer experiments | available | All five overrides from tests.test_installer.InstallerTests.environment; actual installed launcher subprocess tested from a temporary cwd | Temporary state only; no persistent user PATH or user installation changes |
| Scoped review artifact write | available | Only this stage-review.md added | No implementation ownership |
| Review commit and other Git mutations | restricted | Handoff says NOT_AUTHORIZED; user requested Review without a separate commit grant | Preserve uncommitted report; no post-commit validity claim |
| Desktop restart and explicit invocation M-01 | unverified | No actual install/restart or new-chat invocation performed | Repository owner retains M-01; stage cannot become ACCEPTED before completion |

## Evidence independently run

All commands below ran from the repository root unless a temporary cwd is stated.

| Command/check | Exit/result |
|---|---|
| `git status --short`; `git branch --show-current`; `git rev-parse HEAD HEAD^` | exit 0; clean entry, main, delivery head and implementation parent match the fields above |
| `git log -n 1 --format=%H -- docs/implementation/stages/s01-review-followups/stage-handoff.md` | exit 0; resolves the exact delivery head |
| `git diff-tree --no-commit-id --name-status -r 4a9f93c733cd9a22b71cee13cdbdb5b174ba8afe` | exit 0; only stage-handoff.md added |
| `git log --format='%H %P %s' f9057ce..HEAD`; full `git diff f9057ce 06177bd` | exit 0; six semantic unit commits in order, then the direct-child handoff; each unit stays within its allowed paths |
| G1: `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest discover -s tests -v` | exit 0; 205 tests, OK (skipped=7), 6.011 seconds; all seven skips are Windows-only; symlink checks ran |
| G2: `python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skill/codex-copilot` | exit 0; Skill is valid! |
| G3: `python3 scripts/check_release.py` | exit 0; Release metadata valid: 1.1.0 |
| G4: `git diff --check f9057ce5d021a226b15586aa851eb1544cc8a161 06177bd939a60790eff04c5d0643b17316a5d281` | exit 0; no whitespace errors |
| `python3 "/Users/eric/Documents/Vibe Coding/Cross-Agent-Delivery/scripts/validate_stage_batch.py" docs/implementation/stages/s01-review-followups/README.md docs/implementation/stages/s01-review-followups/execution-plan.md` | exit 0; structure and eligibility pass |
| Independent extraction/comparison of test_band_boundaries from baseline and current tests/test_routing.py | exit 0; existing boundary test unchanged |
| Independent reservation permission matrix described below | exit 0; 200 combinations pass |
| Actual installed-launcher reproduction below | reproduction exit 0; both attempted setting changes return CLI exit 1; manifest preserved |

The permission matrix used the existing isolated ExecutionTests helpers, without
native dispatch. For each L1/L2/L3 × balanced/conservative/premium configuration
(including L3 premium Astra and Sol fallback), it completed a first Green review
with a bound session. It then tried each of Green/Yellow/Red/Critical/Unknown ×
fresh/follow-up × no-grant/scoped-grant in a new isolated run. Expected admission
was a valid grant, or a follow-up permitted by the unchanged role/band/cumulative
policy. All 200 cases matched. The full suite additionally verifies unresolved
sessions, invalid scope/identity, total-call limits, investigator→final→follow-up
denial, and legacy recovered consumption.

Representative local manifest was inspected read-only for shape only: schema 2,
version 1.1.0, copy mode, seven managed configuration changes, artifact kinds
agent/distribution/executable/runtime/skill, and no implicit_invocation field.
This matches the legacy-without-field migration case. No local artifact/config
contents or user paths were copied into this report. Existing 0.1.0/0.1.1 fixture
migrations and isolated legacy policy migration/rollback tests passed in G1.

## Scope and requirement verdicts

Boundary integrity, file ownership, and unchanged prohibited paths: PASS. The
accepted pre-existing U1 test patch was included in U1 as planned; delivery status
was clean at entry. No acceptance criteria or authority were weakened. VERSION,
agents/*.toml, delegation.py, config_policy.py, known_skills.py and
docs/verification.md are unchanged.

| Requirement | Verdict | Evidence |
|---|---|---|
| S01-REQ-1 | PASS | Exact new fresh-review gate/message; 200-case matrix; cumulative-budget, follow-up, grant and legacy controls pass; routing/compatibility guidance agrees |
| S01-REQ-2 | PASS | Single-window 60/30/10 thresholds documented; six fractional/boundary cases pass; old boundary test and routing implementation unchanged |
| S01-REQ-3 | PASS | Original Start step 2 rules map to new steps 2–5: installation states/PATH, conditional installation reference/degraded continuation/request-only changes, status/profile/quota recovery, model choice; later steps renumbered; validator passes |
| S01-REQ-4 | FAIL | Source-call tests cover defaults, opt-in, upgrade preservation, legacy migration, token binding, doctor, symlink rejection and rollback; documented installed-CLI switch fails in both directions (F-01) |
| S01-REQ-5 | PASS | Consistency test covers every declared role/model/effort, default scout model and literal documented IDs; full suite passes; recorded executor scratch negative control inspected |
| S01-REQ-6 | PASS | Unreleased wording and required three entries present; release metadata valid; VERSION unchanged |

Manual M-01 remains PENDING. The validation plan explicitly permits code Review
before M-01, but forbids advancing the stage to ACCEPTED until it is COMPLETE.

## Findings

### F-01 / P1 — The documented setting switch fails through the installed launcher

- Requirement/rule: S01-REQ-4 promises `codex-copilot install
  --implicit-invocation {on,off}` as the setting switch; the notice, README files
  and installation reference advertise that command. Existing transactional and
  source-overlap protections must remain intact.
- Evidence: src/codex_copilot/installer.py:232–233 makes current-install detection
  false on a setting change. Lines 418–422 then treat that change as a distribution
  upgrade and reject source==destination. bin/codex-copilot loads the installed
  runtime from its pointer, so repo_root() is the copied distribution for the
  advertised PATH command. Existing tests call the source import or source main
  directly, bypassing this bootstrap.
- Reproduction: after a fresh copy install with off, executing the installed
  launcher with `install --implicit-invocation on --yes` exits 1 with
  `error: Copy-mode upgrades must run from a source checkout outside the installed copy`.
  Starting with on and requesting off fails identically. Merely changing cwd to
  the checkout does not change which runtime the installed launcher imports.
- Impact: users cannot enable or disable implicit invocation through the
  advertised command. In particular, an opted-in user cannot turn it off that
  way. Both failures preserve the installed manifest, so this is a required
  interface failure, not observed data loss.
- Minimal repair boundary: plan a transaction-safe way for the installed CLI to
  perform a setting-only change, or resolve an explicitly approved source-command
  interface and correct all instructions. Preserve the existing guard against
  copying an installed distribution over itself; do not simply delete it. Add
  subprocess regressions using the actual installed launcher, cleared PYTHONPATH,
  and all five isolated path overrides, for both directions and confirmation/
  rollback behavior. Do not change quota, role policy, model permissions or PATH.
- Route: COMPLEX_REPAIR_PLAN because the correction touches installation behavior;
  it does not qualify for the low-risk self-repair exception.

Reproduction command (exit 0 means the defect was reproduced, not repaired):

```bash
PYTHONPATH=src python3 - <<'PY'
import os, subprocess, sys, tempfile
from pathlib import Path
from unittest.mock import patch
from tests.test_installer import InstallerTests
from codex_copilot.installer import install, load_manifest

with tempfile.TemporaryDirectory(prefix='s01-review-installed-') as tmp:
    with patch.dict(os.environ, InstallerTests().environment(tmp)):
        launcher = Path(os.environ['CODEX_COPILOT_BIN_DIR']) / 'codex-copilot'
        for initial, desired in [('off', 'on'), ('on', 'off')]:
            install(implicit_invocation=initial)
            manifest = Path(os.environ['CODEX_COPILOT_STATE_DIR']) / 'install.json'
            before = manifest.read_bytes()
            child_env = dict(os.environ)
            child_env.pop('PYTHONPATH', None)
            result = subprocess.run(
                [sys.executable, str(launcher), 'install',
                 '--implicit-invocation', desired, '--yes'],
                env=child_env, cwd=tmp, capture_output=True, text=True)
            print(initial + '-to-' + desired, result.returncode,
                  result.stderr.strip())
            assert result.returncode == 1
            assert 'source checkout outside the installed copy' in result.stderr
            assert manifest.read_bytes() == before
            assert load_manifest()['implicit_invocation'] == initial
print('Both installed-launcher failures reproduced; state preserved.')
PY
```

The first diagnostic harness assumed error exit 2 and stopped after the first
off→on observation. Inspection showed the CLI uses exit 1 for InstallError; the
corrected harness above independently completed both directions. This was a
review-harness assertion correction, not an additional product failure.

## P2 backlog

None. No additional documented-standards violation was identified independently
of F-01. No heuristic code-smell preference is treated as a required repair.

## Next route

Use cross-agent-delivery in Plan mode to create repair-contract.md for F-01.
Do not repair implementation in this Review context. Review commit is not
authorized; this report remains uncommitted. A later authorized review commit
must be a direct child of the delivery head, contain only the allowed review
path, and pass the validator again after commit. Preserve the reviewed delivery
head and do not advance evidence/index acceptance states.
