# S01 evidence matrix

**State:** ACCEPTED (2026-10-28; acceptance criteria unchanged)
**Stage:** s01-review-followups
**Authority:** [spec.md](spec.md), [validation-plan.md](validation-plan.md)
**Last governed baseline:** 720a881589aa9eb18ef5abca241520b24fd6f850

| Requirement | Implementation owner | Implementation | Evidence | Verifier | Review/head | Status |
|---|---|---|---|---|---|---|
| S01-REQ-1 | executor (U3) | `aade150` | [Batch handoff](stage-handoff.md): fresh-review denial, follow-up/grant controls + G1; [stage review](stage-review.md): 200-case permission matrix PASS | independent L3 reviewer | `88ff1c4`, REQ-1 PASS | ACCEPTED |
| S01-REQ-2 | executor (U2) | `b7d1c52` | [Stage review](stage-review.md): six boundary cases, unchanged existing boundary test, documentation + G1 PASS | independent L3 reviewer | `88ff1c4`, REQ-2 PASS | ACCEPTED |
| S01-REQ-3 | executor (U5) | `915c92e` | [Stage review](stage-review.md): startup rule preservation + G2 PASS | independent L3 reviewer | `88ff1c4`, REQ-3 PASS | ACCEPTED |
| S01-REQ-4 | executor (U4); F-01 repair executor | `ad61c51`; repair `2a2366d` | [Batch handoff](stage-handoff.md): defaults/migration/rollback tests; [repair handoff](handoff-r01.md) and [repair review](review-r01.md): installed-launcher switch, confirmation and safety PASS; [M-01](validation-plan.md) COMPLETE | independent L3 repair reviewer; repository owner for M-01 | `a15fd38`, repair ACCEPT; manual 2026-10-28 | ACCEPTED |
| S01-REQ-5 | executor (U1) | `a672dfd` | [Batch handoff](stage-handoff.md): consistency test + scratch drift failure; [stage review](stage-review.md): REQ-5 PASS | independent L3 reviewer | `88ff1c4`, REQ-5 PASS | ACCEPTED |
| S01-REQ-6 | executor (U6) | `06177bd` | [Stage review](stage-review.md): release notes, G3 and unchanged VERSION PASS | independent L3 reviewer | `88ff1c4`, REQ-6 PASS | ACCEPTED |

## Acceptance basis (2026-10-28)

Original governed baseline above is retained as planning history; the executed
batch baseline is `f9057ce5d021a226b15586aa851eb1544cc8a161`. Original review
`88ff1c44d5d70e6b715e3b80c7ba7678adf2d193` remains NEEDS_REPAIR historically;
its sole finding F-01 is closed by the independently accepted repair in
`a15fd386c4bb06d5bc9c865aef8c7cf5ab42a308`. Neither review is rewritten.
Both handoff/review pairs pass the independent-review validator at closeout.

Manual M-01 is COMPLETE: off installation, owner-reported Desktop restart,
and successful explicit invocation in a new chat are recorded in the validation
plan. Automatic selection while on was not tested and is not M-01's criterion.
Closeout G1–G4 pass (219 tests; seven Windows-only skips, Skill validator,
release metadata and whitespace checks). Native Windows/Linux and other Python
versions remain outside local evidence; no release eligibility is inferred.

The repository owner authorized the acceptance record, commit and push. This
matrix consolidates existing independent verdicts and manual evidence; it does
not provide a new self-authored code-review verdict or alter requirements.
