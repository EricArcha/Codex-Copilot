# Changelog

Dates identify source version changes; 0.1.x entries are historical source
versions, not retroactively claimed GitHub releases.

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
