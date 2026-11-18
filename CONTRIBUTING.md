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

## Choose a merge path

Cosmetic edits confined to `README.md` or `README.zh-CN.md` can go directly to
`main` when repository protections allow it. This covers typos, presentation
wording and ordinary link repairs. Changes to installation or usage instructions,
compatibility claims, version or release history, or governance use a PR.

For all other changes, sync with `main` and use a short `codex/` branch and PR.
Merge after the `pull_request` CI run covers the latest PR revision and all
applicable jobs and required reviews pass. The workflow runs on PRs, pushes to
`main`, and version tags. A feature branch push has no separate CI run.
The `main` run verifies the merged commit and gates publication. See the
[release policy](docs/releasing.md) for the full publication sequence.

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
