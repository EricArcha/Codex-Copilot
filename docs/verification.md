# Verification evidence

Local validation on 2026-10-02 used Windows, Python 3.13.7 and Codex CLI 0.159.0-alpha.12.1.

- Baseline at `8df44bb`: 71 tests, 5 failures and 13 errors. The full installer rejected Windows; one error independently demonstrated missing symlink privilege.
- Updated full suite: 100 tests discovered; 95 passed and 5 skipped. Four skips require unavailable Windows symlink privilege; one executes the original POSIX-only 0.1.0 installer. Copy installation and business logic are not skipped. The final affected-module rerun also passed.
- The installed Skill Creator `quick_validate.py` accepted the updated Skill.
- Real app-server quota reads succeeded. Tests additionally verify unknown/cache degradation, malformed responses, EOF, timeout, partial lines and descendant cleanup. No quota fixture was used for the live check.
- Real copy installation adopted the verified existing Skill registration after backing it up, installed all six regular agent files and managed settings, and reported `doctor: complete`. Upgrading to the reviewed source and a subsequent no-change installation succeeded. Persistent user PATH was not modified.
- Isolated tests cover Unicode/space paths, `.cmd` arguments/exit codes, custom runtime paths, conflicts, backups, upgrade and uninstall restoration, edited files/settings, failed rollback and mocked user PATH ownership.
- An independent GPT-6.1 Sol High review found lifecycle issues; their reproductions now pass and no blocking findings remain. Model routing, privacy and delegation policies were retained.

GitHub Actions [run 36981531703](https://github.com/EricArcha/Codex-Copilot/actions/runs/36981531703) passed all 12 Windows, Linux and macOS test jobs with Python 3.11–3.14, plus the official Skill validation job. The first run exposed a macOS exited-process-group cleanup error; reaping the leader before signaling and unconditional pipe cleanup fixed it. The Windows runner explicitly enables and probes symlink capability; Linux/macOS additionally run the archived original 0.1.0 installer upgrade regression. Check the PR's latest Actions results for executed platform evidence.

All six agent configurations are verified, but configuration presence is not proof that every role/model can be dispatched by a freshly restarted Codex Desktop. This delivery did not execute all six roles, including the premium Astra role. Restart Desktop and open a new task before checking that runtime availability. Symlink installation on this local ordinary-user Windows account remains unavailable; default copy mode is verified.

Caught installation failures retain unique backups and a recovery journal. Forced process interruption and external file locks may require manual recovery. The persistent Windows PATH registry operation is opt-in and its lifecycle is tested using a mocked registry; no live user PATH write was performed during validation.

The archived fixture in `tests/fixtures/release-0.1.0.zip` contains the original source components and MIT license from commit `8df44bb92beb45a7e387a4a2cd9d7fe381ea9662`, for offline upgrade testing.
