# Session Summary — 2026-07-16 — FIGHT-098 closed (mob_hit area-attack char_list domain)

## Scope

Autonomous loop iteration 2/10. Picked up the "Next Intended Task" from the
prior status: **FIGHT-098** (`mob_hit`'s OFF_AREA_ATTACK sweep iterated
`room.people` in Python but ROM's global `char_list` from the room-head seed —
the FIGHT-095 sibling). Single gap-closer session per `/rom-gap-closer
FIGHT-098`.

## Outcomes

### `FIGHT-098` — ✅ FIXED

- **Python**: `mud/combat/engine.py:mob_hit` area-attack branch; new shared
  `mud/combat/engine.py:char_list_walk_from_room_head` (promoted from
  `assist.py`'s FIGHT-095-private helper; `assist.py` deduped to import it)
- **ROM C**: `src/fight.c:262-270` (`for (vch = ch->in_room->people; vch;
  vch = vch_next) { vch_next = vch->next; ... }` — global char_list link, not
  `next_in_room`), `src/db.c:2256-2257` (char_list head-insert, newest-first)
- **Gap**: FIGHT-098 — the sweep's iteration domain diverged: Python wrongly
  swung at same-room fighters NEWER than the room head (unreachable in ROM)
  and never visited cross-room fled-but-still-fighting chars (visited in ROM;
  the swing whiffs in one_hit's cross-room guard, FIGHT-097) — the identical
  INV-045 nested-walk class as FIGHT-095.
- **Fix**: sweep now iterates `char_list_walk_from_room_head(attacker)` (the
  reversed `character_registry` slice from the room head — newest-first ROM
  char_list equivalence), gate unchanged (`vch is not victim and vch.fighting
  is attacker`).
- **Tests**:
  `tests/integration/test_fight098_area_attack_char_list_domain.py` (3,
  failing-first: newer-than-head same-room fighter NOT swung at; cross-room
  fighter visited; unregistered-head fallback to room scope). Template:
  FIGHT-095's C-independent domain-lock pattern.
- **Commit**: `dee59869`.

## Files Modified

- `mud/combat/engine.py` — area sweep domain + shared helper
- `mud/combat/assist.py` — deduped: imports the shared helper
- `tests/integration/test_fight098_area_attack_char_list_domain.py` — new (3)
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-098 flipped ⚠️ OPEN → ✅ FIXED
- `CHANGELOG.md` — `Fixed` entry
- `pyproject.toml` — 2.14.323 → 2.14.324

## Test Status

- FIGHT-095/096/097/098 files — 11/11 passing
- Combat + group + differential suites — 141 passed, 1 skipped
- Full suite: **6222 passed, 4 skipped, 0 failed** (243s parallel)

## Notes

- A dedicated C-oracle differential scenario for the area sweep (an
  OFF_AREA_ATTACK mob + fled-but-still-fighting char) remains desirable but
  needs the instrumented C binary; deferred alongside DB-005's `__mob_census`
  scenario to a C-capture-enabled session (noted in the audit row).

## Next Steps

**GL-050** (`aggr_update` victim selection with 2 PCs in room) — needs a probe
before fixing (repro shape recorded in its row). Alternatives: HANDLER-009
(test-only `MobInstance.move_to_room` tail-append) or carry-overs (FIGHT-094,
DESC-001, OLC spell-name lookup, IS_BUILDER).
