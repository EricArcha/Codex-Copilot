# Verification evidence

Local validation on 2026-10-02 used Windows, Python 3.13.7 and Codex CLI 0.159.0-alpha.12.1.

- Baseline at `8df44bb`: 71 tests, 5 failures and 13 errors. The full installer rejected Windows; one error independently demonstrated missing symlink privilege.
- Updated full suite: 104 tests discovered; 98 passed and 6 skipped. Four skips require unavailable Windows symlink privilege; two exercise POSIX-only behavior (the original 0.1.0 installer and a child ignoring SIGTERM). Copy installation and business logic are not skipped. The final affected-module rerun also passed.
- The installed Skill Creator `quick_validate.py` accepted the updated Skill.
- Real app-server quota reads succeeded. Tests additionally verify unknown/cache degradation, malformed responses, EOF, timeout, partial lines and descendant cleanup. No quota fixture was used for the live check.
- Real copy installation adopted the verified existing Skill registration after backing it up, installed all six regular agent files and managed settings, and reported `doctor: complete`. Upgrading to the reviewed source and a subsequent no-change installation succeeded. Persistent user PATH was not modified.
- Isolated tests cover Unicode/space paths, `.cmd` arguments/exit codes, custom runtime paths, conflicts, backups, upgrade and uninstall restoration, edited files/settings, failed rollback and mocked user PATH ownership.
- An independent GPT-6.1 Sol High review found lifecycle issues; their reproductions now pass and no blocking findings remain. Model routing, privacy and delegation policies were retained.

GitHub Actions [run 36981531703](https://github.com/EricArcha/Codex-Copilot/actions/runs/36981531703) passed all 12 Windows, Linux and macOS test jobs with Python 3.11–3.14, plus the official Skill validation job. The first run exposed a macOS exited-process-group cleanup error; reaping the leader before signaling and unconditional pipe cleanup fixed it. The Windows runner explicitly enables and probes symlink capability; Linux/macOS additionally run the archived original 0.1.0 installer upgrade regression. Check the PR's latest Actions results for executed platform evidence.

After the user restarted Codex Desktop on 2026-10-02, all six installed role types were dispatched in fresh bounded child sessions and returned successful file-read smoke results: copilot_scout, copilot_investigator, copilot_worker, copilot_reviewer, copilot_final_reviewer and copilot_astra_final_reviewer. The runtime used the role configurations for Luna Low, Sol Medium/High and Astra High. This verifies dispatch and a representative tool read, not a long task for each role. Trace run 40b3363d-4f88-4670-a803-7c984ef5d58c records six successes and explicit user authorization to exceed the default delegation budget. The test used a temporary premium route; the default profile remained balanced. No source or user configuration was changed by the probes. Symlink installation on this local ordinary-user Windows account remains unavailable; default copy mode is verified.

Caught installation failures retain unique backups and a recovery journal. Forced process interruption and external file locks may require manual recovery. The persistent Windows PATH registry operation is opt-in and its lifecycle is tested using a mocked registry; no live user PATH write was performed during validation.

The archived fixture in `tests/fixtures/release-0.1.0.zip` contains the original source components and MIT license from commit `8df44bb92beb45a7e387a4a2cd9d7fe381ea9662`, for offline upgrade testing.

A later macOS CI run revealed the same Darwin EPERM edge on an exited descendant group during the final SIGKILL. The cleanup helper now checks /bin/ps group/state output only after Darwin denies a signal: it accepts an absent or zombie-only group, preserves denials for live members, and fails if inspection is unavailable or malformed. This follows [Apple XNU killpg1](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_sig.c#L1612), which excludes zombies from group iteration. Regression checks include real TERM-ignoring descendants, ten repeated real descendant cleanups on macOS, and explicit live-member/inspection-error cases. The existing independent reviewer rechecked this affected finding without blocking findings.

## 1.0.0 release validation (2026-10-02)

- Source baseline: main 8f6e23e, 104 tests passed locally on macOS (7 platform-specific skips); Skill validator passed.
- Immutable 0.1.1 upgrade fixture is an archive of src, skill, agents, bin, VERSION and LICENSE from 8f6e23e3e2cca89cbcc81278380074c0220f2ebf. The existing 0.1.0 fixture is unchanged.
- Real restricted-host query returns unknown with state_initialization_failed; no raw stderr is emitted or saved. The same host-approved query returns real windows with source=app-server.
- The actual L3 balanced final-review gate refreshed live quota with source=app-server and retained its cumulative budget. Trace run 3793b6b4-9036-4488-9bca-f9d0e6f4a5af records the declared review.
- User-install dry-run upgrades only managed artifacts; all six managed settings are unchanged. Actual installation is performed only after release verification.
- Version metadata and v1.0.0 tag checks pass. Cross-platform CI and final review evidence are recorded in the release PR. Restart-dependent fresh-chat role loading requires the user to restart Desktop; this running chat cannot certify a future restart.

- Final local suite: 114 tests passed with 7 platform-specific skips; Skill and release metadata validators passed. Independent GPT-6.1 Sol High review found one denied-cache exception leak. The cache existence probe was removed; refresh/non-refresh regressions now pass. The reviewer rechecked affected paths (26 tests) and reported no blocking findings.
