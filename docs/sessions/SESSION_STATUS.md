# Session Status — 2026-07-16 — C-oracle scenario batch + FIGHT-103 closed

## Current State

- **Active focus**: cross-file invariants / divergence-class probe mode,
  running as an autonomous 10-iteration loop (iteration 7 complete).
- **Last completed**: **C-oracle scenario batch** — DB-005 census, FIGHT-098
  area-attack domain (mutation-tested), FIGHT-100 wimpy auto-flee all locked
  against the live C engine; **FIGHT-103 ✅ FIXED** (fleer output channel:
  look-before-flee-lines + epilogue delivery), surfaced by the capture.
  Commits `8f782125`, `c04f1f29` (v2.14.329). New mirrored directives:
  `__mob_census` (py), `__mob_fight`, `__char_fight` (both). Loop history:
  iters 1-6 = DB-005, FIGHT-098, GL-050+FIGHT-099, FIGHT-100, FIGHT-101,
  FIGHT-102.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-07-16_CORACLE_SCENARIO_BATCH_FIGHT103.md](SESSION_SUMMARY_2026-07-16_CORACLE_SCENARIO_BATCH_FIGHT103.md)
- **Prior sessions (same date)**:
  [SESSION_SUMMARY_2026-07-16_FIGHT102_WAIT_GATE_SWEEP.md](SESSION_SUMMARY_2026-07-16_FIGHT102_WAIT_GATE_SWEEP.md),
  [SESSION_SUMMARY_2026-07-16_FIGHT101_FLEE_WAIT_GATE.md](SESSION_SUMMARY_2026-07-16_FIGHT101_FLEE_WAIT_GATE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.329 |
| Tests | **6239 passed, 4 skipped, 0 failed** (unit 2801 + integration 3438; layers run separately — intermittent xdist worker-crash INTERNALERROR on single full runs is an infra flake). |
| ROM C files audited | 43 / 43 |
| Differential harness | **102/102 across 69 scenarios** convergent |
| Push status | **Local only** — loop commits `29e9f99d`…`c04f1f29` (14 total incl. docs); operator to review + push/publish. |
| Active focus | Cross-file invariants / divergence-class probe (autonomous loop, 7/10) |

## Outstanding — deferred by design

- **FIGHT-094** (OPEN, carry-over) — `check_killer` placement. The most
  substantive remaining combat item; probe-then-close.
- **HANDLER-009** (OPEN, test-only) — `MobInstance.move_to_room` tail-append.
- Carry-overs: DESC-001, OLC spell-name lookup, IS_BUILDER, stray
  `data/quickmud.db` / `doc/game.db` cleanup.

## Next Intended Task

**FIGHT-094** — probe `check_killer` placement: grep its row in
`FIGHT_C_AUDIT.md`, read ROM `src/fight.c:check_killer` and every Python
call site, write the failing contract test, close via `/rom-gap-closer
FIGHT-094`. Fallback if blocked: HANDLER-009 (test-only, well-scoped).
