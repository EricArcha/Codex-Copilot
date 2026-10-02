# Contributing

Read [AGENTS.md](AGENTS.md), [compatibility](docs/compatibility.md) and
[release policy](docs/releasing.md) before changing public behavior.

Keep one writer. Use read-only bounded agents only through the Skill delegation
gate. Normal changes require focused verification and independent review when
required by the Skill; permission, installation/migration or delegation changes
are L3 and require an independent final review. Fix findings before merging.

Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`, the official
Skill Creator quick_validate.py against skill/codex-copilot, and
`python3 scripts/check_release.py`. Follow AGENTS.md for Windows commands.
Do installation experiments with all five path overrides in temporary directories.
Never write a developer's persistent PATH or reset account state to pass tests.

PRs describe the concrete problem, resulting behavior, compatibility impact,
tests and material limitations. Keep relevant evidence in docs/verification.md;
never include secrets or raw authentication/error output. Update CHANGELOG for
user-facing changes. Do not create new governance documents when an existing
rule can be clarified in its current home.

## Change boundary checklist

Each PR includes three brief statements: responsibility owner, interfaces/trust
boundaries changed, and exclusions. Explain why a new file belongs to that owner.
Keep normative rules in their owner documents listed in AGENTS.md; link instead
of duplicating. Verification records report evidence rather than setting policy.
For a proposed expansion outside Desktop orchestration, stop scope creep and
obtain explicit user requirements before implementation. Do not silently add a
service, permission grant, background task or installed artifact.
