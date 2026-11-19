# Installation, diagnosis and recovery

Read this when installation is requested, diagnostics show residue, or the CLI is missing. Support Windows, macOS and Linux with Python 3.11+; full agent orchestration remains Codex Desktop-only.

## Identify the mode

- **Skill-only:** instructions exist, but no managed installation is recorded. Continue using the guidance and the unknown quota route; do not assume custom agents exist.
- **Complete:** `doctor --json` reports `installation_state: complete`. Use quota and the installed agent delegation gate. Account/model access is still determined by Codex at runtime.
- **Incomplete:** a manifest, launcher or agents exist, but required files/settings differ or are missing (service_tier preference does not count). Report the exact blocking `config_checks` keys and expected values, or failed artifact checks; distinguish configuration drift from missing/modified files and from quota-access failure. Preview repair from a reviewed source checkout with `install --dry-run`; install only when authorized. Preserve state/backups. Do not dispatch missing or invalid agents. Continue the user's task with available guidance unless its required review cannot be performed.

If the CLI is missing, inspect the known launcher location or run diagnostics from a source checkout before calling an existing full installation Skill-only. Default bin directory is `~/.local/bin`; Windows uses `codex-copilot.cmd`. `doctor` does not require PATH to pass when called by full path.

## Install or upgrade when requested

Clone `https://github.com/EricArcha/Codex-Copilot.git`, enter that directory and select a reviewed source version (public v1.0.0 Release is withdrawn; its source tag remains). For an existing checkout, preserve local work and fetch tags before selecting a release; do not overwrite or reset user changes. On Windows PowerShell:

```powershell
.\bin\codex-copilot.cmd install --dry-run
.\bin\codex-copilot.cmd install
& "$HOME\.local\bin\codex-copilot.cmd" doctor --json
```

On macOS/Linux:

```bash
./bin/codex-copilot install --dry-run
./bin/codex-copilot install
~/.local/bin/codex-copilot doctor --json
```

Default copy mode requires neither administrator rights nor symlink privileges. Explicit symlink mode is optional and Codex may reject symlinked agent files. Use copies for dependable agents. Upgrade from a source checkout; keep the installed runtime intact until the new installation succeeds.

Implicit invocation defaults to **off**; invoke the Skill explicitly with `$codex-copilot`.
With `on`, Codex may start the Skill by itself, loading instructions that can read quota
and create run state. The default avoids spending allowance on misfires. Change it with
`codex-copilot install --implicit-invocation on|off`. Check `doctor --json` →
`implicit_invocation` (`on`, `off`, or `unknown` without a recorded choice).
Use the Desktop acceptance checks below when verifying live behavior.
Upgrades preserve the recorded choice. Legacy installations without that field switch
from implicit invocation to `off` with a notice unless `--implicit-invocation on` is given.
Enabling it requires copy mode; symlink installs use the repository default `off`.

Installation previews all managed settings and artifacts; `--yes` confirms a reviewed plan for automation. Existing session authorization to install is sufficient; do not ask again merely because the CLI has a confirmation prompt. Without installation authorization, offer the appropriate commands and continue the task.

### Desktop chat installation and confirmation

Desktop chat is the primary workflow. When the user requests installation or
upgrade from chat, preview the source installer with the intended options
(preserve an existing symlink mode), run that authorized plan with `--yes`
and without `--set-default-model`, and verify it with the installed launcher's
`doctor --skip-quota --json`. Use the same verified absolute launcher for both
model commands below. The examples use its short name for readability.
Check the executing CLI catalog with `codex debug models`. If the shell's CLI
is older than Desktop's, locate and verify the Desktop-bundled CLI, then put
its directory first on PATH for these commands only. Use that same CLI for
preview and apply. Do not change persistent PATH.

After a successful install or upgrade, follow the scope of the user's request.
If the user already chose to keep the existing default or requested an upgrade
delivery that preserves it, verify that both the model and effort were preserved.
When the user is open to a model recommendation, run:

```text
codex-copilot default-model --json
```

When the result is `available`, ask in the current chat, in the user's
language: “Switch the default for new chats to this installation's
recommendation, <model> / <effort>, or keep your current settings?” Use the
model and effort from this result. Keep is the default, and permission to
install does not answer this question. Wait for an explicit affirmative reply
about that pair, then use only that preview's token:

```text
codex-copilot default-model --apply-plan <plan_token> --json
```

If the preview changed or the command declines the apply, keep settings as
they are and show any new recommendation for a fresh decision. If the result
is `current`, report that the model already matches; keep the configured
reasoning effort. If it is
`paused` or `unavailable`, report the reason and leave settings in place. Never
use the terminal's combined `--set-default-model` option to complete a chat
confirmation. Do not prompt or change the global default during ordinary
development tasks. Per-task model advice applies to the active task.

The installer reuses an existing `$CODEX_HOME/skills/codex-copilot`; otherwise its default is `~/.agents/skills/codex-copilot`. A verified current or known release Skill can be backed up and adopted. Unknown content, changed managed artifacts, and duplicate registrations block installation. Never delete a conflict without examining and backing it up. `CODEX_COPILOT_SKILLS_HOME` selects the parent directory explicitly; `CODEX_HOME` selects Codex configuration, not the default shared Skill directory.

Uninstall before changing the Codex configuration directory, Skill registration directory, or an owned persistent-PATH bin directory. Resolve the restored original Skill registration before reinstalling at a different location. This keeps original settings, backups and PATH ownership attached to the correct installation.

## PATH and executable discovery

Default installation does not modify PATH. In Windows PowerShell, enable the default directory for the current session:

```powershell
$env:PATH = "$HOME\.local\bin;$env:PATH"
```

For persistent Windows user PATH, preview and install with `--add-to-path`. It never edits system PATH and removes only its owned entry on uninstall. Open a new terminal after changing persistent PATH. Use the displayed bin directory if `CODEX_COPILOT_BIN_DIR` is set. On macOS/Linux configure your shell PATH yourself.

Windows launcher discovers `py -3` or `python` and requires Python 3.11+. It records no version-specific Python directory. Runtime metadata supports custom share/bin locations. Codex must be on PATH as a native executable or a standard npm wrapper with Node and its adjacent JS entry. Arbitrary batch wrappers fail with an actionable diagnostic. Quote shell metacharacters as required by the calling shell.

## Acceptance after install or upgrade

Verify the installed `--version` matches the selected release and `doctor --json` reports
complete with intact managed files. Use the displayed launcher path if PATH is
not configured. Repeating install from the same release should report no changes.
A complete installation verifies the managed files and settings. Model access is checked at runtime.

Before asking for a restart or a fresh chat, check the current conversation,
including the user's first message and any report that Desktop already restarted.
If the user confirms this is the post-restart chat and the expected Skill version
and requested behavior are observed here, close that check using this chat's
evidence. Treat older pending entries as dated observations. For the model
confirmation's Keep branch, verify the user's choice and unchanged settings in
the current chat.

Request a restart only when a specific, in-scope check requires a reload and
the evidence still leaves that reload outstanding. Name the missing behavior.
An earlier acceptance applies while the verified version and affected inputs
match, including when a later commit only changes unrelated files. Use
post-reload evidence for any affected behavior changed after that acceptance.
Installer dry runs and unchanged installs provide installation evidence.
A successful installer message about reloading agents or an invocation setting
applies to the named feature and should be checked against the current chat.

From 1.2.0, the managed installation adds `copilot_terra_worker` (Terra Medium,
L1 implementation only). Terra requires CLI 0.159.0+ and account model access.
Its new agent file is subject to the same conflict, fingerprint, rollback and
uninstall protections; do not replace an unknown file to complete an upgrade.
Use the Desktop reload check when verifying updated role discovery.
Parent-model routing recommendations apply to the active task.

`status --refresh --json` must show real quota windows with source=app-server.
For permission_denied, state_initialization_failed or state_write_failed, use
[quota access](quota.md): command-scoped host-approved execution for necessary
CLI/local-state access. Never change global sandbox policy. Resolve state access
before trace-writing delegation; Desktop observations cannot replace that gate.
Unresolved errors use unknown temporarily and are not successful quota acceptance.

From 1.3.0, upgrade managed Sol/Astra roles and the runtime together to the
GPT-6.2 pins. Inspect the executing CLI's `codex debug models` first; Desktop's
bundled CLI and a PATH CLI can differ. Missing model access must be reported;
never silently substitute an old model or widen a role. Checkpoint/finish active
old-model sessions before upgrade: history stays readable, but the new policy
rejects old-model resume/replay.

From 1.3.2, after an interactive install or upgrade, the installer separately
asks whether to apply this run's recommended model and reasoning effort for
new chats. It uses the routine development route with the current profile and
a fresh trusted quota cache if available (Unknown otherwise). Press Enter to
keep the existing settings. `install --yes` keeps them and prints the opt-in command.
Use `codex-copilot install --yes --set-default-model` to explicitly opt in now
or later. The executing CLI must verify the recommended model and effort. If
the current model already matches, the installer keeps the current effort.
When a new default was applied and the scope includes verifying it takes effect,
use the Desktop reload check above.

## Quota and recovery

Quota reads have a deadline and clean up their app-server process. Missing login, invalid responses, EOF, timeout or startup failure use only a valid recent successful cache, otherwise `unknown`; they never authorize larger delegation budgets. A fixture is for tests, not proof of account access. Measurement remains opt-in and off by default.

Uninstall by running `codex-copilot uninstall --dry-run`, then `codex-copilot uninstall`. Windows can use the full `.cmd` path. If the launcher is missing, re-clone and run the same subcommand with that platform's source launcher. Deleting the Skill manually does not restore managed settings.

Uninstall restores a setting only while its current value equals the managed installed value. Unchanged adopted Skills are restored from backup. User-modified artifacts are retained with a recovery manifest; resolve them and rerun uninstall from a source checkout. Preserve `~/.codex-copilot` or `CODEX_COPILOT_STATE_DIR` until recovery finishes. Unique backup directories include originals and `recovery.json`; interrupted installations may need manual restoration from these records. A locked file can prevent rollback too; report the exact recovery location and stop further installation attempts until resolved.

From source 1.0.1, installation preserves `service_tier` unchanged (including unset).
Historical ownership moves to `retired_config_changes`; uninstall does not restore
retired preferences. `features.fast_mode=false` and agent requirements remain managed.
Inspect doctor `config_checks` for exact keys and blocking impacts, `codex_runtime`
for the actual native/npm command resolution, and `runtime_available` separately
from file integrity. A complete installation can still have an unavailable runtime
or quota; a preference difference alone does not mean damaged files.

Before a real upgrade, preserve the previous config, manifest and runtime pointer
alongside the installer transaction backups. Rollback restores only this transaction's
files that still match the just-installed content; preserve later user edits and report
conflicts. Never replace a whole current Codex configuration to repair diagnostics.

Agent symlinks require both link and instruction-content fingerprints. Legacy
link-only records are unverified for dispatch; upgrade from a reviewed checkout
only if the target still matches that source, or use copy mode. Changed targets
remain protected from overwrite. Missing required manifest records also fail integrity.

A successful quota retry resolves only quota access; it does not repair managed settings.
After an authorized repair, rerun doctor and confirm complete installation independently
of live quota success. Existing agents and files alone do not prove valid configuration.
Do not infer when or which application changed a setting without evidence.
