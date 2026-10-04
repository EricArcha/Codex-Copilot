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
Repository-root governance, CI scripts, tests/fixtures, evidence and user files
outside those product trees are not installed. The product trees are copied
recursively; they must contain only product content. Tag validation refuses
uncommitted/untracked content in those trees, preventing accidental release of
local additions. This is a release-source fence, not a Git-based runtime filter. Agent files declare validated roles; they cannot expand
model, effort, phase or host permissions independently of the runtime gate.
Documentation explains contracts; verification evidence cannot create policy.
Diagnostic recovery guidance requests command-specific host approval and never
performs privilege escalation itself. Measurement observes; delegation authorizes.

See [release-source checks](releasing.md) for ignored-file exclusions.

## Diagnostics and preference ownership from 1.0.1

`service_tier` is a user preference, not a Copilot dispatch requirement. Installation
never creates or changes it. Upgrades move prior ownership records into optional
`retired_config_changes` in manifest schema 2; missing means an empty list. Records
and backups remain available, but retired settings are not restored on uninstall.
Existing 0.1.x migrations retain their current tier rather than restoring the
pre-install value recorded by the old installer.

Required agent settings and `features.fast_mode=false` remain managed. Doctor
adds `config_checks` with key, expected/actual, missing, matches, impact and blocking;
only known related settings are displayed. Installation state describes managed
artifacts and required settings; `runtime_available` independently describes CLI,
Python, login and parseable configuration. It does not guarantee model entitlement
or available quota. Missing launcher PATH is an independent warning.

Doctor and status add `quota_status`: read_success, available, source, cache_status,
error_category, retryable, phase, process_exit_code and next_step. Doctor's warning
check `ok=true` means the diagnostic can continue, not that quota was obtained.
A live empty-window response can have read_success=true and available=false.
Cached observations always have read_success=false. Cache status is valid, expired,
missing, invalid, unreadable, write_failed or not_checked. Failure phase is startup,
initialize, quota_read or cache_write; a null exit code means no natural exit was
observed before cleanup. Successful reads have no failure phase. These diagnostics
are not serialized into quota-cache records and never enter metrics or trace.

Dispatch checks required settings before any quota override and verifies the
selected managed agent artifact when an installation manifest exists. Run-wide
cumulative authorization, model/effort policy and trusted quota acquisition remain
independent of diagnostic status. Diagnostic output does not grant host permissions.

New symlinked agent records also carry optional content_fingerprint in schema 2.
Link address and dereferenced instructions must both match. Legacy link-only agent
records cannot authorize dispatch: an upgrade can adopt them only when link identity
still matches and content equals the reviewed source, then records the content hash.
Copy mode keeps its existing whole-file fingerprints. Doctor checks that every
required artifact has a manifest record, including the runtime pointer. Direct
uninstall through 1.0.1 also preserves a tier still actively recorded by an old manifest.
