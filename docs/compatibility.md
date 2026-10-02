# Compatibility contract from 1.0.0

## Supported environment

The product supports Python 3.11+ with standard-library runtime dependencies on
Windows, macOS and Linux, in Codex Desktop. CI exercises Python 3.11–3.14 on all
three platforms. New Python versions require validation; no claim of automatic
future compatibility is made. Full workflow diagnostics require Codex CLI
0.147.0+ and a ChatGPT login. Account model availability is checked at runtime.
The external Skill validator uses PyYAML; it is not a product dependency.

## Stable interfaces

Public CLI commands and existing JSON field names/types retain their meaning
through 1.x. New optional fields are allowed; clients must ignore unknown fields.
Existing success/failure exit-code behavior is preserved. Diagnostic prose is
not a parsing interface; use `error_category` and `retryable` for quota errors.
`retryable` means retry after resolving the condition or a later deliberate query,
not permission to poll or automatically retry.

Quota error categories: permission_denied, state_initialization_failed,
process_exit, authentication_failed, initialization_failed, timeout,
protocol_error, state_write_failed. A successful live observation stays
source=app-server even when caching fails; it carries state_write_failed.
Unknown observations remain source=unavailable. Fresh successful cache fallback
retains the existing 60-second bound and labels its source explicitly.

Hidden underscore commands, exact model IDs, effort routing and quota thresholds
are internal policy interfaces, not fixed forever. Changes still require release
notes, validated configurations and delegation-budget regression coverage.

## User data and upgrades

Never overwrite unknown files or replace the whole Codex configuration. Preserve
user edits, unrelated settings, measurement preferences and recorded history.
Uninstall restores only eligible managed values. Install confirmation is bound
to the inspected plan. Failed upgrades retain rollback/recovery evidence.

Support upgrade from 0.1.0 and 0.1.1 to 1.0.0 and from previously released 1.x
versions to later 1.x versions. Historical fixtures are immutable source snapshots.
Do not require downgrades to be supported; recovery uses installer backups and
journals, not overwriting user data with an older installation.

Product version, installer manifest schema, quota cache fields and measurement /
trace schemas evolve separately. Read supported old records with defaults for
new optional fields. Any incompatible persisted format needs a tested migration
and explicit release note; schema changes must not silently discard history.

## Permissions, trust and privacy

CLI reads official App Server quota itself. Desktop tool output may corroborate
status and supply existing measurement observations, but cannot authorize a
child or override the delegation gate. No caller-reported band or percentage
is accepted by the gate. Run-wide cumulative budgets and the most restrictive
observed band remain binding.

When sandbox permissions block a necessary CLI query or local state write,
request host-approved execution for that command. Do not modify global sandbox
policy, folder permissions or authentication files. Rejection/unavailability
uses explicit diagnostics and the unknown route. It is temporary degradation,
not the normal successful workflow. No polling or per-turn quota reads.

Child stderr is bounded in memory and discarded after classification. Raw stderr,
RPC errors, account secrets, paths and prompts must never enter metrics/trace or
persisted diagnostics. Measurement remains opt-in and does not erase records when
disabled. Reset credits are never suggested or redeemed by this Skill.

## Distribution and authority boundaries

The copied user runtime contains only src, skill, agents, bin and VERSION.
Repository governance, CI scripts, tests/fixtures, evidence and untracked user
files are not installed. Agent files declare validated roles; they cannot expand
model, effort, phase or host permissions independently of the runtime gate.
Documentation explains contracts; verification evidence cannot create policy.
Diagnostic recovery guidance requests command-specific host approval and never
performs privilege escalation itself. Measurement observes; delegation authorizes.
