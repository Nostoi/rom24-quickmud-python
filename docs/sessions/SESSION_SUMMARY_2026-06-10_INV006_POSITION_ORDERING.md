# Session Summary — 2026-06-10 — INV-006 Position-Ordering Sub-Contract

## Scope

Continuation from v2.13.82 (follow helpers dedup). Active pass: cross-file invariants.
Session picked up the two probe candidates from the previous handoff: (1) affect-tick
contracts and (2) position-transition edges.

**Affect-tick probe** — reading INV-015 showed the GL-026 RNG short-circuit and LIFO
msg_off dedup sub-contracts were already locked at v2.13.61 (`test_rng_slot_consumed_per_duration_positive_affect`
+ `test_msg_off_dedup_suppresses_all_but_last_same_type_affect` in
`test_inv015_affect_tick_lifecycle.py`). No new work needed there.

**Position-transition probe** — `stop_fighting` (ROM `src/fight.c:1438-1454`) sets
`fch->position` to `default_pos` (NPC) or `POS_STANDING` (PC) **then** calls
`update_pos(fch)`. The ordering is load-bearing: `update_pos` may override the reset
for negative-HP characters (INCAP/MORTAL/DEAD). The existing INV-006 test exercised
only characters with `hit=100`, leaving the downward-override case unlocked. Extended
INV-006 with two new enforcement tests that are mutation-discriminating (swapping the
two lines makes both go RED). Session ends at v2.13.83.

## Outcomes

### INV-006 position-ordering sub-contract — ✅ LOCKED (extended)

- **ROM C**: `src/fight.c:1448-1451` — `fch->position = IS_NPC ? default_pos : POS_STANDING;`
  then `update_pos(fch);`
- **Python**: `mud/combat/engine.py:stop_fighting` lines ~800-806 — same ordering
- **Gap before**: existing `test_inv006_fighting_pointer_coherence.py` only tested
  `hit=100` characters; the ordering contract was not pinned for negative-HP cases
- **Fix**: added two new tests to `tests/integration/test_inv006_fighting_pointer_coherence.py`:
  - `test_stop_fighting_npc_with_negative_hp_ends_at_dead_not_default_pos` — NPC with
    `hit=0` must end at `DEAD`, not `default_pos`/`STANDING` (proves `update_pos` ran
    after the reset, overriding it)
  - `test_stop_fighting_pc_with_negative_hp_ends_at_incap_not_standing` — PC with
    `hit=-5` must end at `INCAP`, not `STANDING`
- **Mutation check**: swapped the two lines in `stop_fighting` (update_pos first, then
  reset), confirmed both new tests go RED (`<Position.STANDING: 8> != <Position.INCAP: 2>`)
  before restoring the correct order
- **Tracker**: INV-006 row updated with sub-contract description and cross-ref to INV-019
  (upward direction of the same `stop_fighting → update_pos` edge: STUNNED → STANDING
  promotion on positive-HP)
- **Tests**: `pytest tests/integration/test_inv006_fighting_pointer_coherence.py` —
  **4/4 passing** (was 2)

## Files Modified

- `tests/integration/test_inv006_fighting_pointer_coherence.py` — 2 new tests (+66 lines)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-006 row extended with
  position-ordering sub-contract and cross-ref to INV-019
- `CHANGELOG.md` — `[2.13.83]` Fixed entry
- `pyproject.toml` — 2.13.82 → 2.13.83

## Test Status

- `pytest tests/integration/test_inv006_fighting_pointer_coherence.py -v` — **4/4 passing**
- Full suite: **5550 passed, 4 skipped** (was 5548; +2 new enforcement tests)

## Next Steps

Cross-file invariants remains the active pass. Next free INV ID: **INV-042**.

Both session probe candidates are now resolved:
- ✅ Affect-tick contracts (GL-026 / msg_off dedup) — already locked in INV-015 at v2.13.61
- ✅ Position-transition edges (`stop_fighting` ordering) — locked now as INV-006 sub-contract

Remaining probe candidates (none yet covered by an INV row):

1. **`mob_update` loop contracts** — ROM `src/update.c:893-983` iterates `char_list`
   (snapshot-safe via `ch_next`), runs mob AI (aggressive/scavenge/wander), and calls
   `set_fighting`. Cross-file contract: mob AI must not mutate `character_registry` in
   a way that makes `list(character_registry)` snapshots stale mid-iteration. Python
   uses `list(character_registry)` snapshot in `mob_update` (similar to `char_update`
   INV-017); probe method: read `mud/game_loop.py:mob_update` vs. `src/update.c:893-983`.
2. **Group XP delivery ordering** — `group_gain` runs before `TRIG_DEATH` in `raw_kill`;
   INV-031 covers group preservation on death but not the XP-then-trigger ordering contract.
3. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
