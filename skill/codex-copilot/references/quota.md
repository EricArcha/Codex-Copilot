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

Doctor/status `quota_status` separates live `read_success` from `available`. A fresh
cache fallback has available=true but read_success=false; expired or unreadable
cache never authorizes a higher route. Inspect cache_status, failure phase and natural
process_exit_code alongside error_category; null is not evidence of a clean exit.
Doctor's legacy warning `ok=true` means the diagnostic can continue, not live success.
The client waits for initialize success before sending initialized and the quota read.
App Server EOF alone does not prove an installation defect or exhausted allowance.

## Bounded model batches

Bulk `model exec` uses the existing successful CLI quota cache (at most 60 seconds old)
and never starts a quota reader per evaluation turn. Use the planned Start or batch-boundary
status check; an expired/missing cache pauses calls, rather than causing automatic reads or
retries. Do not poll to keep it warm. After a permission change, make only the one targeted
host-approved reattempt already described above. A fresh cache-write warning still proves
live quota for native dispatch, but bulk execution needs the accessible trusted cache.

Execution-state writes are a separate fail-closed requirement: a live quota read cannot
compensate for an unavailable SQLite ledger. An optional run allowance guard uses the
trusted Start cache as its baseline, not Desktop-provided observations. Same-window deltas
are conservative account observations; crossing/resetting the window blocks that guard
instead of rebasing it. A route grant never overrides the observation limit. No guarantee
is made about an in-flight turn's cost or unobserved Desktop/other-account activity.
