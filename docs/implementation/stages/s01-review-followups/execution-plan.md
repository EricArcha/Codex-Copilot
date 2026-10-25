# S01 execution plan

**State:** FROZEN
**Stage:** s01-review-followups
**Authority:** [spec.md](spec.md); [stage manifest](README.md)
**Last governed baseline:** 84d3633 (revision r01: U1 owns `routing.md` model IDs)

## Read order for the executor

1. `AGENTS.md`, `CONTRIBUTING.md`
2. [stage manifest](README.md), [spec.md](spec.md), this plan, [validation-plan.md](validation-plan.md)
3. Only the source files named in the current unit row

## Before the first edit

Record the runtime capability handshake in the stage handoff: identity as `codex/<session-id>`, cwd, branch, `HEAD`, `git status --short`, Python version, and whether G1–G4 pass at the batch baseline. If any gate fails at the baseline, stop with a blocked checkpoint.

## Stage batch execution

| Order | Unit ID | Requirement IDs | Allowed paths | Checkpoint command/result required | Rollback boundary | Known dependency | Stop condition |
|---|---|---|---|---|---|---|---|
| 1 | U1 | S01-REQ-5 | tests/test_delegation.py, skill/codex-copilot/references/routing.md | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_delegation` -> OK | revert U1 commit | adopts the accepted dirty `tests/test_delegation.py` patch | test still fails after the two literal IDs are added, or any agent/config pair drifts (real drift: stop and report) |
| 2 | U2 | S01-REQ-2 | skill/codex-copilot/references/routing.md, tests/test_routing.py | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_routing` -> OK | revert U2 commit | U1 | thresholds in code differ from 60/30/10 |
| 3 | U3 | S01-REQ-1 | src/codex_copilot/execution.py, tests/test_execution.py, tests/test_delegation.py, skill/codex-copilot/references/routing.md, skill/codex-copilot/SKILL.md, docs/compatibility.md | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_execution tests.test_delegation tests.test_execution_cli` -> OK | revert U3 commit | U2 (same routing.md) | change requires editing delegation.py or alters another band's behavior |
| 4 | U4 | S01-REQ-4 | skill/codex-copilot/agents/openai.yaml, src/codex_copilot/installer.py, src/codex_copilot/cli.py, tests/test_installer.py, tests/test_cli.py, tests/test_native.py, tests/test_diagnostics.py, skill/codex-copilot/references/installation.md, README.md, README.zh-CN.md, docs/compatibility.md | `env -u PYTHONDONTWRITEBYTECODE PYTHONPATH=src python3 -m unittest tests.test_installer tests.test_cli tests.test_native tests.test_diagnostics` -> OK | revert U4 commit | U3 (same compatibility.md) | rollback cannot stay transactional; `known_skills.py` or the distribution would need editing |
| 5 | U5 | S01-REQ-3 | skill/codex-copilot/SKILL.md | G2 -> "Skill is valid!" | revert U5 commit | U3 (same SKILL.md) | a rule from step 2 cannot be placed without adding a new rule |
| 6 | U6 | S01-REQ-6 | CHANGELOG.md | `python3 scripts/check_release.py` -> exit 0 | revert U6 commit | U3, U4 (entries describe them) | release check rejects the CHANGELOG |

One commit per unit, message style `<type>: <summary>` matching the repository history. Run G1–G4 at implementation head, then write the stage handoff and stop at `REVIEW_READY`.
