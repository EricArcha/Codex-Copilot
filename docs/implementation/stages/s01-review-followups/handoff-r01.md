# Handoff — S01-R01 installed launcher setting repair

**Result:** REVIEW_READY
**Executor agent identity:** codex/01a17938-a39d-7bb3-8dba-66bf2c51e4bb
**Executor context identity:** codex/01a17938-a39d-7bb3-8dba-66bf2c51e4bb
**Required reviewer:** DIFFERENT_AGENT_REQUIRED (L3)
**Contract:** docs/implementation/stages/s01-review-followups/repair-contract.md
**Contract baseline:** dd81f8710508ec01aaa2e5a9e8dc38f0ca24f339
**Actual base/head:** dd81f8710508ec01aaa2e5a9e8dc38f0ca24f339...2a2366dec9a4c88347f85fd8f09129be499db9a4
**Implementation head:** 2a2366dec9a4c88347f85fd8f09129be499db9a4
**Expected handoff parent:** 2a2366dec9a4c88347f85fd8f09129be499db9a4
**Handoff/evidence allowed paths:** docs/implementation/stages/s01-review-followups/handoff-r01.md
**Review commit allowed paths:** docs/implementation/stages/s01-review-followups/review-r01.md
**User execution confirmation:** In this parent chat, after the repair contract was displayed, the user requested environment-normalized tests and stated: `授权规划提交，只提交合同列出的 5 个文件到当前 main，不推送。` followed by `并且把 F-01 跑完。` The latter authorizes bounded F-01 implementation/verification. The explicit five-file Git grant covered planning only. In a later direct human response to the displayed three-class Git request, the user selected exactly `授权实现、交接和独立审查提交`. This later grant covers one three-file implementation commit, this handoff-only commit and the independent review-only commit on current main, with no push/history rewrite. A reviewer can verify the direct human response through read_thread for thread 01a17938-a39d-7bb3-8dba-66bf2c51e4bb rather than rely on this paraphrase.
**Working directory/worktree:** /Users/eric/Documents/Vibe Coding/Codex-Copilot; main
**Commit status:** planning commit dd81f8710508ec01aaa2e5a9e8dc38f0ca24f339; repair implementation 2a2366dec9a4c88347f85fd8f09129be499db9a4; this handoff is the only path allowed in its direct-child evidence commit (resolve its SHA from path history).
**Git authorization:** planning five-file commit AUTHORIZED and complete; implementation commit AUTHORIZED and complete; handoff/evidence commit AUTHORIZED; review commit AUTHORIZED (reviewer verifies direct human source); push NOT_AUTHORIZED; branch/worktree operations NOT_AUTHORIZED; history rewriting NOT_AUTHORIZED
**Handoff time:** 2026-10-27 Asia/Shanghai

## Runtime capability refresh

| Capability | State | Evidence/source and time | Limit/fallback |
|---|---|---|---|
| Repository, Skill and Git access | available | 2026-10-27; exact planning SHA/parent, five-path commit, main and clean execution start verified | No branch/worktree changes |
| Python/checks/scoped writes | available | macOS, Python 3.14; required gates and actual installed-launcher subprocesses run | Windows/Linux and Python 3.11–3.13 not locally executed |
| Isolated installs | available | All five path overrides, temporary directories, cleared child PYTHONPATH, symlink capability exercised | No real installation or persistent PATH write |
| Copilot run/delegation | available via command-scoped host approval | Local initialization initially restricted; approved status read returned app-server/Green, balanced; one final-review dispatch gate admitted | No caller quota override, polling or configuration changes |
| Independent review | available for preliminary working-tree review | Fresh fork_turns=none copilot_final_reviewer, no implementation participation; independently ran acceptance and all final gates | Formal committed-delivery review and artifact remain pending |
| Git mutations | restricted | Later direct user grant covers implementation, handoff/evidence and independent review commits | No push, history rewrite or branch/worktree operations |
| M-01 Desktop manual evidence | unverified | Not performed; remains owned by repository owner | PENDING, stage cannot become ACCEPTED |

## Outcome and scope

- Installed launcher now switches both directions using a setting-only transaction. Eligibility requires a current intact copy installation, exact target coverage, valid required configuration, matching source/distribution, a recorded setting and no PATH request. Other cases keep the upgrade/self-copy guard.
- Implementation paths: src/codex_copilot/installer.py; CHANGELOG.md; tests/test_installer_setting_change.py. This handoff is the only additional evidence path.
- Setting-only writes affect the installed policy and manifest, with Skill fingerprint refreshed; all other ownership/recovery metadata is retained. State-directory transaction journals/backups are preserved. Partial failure restores original policy and manifest.
- Existing flags, notices, confirmation/plan-token binding and no-op behavior remain. No schema, quota, model, delegation, metrics or public CLI changes. Locked tests and frozen sources remain unchanged.
- Entry status after planning commit was clean. The pre-existing launcher acceptance file was committed unchanged (SHA256 92795bdf36db33b3dcc73e5a4dedb1eed7ce2ae466721ab80cec06de5ef6eed2); no unrelated changes were absorbed.

## Validation evidence

| Command/check | Exit/result | Artifact path |
|---|---|---|
| Planning baseline validator, with outer PYTHONDONTWRITEBYTECODE=1 | exit 0; A01–A05/A08 FAIL; A06/A07/R01 PASS, matching all nine rows; repeated after planning commit | contract baseline evidence |
| validate_ready_contract.py against repair-contract.md | exit 0 before and after planning commit | contract |
| `PYTHONDONTWRITEBYTECODE=1 python3 '/Users/eric/Documents/Vibe Coding/Cross-Agent-Delivery/scripts/validate_acceptance.py' --delivery docs/implementation/stages/s01-review-followups/repair-contract.md --baseline-sha dd81f8710508ec01aaa2e5a9e8dc38f0ca24f339` | exit 0; all nine rows PASS; all locked paths unchanged/clean | parent tool results, independently repeated by reviewer |
| `PYTHONDONTWRITEBYTECODE=1 env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest discover -s tests -v` | exit 0; 219 tests, OK (skipped=7) | /tmp/s01-f01-final-tests.log; independently repeated by reviewer |
| Official quick_validate.py against skill/codex-copilot | exit 0; Skill is valid! | parent tool results; independently repeated |
| `python3 scripts/check_release.py` | exit 0; Release metadata valid: 1.1.0 | parent tool results; independently repeated |
| `git diff --check dd81f8710508ec01aaa2e5a9e8dc38f0ca24f339 HEAD`; `git diff --check` | exit 0 | independently repeated |
| Six added installer boundary tests | PASS within full suite: stale choice/config token, modified Skill refusal, incomplete config refusal, legacy upgrade guard, ownership/uninstall restoration | tests/test_installer_setting_change.py |

All seven skips are existing Windows-only tests. Symlink capability was available
and exercised; no copy-mode/business failure was skipped. Temporary logs are
supplemental only; command/results above are the transfer evidence.

## Requirement evidence

| Requirement | Implementation location | Automated evidence | Manual/external evidence | Status |
|---|---|---|---|---|
| REQ-F01-SWITCH | installer.py setting-only eligibility/transaction | A01/A02, all managed fingerprints valid | Preliminary independent review: no P0/P1; formal verdict pending | PENDING |
| REQ-F01-CONFIRM | existing confirmation/token pipeline with setting-only actions | A03/A04/A06/R01, new token tests | Formal verdict pending | PENDING |
| REQ-F01-SAFETY | unchanged upgrade guard; existing integrity checks; transaction rollback | A05/A07/A08/R01 and boundary tests | Preliminary reviewer also checked unknown-file preservation, policy permissions and extra manifest metadata | PENDING |

## Preliminary independent review and bounded run

The fresh read-only child `/root/f01_final_review` reported no actionable P0/P1,
independently passed all nine acceptance rows, 219 tests and the remaining gates,
and did not edit any repository file. Its working-tree review is not formal
ACCEPT. A committed implementation plus direct-child handoff/evidence commit is
still required before the matched review can conclude against the delivery head.

Copilot run: 5c48ab0f-fc66-46b2-a72c-6895266f6dcf; request
8f9e6807-8018-4d49-b866-37bbbbee163d; ordinal 1;
copilot_final_reviewer / gpt-6.1-sol High / Green balanced; completed success.
The tool exposed only a canonical native task handle, so the parent registered
39aed618-0deb-4988-80ef-605f6c2d05d6 as a local opaque session binding for that
same handle; it is not claimed as a platform-native thread ID. One cumulative
follow-up slot remains for that same reviewer; any dispatch must pass the gate.
Trace: one dispatch, COMPLIANT. Measurement preference was already enabled; one
optional local observation was started without an additional quota read.
After saving this checkpoint, `run close --outcome paused` retained consumption 1
of limit 2 and `measure end --outcome paused` recorded the one allowed completion
snapshot. Resume this same run with its original policy and `--resume-consumed 1`;
do not create a fresh run to reset the cumulative review budget. Measurement is
already ended; do not repeat its end snapshot for this attempt.

## Deviations and gaps

- User expressly requested completion of F-01 after the planning boundary; the parent continued bounded Execute under that instruction. No implementation permission was inferred from the Skill itself.
- One new executor test initially assumed uninstall restored empty TOML tables byte-for-byte. Existing uninstall retains empty tables; only this unlocked new test was corrected to assert restored user values/comments and removed managed values. No product workaround or locked-test change.
- Git authority was initially pending and was then granted explicitly; the original pre-commit checkpoint is preserved below. The remaining step is formal independent review of the committed delivery. Windows/Linux/Python-version gaps and M-01 are unchanged from the parent stage.
- Original delivery/review and all historical attempts are preserved. No self-acceptance or stage/evidence advancement.

## Pre-commit checkpoint history and final delivery

The initial working-tree checkpoint was BLOCKED only on additional Git authority;
no implementation/test changes followed the preliminary independent review.
The human later selected `授权实现、交接和独立审查提交`. The implementation was
committed as 2a2366dec9a4c88347f85fd8f09129be499db9a4, a direct child of the
planning baseline, with exactly the three allowed implementation paths. Reviewed
SHA256 values match the committed files:

- installer.py: e8d90f5f3619910552287534bfdfcc31ddece9bf19d079000e8cfca1c90c3399
- CHANGELOG.md: 836836fab05f2a9b3662d0e5b65119574dd3c20eddf5b4ed5fa22781bc9ddfa3
- test_installer_setting_change.py: 6ea065a69c4a51d86caf63ce9accb0a40c79266436147d9d8f8c80c555700d3a

No earlier handed-off commit or evidence was rewritten. This is the completed
handoff for the same implementation attempt; its evidence commit contains only
this file. Development self-check is complete; independent formal Review is pending.

## Next route

Fresh independent L3 reviewer continues the same native review session through
one cumulative gated follow-up, resolves this file's commit and verifies the
implementation/handoff boundaries. Write only
`docs/implementation/stages/s01-review-followups/review-r01.md`, verify direct
human review-commit authority, run review validity and commit the report only
with a passing verdict/validity as applicable. No code or acceptance edits.
M-01 remains PENDING and does not block code Review; stage cannot become ACCEPTED.

## Rollback

Implementation commit 2a2366dec9a4c88347f85fd8f09129be499db9a4 is the attributable
repair boundary; reverting it requires separate authority. Preserve planning,
original review/delivery and this evidence history. Temporary installation state cleans up automatically;
no persistent user installation/configuration/PATH needs rollback.
