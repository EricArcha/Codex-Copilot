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

### Mac final acceptance handoff (installation/quota completed; restart pending)

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
5. Append the sanitized result and tested commit here. Real-device results below
   distinguish installation/quota acceptance from restart-dependent role loading.

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

### Windows restricted initialization root cause — 2026-10-05

- A targeted source-reader reproduction returned state_initialization_failed at
  initialize, natural exit code 1. Its bounded stderr identified SQLite state
  initialization and Windows OS error 5 (access denied); no raw stderr was saved.
- Read-only Win32 CreateFileW/OPEN_EXISTING permission probes requested a write
  handle without writing bytes. The restricted process was denied (error 5) for
  the Codex state directory and existing SQLite databases. The same directory
  and state database probes succeeded (error 0) in host-approved execution.
- No CODEX_SQLITE_HOME environment override or sqlite_home configuration override
  was active. The selected npm/Node CLI and existing user configuration were
  unchanged. One host-approved absolute-launcher doctor returned complete,
  runtime_available=true and live source=app-server/read_success=true.
- This establishes the current reproduction's cause: the restricted execution
  context denies writes needed by App Server's local SQLite initialization.
  Existing command-scoped host approval resolves the tested quota operation;
  no global sandbox change, ACL change, credential copying, state relocation or
  account cleanup was performed. The CLI does not auto-escalate permissions.
- The old historical process_exit event still has no retained underlying error;
  this reproduction does not retroactively prove its exact cause. Mac real-device
  acceptance remains pending and is not inferred from this Windows result.
- Official context: [Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox)
  documents write boundaries; [environment variables](https://learn.chatgpt.com/docs/config-file/environment-variables)
  documents SQLite state defaulting to CODEX_HOME. No runtime code change was
  required for this permission boundary; the existing quota reference already
  prescribes one command-scoped host-approved attempt after context changes.
- Revalidation: host-approved full suite ran 136 tests successfully (7 capability/
  platform skips); Skill and release metadata validation passed. Restricted suite
  attempts failed on temporary test-artifact access, including a workspace-scoped
  TEMP attempt; they are not counted as passes. Their owned test processes were
  stopped and the newly created workspace temporary directory was removed.

### Mac installed acceptance — 2026-10-05

- Synced candidate branch `codex/installation-quota-diagnostics` at
  8570d0859078c2c753bd50fe948a1026b0479e97. Its product trees are identical to the
  Windows-reviewed runtime commit 330f6383b4fa0263d8500e4f08b5e21a97b9c2b4;
  the later commits add verification documentation. Latest
  [candidate CI](https://github.com/EricArcha/Codex-Copilot/actions/runs/37225177884)
  passed all 13 jobs, including macOS Python 3.11–3.14.
- Local macOS, Python 3.14.6, Codex CLI 0.147.0 via its npm launcher selected by
  PATH: 136 tests ran successfully
  with 7 Windows-only skips. Native symlink capability probes and symlink business
  regressions passed. Existing five-path-override isolated regressions passed,
  covering historical upgrades, configuration preservation, rollback, changed
  artifacts and dispatch checks. Skill validator, release metadata and whitespace
  checks passed. These tests do not substitute for the live checks below.
- Before upgrade, the absolute installed launcher reported complete 1.0.0 and
  live quota in host-approved execution. The existing manifest matched this source
  checkout and copy mode. Backups of existing config, manifest, runtime pointer,
  measurement preference and metric history files were retained locally under the state
  directory at backups/pre-1.0.1-mac-b2a59e7f-891c-4faf-98cb-a2ecb8c917a7.
  No authentication files were copied or private configuration contents shared.
- Applied the reviewed copy-upgrade preview through its bound plan token; actual
  setting changes were zero. Installed version is 1.0.1. Full configuration bytes
  and parsed values are identical before/after, including the tier preference.
  One historical tier ownership record was retired. The profile file was absent
  before and after (the effective profile remains balanced). Measurement
  preference and existing metrics history were byte-identical during upgrade;
  measurement remains enabled. Persistent PATH was not changed. Repeat-install
  preview reports `Already installed; no changes.`
- Transaction originals and recovery mapping remain under state-directory
  backups/c14708b9ccf24f0f987511ee53d0fe32. No rollback was needed. The rollback
  handoff above continues to apply; backups are retained rather than automatically
  restoring or downgrading the installation.
- Installed absolute-launcher restricted doctor reports ok=true, complete,
  runtime_available=true and all required settings/artifacts valid, with a quota
  warning: state_initialization_failed, phase=initialize, natural exit code 1,
  expired cache, read_success=false and available=false. This Mac observation does
  not establish the SQLite/OS-level cause demonstrated on Windows.
- One command-scoped host-approved comparison reports complete,
  runtime_available=true, no failed/warning checks and live quota
  source=app-server/read_success=true/available=true/cache_status=valid. A separate
  required installed status --refresh returned real 300/10080-minute windows,
  remaining 26%/63%, band=red, and no error. These are time-bound observations.
  No global sandbox policy, folder permissions, credentials or account state were
  changed. The user explicitly authorized continuing L3 work and final-review
  delegation despite the Red-band pause.
- Installation and live-quota acceptance are complete. Restart-dependent fresh
  Desktop chat role loading remains pending a user-timed restart; this active chat
  cannot certify that future restart.
- Independent GPT-6.1 Sol High final review found no blocking issues. The reviewer
  confirmed matching product trees, sanitized acceptance evidence and retained
  originals for all 12 transaction recovery mappings. A documentation correction
  clarifies the absent profile file rather than claiming it was backed up.
  Trace run b2a59e7f-891c-4faf-98cb-a2ecb8c917a7 records one successful final review
  using live app-server quota and the explicit user-authorized Red-band override;
  compliance is `OVERRIDDEN BY USER`, not a default-budget compliant dispatch.


### Mac post-restart role-loading acceptance — 2026-10-05 (completed)

- In the user's post-restart Desktop acceptance chat, tested source commit
  8570d0859078c2c753bd50fe948a1026b0479e97 and installed version 1.0.1.
  Installed absolute-launcher doctor reports complete, runtime_available=true,
  matching artifacts and required settings. Restricted quota initialization still
  warns; one command-scoped host-approved status succeeded with actual App Server
  windows (initial remaining 21%/62%, Red).
- The user explicitly approved continuing the six-role read-only acceptance,
  exceeding the cumulative delegation budget and a temporary premium route.
  Every child passed the installed CLI gate using the same canonical run UUID
  and live source=app-server; no child recursively delegated. All six actual
  role sessions successfully used a tool to read VERSION as 1.0.1:
  copilot_scout (Luna Low), copilot_investigator and copilot_worker (Sol Medium),
  copilot_reviewer and copilot_final_reviewer (Sol High), and
  copilot_astra_final_reviewer (Astra High).
- Trace run 0f554f46-a1ec-4150-88a8-4d203f6d7514 records six dispatches and six
  successful completions, with compliance OVERRIDDEN BY USER. Model/effort
  entries describe configured roles, not independent backend billing telemetry.
  These bounded probes verify fresh role loading and representative tool access;
  reviewer probes are not source reviews or full development-task acceptance.
- Configuration and all six agent-file fingerprints are unchanged; the profile
  file's presence/content is unchanged and the effective default remains balanced.
  No installation, persistent PATH, sandbox policy or account-state changes were
  performed. Only this verification evidence was appended to the existing local
  documentation edits.
- Optional local measurement was already enabled. Begin/end used the same UUID;
  begin had no fresh cached snapshot and end read App Server once. The incomplete
  start observation cannot support an allowance-cost or savings comparison.
- Local revalidation: 136 tests completed successfully with 7 Windows-only skips;
  Skill Creator validation and release metadata check (1.0.1) passed. Installation,
  live-quota and post-restart role-loading acceptance are now complete on this Mac.


### PR merge-gate pipe cleanup regression — 2026-10-05

- PR #7 CI run 37227389650 exposed a macOS/Python 3.14 race: an exited App
  Server reader causes buffered stdin close to raise BrokenPipeError, masking
  the RPC diagnostic and leaving stdout/stderr unclosed. Earlier push CI passed;
  that does not invalidate this observed failure.
- A deterministic real-process regression injects the close failure and failed
  before the fix. Cleanup now ignores only stdin BrokenPipeError from the stopped
  child and closes both output pipes even if another close raises. Successful
  results, original failure phase/natural exit code and other cleanup failures
  retain their behavior.
- All 11 pipe tests pass; the original RPC diagnostic test passed 30 consecutive
  local repetitions. Full suite: 137 tests, 7 Windows-only skips; Skill validator,
  release metadata and whitespace checks pass.
- Additional independent Sol High final review found no blockers and reran all
  11 pipe tests successfully. Trace 5f58fc53-423c-42cf-8247-83a98a54799f records
  one successful review with explicit user-approved override. Its live gate
  observed Green after the natural quota refresh; the override flag remains
  recorded. Cross-platform checks on this repair are required before merge.
- This repair changes source only. Installed-device and six-role acceptance
  above describe the pre-repair installed runtime; no new user installation or
  release publication was performed by this merge-gate repair.

- Follow-up push CI 37227647687 exposed a distinct test-server race: the RPC
  error fixture exited after sending its responses before waiting for client
  initialization/quota requests, allowing a legitimate process_exit instead of
  the expected protocol_error. The fixture now waits for corresponding requests.
  This does not weaken the category or secret-redaction assertions. The same
  independent reviewer rechecked the test-only follow-up with no blockers and
  reran all 11 pipe tests. Full local suite remains 137 tests with 7 Windows skips;
  Skill, release and whitespace checks pass. Runtime repair is unchanged.

## Bounded execution candidate 1.1.0 — 2026-10-07

- Responsibility owner: execution/delegation enforce cumulative budgets and role
  policy; model constructs data-plane invocations; metrics remains a best-effort
  privacy-safe projection. Trust changes are limited to local durable authorization,
  explicit user-declared grants and caller-declared opaque acceptance evidence.
  Exclusions: no user installation, global settings/permissions, credential handling,
  Any-Persona changes, exact billing or Desktop-parent hard enforcement.
- Incident verification independently reproduced the documented live-* receipt
  totals by content-hash deduplication and confirmed eight formal artifacts with
  no final blind scores. Retained dispatches all used live app-server quota;
  unavailable reads were not observed in those successful gate events. Account
  deltas cannot be attributed as exact task costs.
- A restricted current quota query reproduced state_initialization_failed at
  initialize, natural exit 1. A command-scoped host-approved comparison succeeded
  with two actual windows. This establishes the execution-context distinction,
  not a proven macOS SQLite file/OS-error root cause for every historical failure.
- Local suite: 184 discovered, 177 passed, seven Windows-specific skips on macOS.
  New regressions cover scoped grants, structural policy, closing reserves,
  concurrent reservations, interrupted/replayed calls, ledger corruption and
  write failure, rotation-independent counts, native follow-up identity,
  batch evidence/scoring, incomplete effect acceptance, privacy and Git identity.
  Existing installation tests use all five isolated path overrides. Skill Creator
  validation, release metadata 1.1.0 and whitespace checks passed.
- One bounded live probe obtained trusted Yellow quota and started the fixed model
  command. The parser rejected a native message representation; the attempt remains
  recorded as failed/consumed, not retrospectively rewritten. Offline native receipt
  inspection found Reasoning/AgentMessage item variants and no tools in the matched
  receipt. The parser now accepts those exact variants; a deterministic real-process
  regression passes. A successful live rerun is not claimed.
- Independent L3 review and cross-platform CI results are recorded below when
  available. Project-local Git identity is absent at this checkpoint; no commit,
  branch push, tag, public release or user installation is claimed.

### Independent review and bounded closure

- One actual reserved copilot_final_reviewer (GPT-6.1 Sol High, balanced) passed the
  source gate with live app-server Yellow. It independently identified six issues:
  paused-stage bypass, identical-count resume, metrics-dependent durable recovery,
  effective-band L3 fallback, uncertain model outcomes (including interruption),
  and recovered legacy trace visibility. Root fixed them as the sole writer.
- The same active review turn rechecked affected changes without another dispatch;
  58 focused offline tests passed and no actionable findings remained. Post-spawn
  timeout/KeyboardInterrupt now preserves an unknown outcome and observed session;
  unknown turns block continuation, expansion and completed closure. Status opens
  its ledger read-only, and durable resume does not depend on readable metrics.
- Final full local suite: 184 discovered, 177 passed, seven platform skips; Skill,
  release metadata and whitespace checks passed. Cross-platform CI and a successful
  corrected live model smoke remain unverified. No user installation was changed.
- Run 2c307c91-50d4-4ac1-9867-a69d95b33e2c consumed two managed starts (one failed
  model probe, one successful independent review), no route override, total cap 3.
  It is paused as an acceptance checkpoint. Trace records one compliant declared
  reviewer; the failed probe is unchanged. An approval review initially conflated
  child ordinal 1 with model/global ordinal 1; a read-only request-ID check proved
  they differ, and exact-ID closure preserved the failure without changing budget.
- Missing project-local commit identity remains awaiting user confirmation. No
  commit, push, tag, publication or cross-platform CI success is claimed.
- Optional measurement reused the initial Start values and made one final read:
  same-window primary used 51% to 79% (28 percentage points), secondary 8% to 12%
  (4 points). These are shared-account observations, not exact task billing or
  measured savings; Desktop parent usage is outside managed-start enforcement.

### Pre-push revalidation — 2026-10-07

- Repeated full local suite: 184 discovered, 177 passed, seven Windows-specific
  skips on macOS; Skill validation, 1.1.0 metadata and whitespace checks passed.
- Isolated copy-mode upgrade from the actual supported 1.0.1 distribution to
  1.1.0 used all five path overrides. Configuration bytes, measurement preference,
  profile and a history sentinel remained unchanged; repeat installation was
  idempotent. No persistent user PATH or global installation changed in this test.
- Remote main matched the branch base before commit preparation. Host-approved
  GitHub authentication succeeded; restricted authentication diagnostics alone
  were misleading. The next live quota checkpoint returned Red, so the corrected
  smoke requires a specific finite user authorization or natural recovery.

### Authorized pre-push smoke checkpoint — 2026-10-07

- The user confirmed the repository-local EricArcha commit identity and exactly
  one finite evaluation/probe exception. Identity validation now passes; global
  Git identity was not changed.
- Run 3e789f92-5f4f-40a2-abc0-132e0eb1327e had total/smoke caps of one, no closing
  reserve, and one 600-second grant. Its sole request
  d192335f-15bf-41e6-8b06-f487fd5884a8 started the fixed isolated model command,
  but rejected an unexpected item before completion. It remains unknown/consumed,
  the grant is exhausted, and the run is paused. No retry was started.
- The observed native session identifier was retained. Its local rollout was
  empty and read-only history inspection yielded no items; the exact rejected
  representation and whether it represented a tool are not established. The
  generic rejection message is not evidence of actual tool use. Accepting guessed
  item types or retroactively marking the probe successful would be unjustified.
- Corrected live end-to-end acceptance therefore remains blocked. The source may
  be committed/pushed for CI and draft review, but this checkpoint does not qualify
  for the requested local upgrade or publication. Existing local 1.0.1 stays installed.

### Cross-platform follow-up

- First push/PR CI passed all eight macOS/Linux Python 3.11–3.14 jobs and Skill
  validation. All four Windows jobs exposed one test cleanup failure: a test-owned
  sqlite3 connection context committed its transaction without closing the handle.
- The test now uses contextlib.closing around that connection, retaining the actual
  corruption assertion and transaction commit. Runtime enforcement is unchanged;
  the independent L3 production review still covers the same production source.
- The full local suite, Skill and release checks still pass. Windows rerun results
  belong to the subsequent exact-commit CI, not the first failed CI.

### Real end-to-end diagnosis and acceptance — 2026-10-07

- Follow-up diagnosis retained caller-owned JSONL before parser rejection, outside
  metrics/state. The reproduced rejected item was item.completed/error carrying
  the CLI notice about the enabled experimental skip_host_skill_discovery feature.
  It was not a tool. Earlier missing receipts cannot prove that every historical
  rejection was the same item; the reproduced parser defect is now established.
- Managed arguments suppress unstable-feature notices for that invocation only;
  no global config changes. Non-fatal error/Error items are forwarded to callers,
  while actual tool items and top-level error/turn.failed remain rejected. A real
  subprocess regression covers notice followed by success and both terminal errors.
- Diagnostic run 052758e0-43f9-4480-88d2-85c716542499 preserves its consumed/unknown
  attempt and is paused. Acceptance run e3c02340-aaea-409c-863e-2390097bb308 imports
  that one consumed attempt explicitly, total cap 4/reserve 1, smoke cap 2. This
  retains cumulative accounting rather than rewriting failure or resetting budget.
- Two actual managed model calls succeeded: first returned a fresh random token;
  a follow-up bound to the same observed session correctly repeated the previous
  token. Both request replays returned executed=false without another process.
  Direct smoke evidence passed; no domain-effect conclusion is claimed from it.
- Full local suite: 185 discovered, 178 passed, seven Windows-specific skips. Skill
  validator, release metadata 1.1.0 and whitespace checks passed. One reserved
  independent L3 final review and exact-commit CI remain required before install.

- Independent copilot_final_reviewer found no actionable issues in the two-file
  executable/test delta; all 13 focused tests passed. Additional subprocess probes
  confirmed both notice case variants are forwarded and a following tool event is
  still rejected. It independently checked the retained diagnostic and cumulative
  four-call ledger accounting, without making model/network/quota calls itself.
- The acceptance budget is exhausted (one imported diagnostic, two real model turns,
  one successful reviewer). The run is honestly closed as a paused checkpoint:
  smoke advancement preceded final review, so the existing stage-bound acceptance
  API cannot attach review acceptance without a new pilot call. No stage or outcome
  was rewritten and no fifth call was made. Repo acceptance is evidenced separately
  by direct smoke receipts, independent review and exact-commit CI; no comparison
  effect or runtime publication_eligible claim is made.

### Verified local synchronization

- Product commit e23f677c68abe21de460e029d3a40a6aedc528e9 passed all 13 CI
  jobs (Windows/macOS/Linux × Python 3.11–3.14 and Skill validation):
  https://github.com/EricArcha/Codex-Copilot/actions/runs/37641524577 .
- After reviewing the managed plan, the user-authorized copy installation upgraded
  1.0.1 to 1.1.0 from that exact clean source. Additional local backups preserved
  the prior config, manifest and runtime pointer; installer transaction backups
  also remain. Config, measurement preference, profile, execution ledger and metrics
  were byte-identical immediately after installation. No persistent PATH changes.
- Installed launcher reports 1.1.0; host-approved doctor reports complete installation,
  runtime available and successful live app-server quota. Repeat dry-run requires no
  changes. Replaying the successful request through the installed launcher returns
  executed=false, no model output and unchanged total consumption 4/4.
- Optional measurement ended once using doctor's existing snapshot, without another
  quota read. Its baseline covers the acceptance portion only, excluding the earlier
  diagnostic; it is a shared-account observation rather than exact task cost.
- No merge, public release or tag was performed. Desktop restart/fresh-chat loading
  is a user-side follow-up and was not claimed as tested in this active chat.
