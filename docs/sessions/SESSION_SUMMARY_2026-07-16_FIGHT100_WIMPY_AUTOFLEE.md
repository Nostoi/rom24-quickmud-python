# Session Summary — 2026-07-16 — FIGHT-100 closed (wimpy auto-flee on damage)

## Scope

Autonomous loop iteration 4/10. Closed **FIGHT-100** (filed last iteration):
the wimpy auto-flee legs of ROM `damage()`'s epilogue, completing the
`src/fight.c:978-1012` block started by FIGHT-099.

## Outcomes

### `FIGHT-100` — ✅ FIXED

- **Python**: `mud/combat/engine.py:apply_damage` (epilogue extended)
- **ROM C**: `src/fight.c:993-1012` — after the link-dead block: (a) NPC
  ACT_WIMPY at `hit < max_hit/5` on `number_bits(2) == 0` → `do_flee`; (b)
  charmed NPC with master in another room → `do_flee` (hp-independent); (c)
  PC with `0 < hit <= wimpy` → `do_flee`. All gated
  `wait < PULSE_VIOLENCE / 2`.
- **Fidelity details**: the NPC OR chain short-circuits, so `number_bits(2)`
  draws only when ACT_WIMPY is set (shared-RNG-stream faithful); `max_hit/5`
  via `c_div` (ARITH-208 precedent); the charm-master room compare uses
  identity (`is not`), mirroring ROM's pointer compare.
- **Tests**: `tests/integration/test_fight100_wimpy_autoflee_on_damage.py`
  (5, failing-first). Test-authoring finds: PCs pay a sector move cost on
  flee (FIGHT-061) so fixtures need `move > 0`; NPCs can't flee into
  ROOM_NO_MOB rooms (Temple 3001), so the door helper is NO_MOB-aware.
- **Commit**: `58c955f7` (v2.14.326).

### `FIGHT-101` — ⚠️ FILED OPEN

Python `do_flee` carries a **non-ROM wait-gate** ("You are still
recovering." when `wait > 0`) **and a non-ROM WAIT_STATE** (ROM `do_flee`
has neither). Reachable: ROM's wimpy auto-flee fires at wait 1..5, Python's
internal gate blocks it; and ROM never lags a fleer. Row in
`FIGHT_C_AUDIT.md` notes to verify whether the gate is a deliberate
command-dispatch compensation before removing.

## Files Modified

- `mud/combat/engine.py` — wimpy auto-flee legs
- `tests/integration/test_fight100_wimpy_autoflee_on_damage.py` — new (5)
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-100 ✅, FIGHT-101 filed
- `CHANGELOG.md`, `pyproject.toml` — 2.14.325 → 2.14.326

## Test Status

- Unit layer: **2798 passed, 1 skipped**; integration: **3434 passed,
  3 skipped** (+5). Zero fallout this time (charm-flee fixtures keep masters
  co-located; wimpy flags rare in fixtures).
- Differential harness: 99/99 across 66 scenarios.

## Next Steps

**FIGHT-101** (do_flee wait-gate/lag) needs a verification-first probe —
check whether Python's command dispatcher separately enforces wait (making
the in-function gate double-counting) before removing. Alternatives:
HANDLER-009 (test-only), deferred C-oracle scenarios (DB-005 census,
FIGHT-098 area-attack), carry-overs (FIGHT-094, DESC-001, OLC spell-name,
IS_BUILDER).
