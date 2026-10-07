# Changelog

Dates identify source version changes; 0.1.x entries are historical source
versions, not retroactively claimed GitHub releases.

## [Unreleased]

- Withdraw the public 1.0.0 GitHub Release to draft at the owner's request; retain the source version and tag, and correct README release claims.

- Add source-history milestones to both README files and complete the project introduction demo.

- Align README release entry points and Skill-only/full-install capability boundaries.
- Expand installation acceptance and quota-permission guidance for the published 1.0.0 workflow.

## [1.1.0] - 2026-10-07

- Replace bare internal delegation overrides with scoped, expiring user-declared
  grants; role, phase, model/effort, safe configuration and writer constraints
  remain binding. Native follow-ups retain their original session role.
- Store cumulative authorization in a transactional SQLite execution ledger,
  separate from rotating, best-effort metrics. Failed and interrupted attempts
  remain consumed; duplicate request IDs cannot launch another model turn.
- Add explicit run budgets, closing reserves, legacy recovery confirmation and
  bounded offline/smoke/pilot/batch evidence checkpoints. Engineering success
  alone cannot complete a comparison with missing effect acceptance.
- Distinguish native non-fatal CLI notice items from tool activity and terminal
  errors; suppress experimental-feature notices in the managed invocation only.
- Add a fixed, isolated `model exec` data-plane entry point and project-local Git
  identity check. Results belong to callers; prompts and raw receipts never enter
  Copilot execution state or metrics.
- Offer an explicit account-observation guard without enabling measurement or
  polling. Bulk calls reuse only the recent trusted quota cache; unavailable
  quota blocks bulk expansion. Strictest-band and cumulative limits survive resets.
- Existing public CLI/JSON meanings remain; internal `_delegate` callers must
  begin a run, provide a request UUID and replace `--override` with `--grant-id`.
  Older traces remain display-only legacy declarations. No automatic migration,
  installation, privilege escalation or global configuration changes.

## [1.0.1] - 2026-10-05

- Preserve service-tier preferences on install, upgrade and uninstall; retire old
  tier ownership records without losing their history or backups.
- Separate installation integrity, required configuration and runtime availability
  in doctor, with per-key impacts and independent PATH warnings.
- Verify required manifest coverage and symlinked agent instruction content.
- Require safe settings and unchanged managed agent artifacts before delegation;
  quota overrides cannot bypass these checks.
- Preserve quota results and diagnostics when closing an exited App Server input
  raises a broken-pipe error; always close the remaining output pipes.
- Wait for App Server initialization before reading quota; report failure phase,
  natural exit code, cache state and live-read/availability separately.
- Keep command-scoped host approval, bounded child cleanup and 60-second successful
  cache fallback. No automatic escalation, additional quota polling or telemetry.

## [1.0.0] - 2026-10-02

- Establish a stable CLI, JSON, installation and persistent-data contract.
- Classify quota permission/state initialization, process, login, protocol and
  timeout failures without persisting raw child output or secrets.
- Preserve successfully read live quota when its cache cannot be written.
- Define command-scoped host-approved execution for Desktop sandbox restrictions;
  unknown routing remains a temporary failure mode, not the expected happy path.
- Add release metadata checks, tag verification and release/contribution governance.
- Fence document ownership, runtime responsibilities, trust sources and installed
  artifacts; exclude repository-root non-product files from installations and
  reject uncommitted/untracked product-tree content during tag validation.
- Verify upgrades from immutable 0.1.0 and 0.1.1 source snapshots.

## [0.1.1] - 2026-10-02

- Add native Windows support and safe cross-platform installation.
- Improve App Server pipe handling, timeout and process-tree cleanup.
- Add cross-platform CI and installation/upgrade verification.

## [0.1.0] - 2026-09-05

- Introduce quota-aware Codex orchestration, managed roles and installation.
- Subsequent unversioned updates through September add guided safe installation,
  optional allowance measurement and GPT-6 family routing, including GPT-6.1 Sol.
