# Release policy

`VERSION` is the authoritative product version. `pyproject.toml` is a checked
mirror; runtime and App Server client metadata read `VERSION`. Never rewrite
historical fixtures to match a current version. Schema versions are independent.

From 1.0.0, use stable semantic versions: PATCH for compatible fixes and docs,
MINOR for compatible features, MAJOR for changes breaking the guarantees in
[compatibility.md](compatibility.md). A large feature does not by itself require
MAJOR. The existing 0.1.0 and 0.1.1 source versions were not tagged GitHub releases;
1.0.0 establishes the first stable contract. Do not invent historical releases.

## Required sequence

1. Sync main without overwriting user work; develop in a `codex/` branch.
2. Update VERSION, its mirror and CHANGELOG. Run `python3 scripts/check_release.py`.
3. Pass the full unit suite, Skill validator and all applicable cross-platform CI
   jobs. Verify upgrades from the supported previous versions. Permission,
   installation/migration and delegation changes require L3 independent review.
4. Create a PR with behavior, compatibility impact and validation evidence.
   Merge only after checks on its latest commit and required review pass.
5. Wait for verification on the resulting main commit. Run
   `python3 scripts/check_release.py --tag v<version>` on that exact commit.
   Tag validation also rejects uncommitted/untracked content in product trees;
   root-level user files outside those trees remain excluded from installation.
6. Create an annotated `v<version>` tag pointing to that main commit, push it,
   and wait for tag verification. Publish a non-draft, non-prerelease GitHub
   Release with the changelog entry, upgrade instructions and known limitations.
7. Install from the tagged commit after reviewing the installer dry-run; verify
   version, doctor, repeat-install idempotence and live quota in host-approved
   execution. Restart Desktop and verify in a fresh chat.

Never publish while required validation fails. Never move or reuse a published
version/tag. For a release defect, publish a new PATCH or MINOR as appropriate;
stop distribution of a faulty release and document recovery. Keep verification
and review evidence in the PR and docs/verification.md. CI enforcement supplements
this policy; no branch-protection setting change is implied.

Release-source checks also reject ignored non-runtime files inside product trees
(e.g. credentials); generated .pyc/.pyo, which the installer omits, are the only exceptions.
