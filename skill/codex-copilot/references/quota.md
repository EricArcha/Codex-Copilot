# Quota access in Desktop

The CLI reads official App Server quota for status, doctor, launch and delegation.
A functioning full workflow obtains actual windows; unknown is temporary failure.

Inspect `error_category` / `retryable` in `status --json`. If permission_denied,
state_initialization_failed or state_write_failed occurs in a restricted host,
explain the condition and use the host approval mechanism for command-scoped
execution of the necessary CLI query or state-writing operation. Apply this to
`_delegate` and measurement commands as well: both need their local state paths.
Only make one targeted reattempt after the permission context has changed; do
not poll or add per-turn quota reads. Never alter global sandbox policy, chmod
user directories, copy credentials or clear account state. If approval is denied
or unavailable, report it and follow unknown routing. Authentication failures
need a valid ChatGPT login; protocol errors need compatible installation.

Desktop's get_usage_limits can corroborate account status and supply the numeric
observations supported by optional measurement. It is not a trusted CLI bridge:
do not import its percentages into cache, claim that the CLI gate used them, or
bypass the gate. The gate independently refreshes official quota before every
child and retains cumulative budgets and the strictest observed band.

A cache-write warning with source=app-server still has authoritative live quota;
resolve state access before commands requiring trace persistence. stderr is only
classified in bounded memory; never copy raw errors into metrics or trace.

Normal acceptance: host-approved `status --refresh --json` has real windows and
source=app-server; the actual final-review dispatch gate uses app-server (or its
valid short-lived fallback). An unknown read is not a successful acceptance test.
