# Contributing

Read [AGENTS.md](AGENTS.md), [compatibility](docs/compatibility.md) and
[release policy](docs/releasing.md) before changing public behavior.

Keep one writer. Use read-only bounded agents only through the Skill delegation
gate. Normal changes require focused verification and independent review when
required by the Skill; permission, installation/migration or delegation changes
are L3 and require an independent final review. Fix findings before merging.

Use the local checks in [AGENTS.md](AGENTS.md), including `python3 scripts/check_release.py`.
Do installation experiments with all five path overrides in temporary directories.
Never write a developer's persistent PATH or reset account state to pass tests.

## Upgrade delivery

An explicit request for “升级交付” or “upgrade delivery” in this project covers
the following sequence. A narrower request ends at its stated scope. A model
change still requires its own approval of the exact recommendation.

1. Verify the configured remote and latest `main`. Choose the merge path below,
   preserve user changes, and resolve conflicts before validating the candidate.
2. Commit the scoped changes and verify the outgoing files and destination.
   For a direct push, pass the required local checks and push to `main` without
   force. Follow the PR checks below when a PR is required.
3. Confirm that the change reached remote `main` and fast-forward a clean local
   `main`. If a PR was used, delete the reviewed branch after verifying its
   local head and ancestry. Use an expected-head lease for remote deletion.
   Leave a moved branch or one containing unmerged work intact.
4. Verify the local installation. When managed artifacts changed, preview and
   sync them from the verified `main` after checks pass. Keep the configured
   model and effort, and reuse applicable Desktop acceptance evidence.

Continue through waits and recoverable failures in the same chat. If a push is
rejected, verify the exact destination, authorization and outgoing payload
before any permitted retry. If access remains blocked, continue independent
checks and keep the branch available. When user action is required, report the
completed stages, the blocker, and the single action that can unblock delivery.

## Choose a merge path

Low-risk documentation edits can go directly to `main` after the local checks
in [AGENTS.md](AGENTS.md) pass and when repository protections allow it. This
covers typos, wording clarifications that preserve meaning, and ordinary link
repairs. Changes to installation or usage instructions, compatibility claims,
version or release history, or governance use a PR.

Use a short `codex/` branch and PR for code, installer, migration, permission,
delegation, CI and other changes that need verification before reaching `main`.
Use the PR path if repository protections require it. Start required independent
review alongside PR CI after focused local checks pass and finish the full local
checks. Merge only after CI and required review pass for the exact candidate.
Fix failures within scope and reverify if the PR head or base moves. Pin the
verified head for the merge.

CI runs on PRs, pushes to `main`, and version tags.
A feature branch push has no separate CI run.
The `main` run verifies the merged commit and gates publication. See the
[release policy](docs/releasing.md) for the full publication sequence.

Give the independent reviewer the candidate SHA, affected behavior, risk
boundaries and existing check results. Use the Skill's
[review continuation policy](skill/codex-copilot/references/routing.md#final-review-continuation)
for bounded follow-up and stalled reviews.

PRs describe the concrete problem, resulting behavior, compatibility impact,
tests and material limitations. Keep relevant evidence in docs/verification.md;
never include secrets or raw authentication/error output. Update CHANGELOG for
user-facing changes. Do not create new governance documents when an existing
rule can be clarified in its current home.
Include the bilingual README milestone check from [AGENTS.md](AGENTS.md) in
each update's documentation review.

## Change boundary checklist

Each PR includes three brief statements: responsibility owner, interfaces/trust
boundaries changed, and exclusions. Explain why a new file belongs to that owner.
Keep normative rules in their owner documents listed in AGENTS.md; link instead
of duplicating. Verification records report evidence rather than setting policy.
For a proposed expansion outside Desktop orchestration, stop scope creep and
obtain explicit user requirements before implementation. Do not silently add a
service, permission grant, background task or installed artifact.
