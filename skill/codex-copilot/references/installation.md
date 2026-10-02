# Installation, diagnosis and recovery

Read this when installation is requested, diagnostics show residue, or the CLI is missing. Support Windows, macOS and Linux with Python 3.11+; full agent orchestration remains Codex Desktop-only.

## Identify the mode

- **Skill-only:** instructions exist, but no managed installation is recorded. Continue using the guidance and the unknown quota route; do not assume custom agents exist.
- **Complete:** `doctor --json` reports `installation_state: complete`. Use quota and the installed agent delegation gate. Account/model access is still determined by Codex at runtime.
- **Incomplete:** a manifest, launcher or agents exist, but required files/settings differ or are missing. Explain the failed checks; preserve state/backups. Do not dispatch missing or invalid agents. Continue the user's task with available guidance unless its required review cannot be performed.

If the CLI is missing, inspect the known launcher location or run diagnostics from a source checkout before calling an existing full installation Skill-only. Default bin directory is `~/.local/bin`; Windows uses `codex-copilot.cmd`. `doctor` does not require PATH to pass when called by full path.

## Install or upgrade when requested

Clone `https://github.com/EricArcha/Codex-Copilot.git`, enter that directory and select the desired released tag (currently `git checkout v1.0.0`). For an existing checkout, preserve local work and fetch tags before selecting a release; do not overwrite or reset user changes. On Windows PowerShell:

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

Installation previews all managed settings and artifacts; `--yes` confirms a reviewed plan for automation. Existing session authorization to install is sufficient; do not ask again merely because the CLI has a confirmation prompt. Without installation authorization, offer the appropriate commands and continue the task.

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

Restart Codex Desktop and open a fresh chat to load updated roles. Verify the
installed `--version` matches the selected release and `doctor --json` reports
complete with intact managed files. Use the displayed launcher path if PATH is
not configured. Repeating install from the same release should report no changes.
A complete installation verifies artifacts/settings, not model entitlement.

`status --refresh --json` must show real quota windows with source=app-server.
For permission_denied, state_initialization_failed or state_write_failed, use
[quota access](quota.md): command-scoped host-approved execution for necessary
CLI/local-state access. Never change global sandbox policy. Resolve state access
before trace-writing delegation; Desktop observations cannot replace that gate.
Unresolved errors use unknown temporarily and are not successful quota acceptance.

## Quota and recovery

Quota reads have a deadline and clean up their app-server process. Missing login, invalid responses, EOF, timeout or startup failure use only a valid recent successful cache, otherwise `unknown`; they never authorize larger delegation budgets. A fixture is for tests, not proof of account access. Measurement remains opt-in and off by default.

Uninstall by running `codex-copilot uninstall --dry-run`, then `codex-copilot uninstall`. Windows can use the full `.cmd` path. If the launcher is missing, re-clone and run the same subcommand with that platform's source launcher. Deleting the Skill manually does not restore managed settings.

Uninstall restores a setting only while its current value equals the managed installed value. Unchanged adopted Skills are restored from backup. User-modified artifacts are retained with a recovery manifest; resolve them and rerun uninstall from a source checkout. Preserve `~/.codex-copilot` or `CODEX_COPILOT_STATE_DIR` until recovery finishes. Unique backup directories include originals and `recovery.json`; interrupted installations may need manual restoration from these records. A locked file can prevent rollback too; report the exact recovery location and stop further installation attempts until resolved.
