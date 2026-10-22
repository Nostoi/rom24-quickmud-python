# Session Summary — 2026-07-16 — GL-050 probed+closed; FIGHT-099 link-dead recall fixed

## Scope

Autonomous loop iteration 3/10. Picked up **GL-050** (aggr_update victim
selection divergence with 2 PCs, observed 2026-07-16 but not root-caused). The
probe ran live against the instrumented C oracle (`src/diffshim`) via a new
differential scenario, root-caused the observation, and surfaced + closed a
new HIGH gap in `damage()`'s epilogue.

## Outcomes

### `GL-050` — ✅ CLOSED (probe: no aggr_update divergence)

- **Python**: `mud/ai/aggressive.py:aggressive_update` — verified faithful
  against `src/update.c:1077-1141` by code-read (reversed-registry watcher
  walk per GL-043, per-watcher rescan, reservoir `count++` outside the pick,
  room-people inner domain).
- **Root cause of the observed flip**: DB-005 boot-order registry divergence
  (fixed this loop, v2.14.323) desynced walk order + the shared RNG stream.
- **Lock**: new C-oracle scenario
  `tools/diff_harness/scenarios/aggr_two_pc_victim_selection.json` (driver +
  descriptorless grouped ally + aggressive mob 2302) — victim selection now
  converges byte-for-byte.

### `FIGHT-099` — ✅ FIXED (filed + closed this session)

- **Python**: `mud/combat/engine.py:apply_damage` (epilogue added)
- **ROM C**: `src/fight.c:978-991` — after damage lands, `victim == ch`
  guard, then a PC victim with `desc == NULL` rolls `number_range(0, wait)`;
  on 0 it `do_recall`s out of the fight ("$n prays for transportation!").
- **Gap**: Python had NO damage() epilogue — link-dead PCs just kept taking
  rounds (C oracle's ally recalled after the first hit; Python mauled it).
- **Tests**: `tests/integration/test_fight099_linkdead_recall_on_damage.py`
  (4, failing-first) + the scenario golden (99/99 differential).
- **Commit**: `e2ba759d` (v2.14.325).

### `FIGHT-100` — ⚠️ FILED OPEN

Wimpy auto-flee legs of the same epilogue (`src/fight.c:993-1012`): NPC
wimpy/charm flee + PC `hit <= wimpy` flee — both missing. RNG-bearing; row in
`FIGHT_C_AUDIT.md` with close route.

### Harness fidelity fix (ridealong)

`tools/diff_harness/pyreplay.py:_configure_test_character` now mirrors the C
shim's descriptor wiring (`diffmain.c:448-531`): the DRIVER gets a desc
sentinel (connected), `__group_pc` allies stay `desc=None` (link-dead).
Python's driver previously read as link-dead — every desc-gated ROM path
would have desynced.

## Fallout triage (CRITICAL blast radius — apply_damage)

11 tests failed order-dependently after the epilogue landed; all were
fixtures modeling *connected* players whose desc-less PC victims now
faithfully auto-recalled (ROM would do the same to a genuinely link-dead
victim). Fixed by attaching `desc` stubs with FIGHT-099 citations
(test_skills_damage ×3, test_fight_019, test_hpcnt, test_inv026,
test_check_assist_dispatch_scope, test_combat_damage_types,
test_skills_combat, test_combat_assist) and seeding one unseeded
ambient-RNG test (test_skills_detection lore — 2026-07-10 trip-flake
pattern).

## Files Modified

- `mud/combat/engine.py` — damage() epilogue (self-guard + link-dead recall)
- `tools/diff_harness/pyreplay.py` — driver/ally descriptor wiring
- `tools/diff_harness/scenarios/` + `tests/data/golden/diff/` — new scenario
- `tests/integration/test_fight099_linkdead_recall_on_damage.py` — new (4)
- 9 test files — fixture desc stubs / seed (see triage above)
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-099 ✅, FIGHT-100 filed OPEN
- `docs/parity/UPDATE_C_AUDIT.md` — GL-050 ✅ CLOSED (root causes recorded)
- `CHANGELOG.md`, `pyproject.toml` — 2.14.324 → 2.14.325

## Test Status

- Unit layer: **2798 passed, 1 skipped**; integration layer: **3429 passed,
  3 skipped** (run split due to an intermittent xdist worker-crash
  INTERNALERROR on full-suite runs — an infra flake, not test failures; the
  crashed runs reported phantom failures with no tracebacks).
- Differential harness: **99/99 across 66 scenarios** convergent.

## Next Steps

**FIGHT-100** (wimpy auto-flee legs) is the natural next gap — same ROM block,
fix pattern established, C oracle available for a wimpy-flee scenario.
