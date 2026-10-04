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

- Pre-release boundary follow-up defines responsibility owners and scope fences in existing governance files. A copy-install regression verifies the runtime contains only src/skill/agents/bin/VERSION and excludes repository-root governance, tests, scripts and user files outside the product trees.

- Boundary follow-up suite: 118 tests passed with 7 platform skips. An actual temporary Git repository verifies that ignored .env/private.key product files block tag validation while installer-excluded bytecode is allowed; diagnostics omit private filenames.

## Introduction media and README — 2026-10-04

- Added bilingual project milestones grounded in source history; only v1.0.0 is described as a tagged stable release.
- Completed a 24-second workflow illustration with music and cue sound effects. A 1080p 60fps master, 720p 30fps web MP4, 640px GIF and poster remain outside installed product trees.
- Verified seven representative frames, deterministic seeks, playback controls and phone-size scaling with zero browser errors. Chromium loads and plays the web H.264/AAC export. Both MP4s are 24 seconds with an audio stream; final web audio measured -17.2 LUFS and -1.5 dBFS true peak.
- README uses a centered, linked GIF preview with separate web/master MP4 entry points. No embedded player HTML is required in GitHub Markdown.
- Local repository suite: 118 tests run, 7 Windows-specific tests skipped on macOS; Skill validator, release metadata and whitespace checks pass. Runtime, agent configurations, installation and permission behavior are unchanged.

## GitHub Release withdrawal (2026-10-05)

- At the owner's request, GitHub Release 401943324 was returned to draft (`draft=true`); the `v1.0.0` tag and source version remain unchanged.
- Bilingual README headings and milestones now describe the source version and link to its tag instead of the withdrawn public Release. Runtime, installation instructions and demo assets are unchanged.

## Installation/quota diagnostics candidate 1.0.1 — 2026-10-05

- Confirmed source checkout from installation manifest: baseline 400609c. Installed
  artifacts matched; only service_tier differed (standard expected, default current).
  Exact-value aggregation caused incomplete despite intact installed files.
- Read-only comparison on Windows/Python 3.13.7/Codex CLI 0.160.0 used the npm
  wrapper selected by PATH. Restricted execution classified state_initialization_failed;
  host-approved execution with unchanged configuration returned real App Server
  windows. The historical process_exit cause and natural exit code remain unknown.
  No evidence links that failure to service_tier or depleted allowance.
- Candidate unit suite: 132 tests, 6 capability/platform skips on this Windows
  account. Copy/business tests passed; symlink privilege was probed by the existing
  test helper. Skill validation and release metadata checks passed.
- Five-override isolated tests cover retirement, repeat install, uninstall,
  configuration-preserving rollback, dispatch safety and managed agent drift.
  Real-pipe simulated servers cover strict initialization, natural versus cleanup
  exit codes, deadlines and process-tree cleanup. They are not live quota evidence.
- Independent L3 review, candidate CI and Windows upgrade acceptance are pending
  at this checkpoint; subsequent entries record actual results.

### Mac final acceptance handoff (pending)

The baseline 400609c was produced on the owner's Mac; this alone does not validate
live quota access. Shared configuration/RPC regressions apply to macOS as well.
After candidate CI passes, use the same reviewed candidate commit as Windows:

1. Read `${CODEX_COPILOT_STATE_DIR:-$HOME/.codex-copilot}/install.json` locally;
   locate repo_root, config_path, agent/launcher targets and mode. Keep private
   configuration and credentials out of shared outputs. Check Git state and the
   actual CLI/Python versions; preserve local edits before fetching this branch.
2. Record the pre-upgrade doctor summary by absolute launcher path. Back up config,
   manifest and runtime pointer locally. Select the recorded candidate commit,
   run the source install --dry-run, then install only the reviewed artifact plan.
   The tier preference must stay unchanged; use copy mode if agent symlinks fail.
3. Use the manifest's absolute launcher for doctor --json and one
   status --refresh --json. Required settings/artifacts must pass; quota acceptance
   requires source=app-server, read_success=true and actual windows. Record PATH
   warnings separately. Fresh-chat role loading follows a user-timed Desktop restart.
4. For permission/state errors, make at most one command-specific host-approved
   comparison after the execution context changes. Report safe category, phase and
   natural exit code; do not copy credentials or reset account state.
5. Append the sanitized result and tested commit here. Until then, macOS real-device
   quota/installation acceptance remains pending, irrespective of simulated CI tests.

Rollback handoff: retain the installer's backup_dir and recovery.json plus the
pre-upgrade manifest/runtime pointer backup. Compare each affected target with
its new manifest fingerprint before restoring its original. For config, restore
only keys changed by this upgrade that still equal their newly installed values;
never replace a current whole config if subsequent user edits exist. Preserve
measurement preferences/history and unrelated state. Stop and report conflicts or
missing backups; do not use downgrade installation as destructive recovery.

- L3 reviewer reproduced direct legacy uninstall restoring tier, omitted runtime
  pointer records yielding complete, and symlink target edits escaping link-only
  fingerprints. Fixes preserve tier even before upgrade, enforce expected artifact
  coverage, and record/verify symlink instruction content. Legacy link-only agents
  need a source-verified upgrade. Both mock and real-symlink regressions were added;
  real-symlink tests remain capability-dependent on this Windows account.

- Revised Windows suite: 136 tests, 7 platform/capability skips; no business failures.
  L3 reviewer rechecked 34 diagnostics/CLI tests (3 capability skips) and reported no
  blockers after the three fixes. A proposed extra cache-consistency hardening delta
  was withdrawn when the second authorized review hit model capacity. The shipped
  changes retain the reviewed cache provenance/TTL behavior. Both dispatches count
  against the same cumulative run budget; no budget override was used.

### Windows installed acceptance and CI (completed)

- Reviewed runtime source commit: 330f6383b4fa0263d8500e4f08b5e21a97b9c2b4.
  All 13 jobs passed in [candidate CI](https://github.com/EricArcha/Codex-Copilot/actions/runs/37221851774):
  Windows/macOS/Linux Python 3.11–3.14 plus the Skill validator. macOS automated
  checks passed; the owner's Mac real-device acceptance remains pending.
- Formal copy upgrade preview had zero actual setting changes and used its bound
  plan token. Installed version is 1.0.1; service_tier=default is retained and its
  prior ownership record is retired. Repeat-install preview needs no changes.
- Pre-upgrade config/manifest/runtime-pointer backups are under the state directory,
  backups/pre-1.0.1-d744f9d0-ea84-4e02-9654-7f1181d2d785. Transaction backups/recovery
  mapping are under backups/e59278ccf9904f24a88650669cc6c601. No auth files were copied.
- Parsed full Codex configuration is identical before/after. Existing installer
  text writing normalized LF to CRLF on Windows; this is the only byte difference.
  Profile and measurement preference presence/content and persistent user PATH
  match the pre-upgrade baseline. Measurement remains off; history was not removed.
- By the absolute installed launcher, host-approved doctor reports ok=true,
  installation_state=complete, runtime_available=true, and quota read_success=true,
  available=true, source=app-server. The resolved runtime is the existing npm entry
  via Node selected by PATH, still Codex CLI 0.160.0.
- A separate installed status --refresh read returned actual 300/10080-minute windows
  with remaining 48%/66%, band=yellow, no quota error and cache_status=valid. These
  are observations at acceptance time, not future allowance guarantees.
- The ordinary restricted installed launcher still reports process_exit at initialize,
  natural exit code 1, expired cache and unavailable quota, while installation remains
  complete and service_tier is nonblocking. Earlier direct restricted diagnostics
  classified state_initialization_failed. Host-approved success proves the environment
  matters but does not establish the exact low-level cause of every historical exit.
- Reviewer trace d744f9d0-ea84-4e02-9654-7f1181d2d785 is COMPLIANT: one successful L3
  final review, one model-capacity failure for the withdrawn optional delta; no override.
- GitHub connector denied draft-PR creation (403). Automatic approval then rejected
  reusing Git credentials for a direct API write as insufficiently authorized. That
  script never executed; no token was read/output/persisted. The reviewed branch is
  pushed, but PR creation is pending explicit authorization. No main merge, tag,
  public Release or Desktop restart occurred.
