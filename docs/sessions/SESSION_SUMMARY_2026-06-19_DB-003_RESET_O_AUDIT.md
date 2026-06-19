# Session Summary — 2026-06-19 — DB-003: O-reset population audit (per-room one-copy / no arg2 cap)

## Scope

Picked up directly from `HANDOFF_2026-06-19_DB-003_RESET_O_AUDIT.md` (the prior
`/loop` session deliberately deferred DB-003 as audit-sized rather than forcing it
through `/rom-gap-closer`). This session executed that dedicated reset-path audit:
read ROM `reset_room`/`load_resets` whole, confirmed/refuted all three flagged
divergences, rewrote the Python O-branch to mirror ROM, redesigned a
ROM-impossible blocking test, and added a differential MUST check on shipped
areas. One audit-sized gap closed in one commit. Workflow: probe → TDD
(failing-first) → implement → differential gate → fallout triage → full suite.
Advisor consulted before implementation (flagged the `last_obj` refill path) and
the GitNexus MCP server confirmed live at session start (was down all prior day).

## Outcomes

### `DB-003` — ✅ FIXED

- **Python**: `mud/spawning/reset_handler.py` (`apply_resets` O-branch, ~502-545;
  removed `room_obj_targets` precompute at the old 385-389)
- **ROM C**: `src/db.c:1754-1786` (`reset_room` O-case), `src/db.c:1050`
  (`load_resets` `rVnum = arg3` for O)
- **Gap**: ROM places **at most one** instance of an object **per room** (skip on
  `count_obj_list(pObjIndex, pRoom->contents) > 0`) and applies **no global count
  cap** — `arg2`/`arg4` are unused for O. Python diverged two ways:
  - **(a) per-room over-placement** — a `room_obj_targets` precompute allowed one
    copy per O-reset *command*, so rooms with multiple same-obj O-resets spawned
    multiple copies. Reachable in shipped data: room 1333/obj 1307 and room
    8915/obj 8902 (2 copies each → now 1).
  - **(b) synthetic global cap** — `_resolve_reset_limit(arg2)` gated placement on
    the world object count, under-placing objects whose O-reset room-count exceeded
    arg2. Worse than documented: `object_counts` is seeded from the *entire existing
    world* (`_count_existing_objects`), so an obj already present anywhere could
    block even the first placement. Obj 3200 (15 O-resets) → now all 15 rooms get
    one copy.
  - **(c) suspected third divergence — CONFIRMED NON-EXISTENT.** The handoff flagged
    that ROM validates `pRoomIndex` from arg3 but places into `pRoom`. Resolved by
    reading `load_resets`: line 1050 sets `rVnum = arg3` for O, so the reset attaches
    to `get_room_index(arg3)` and `reset_room(pRoom)` runs with `pRoom == arg3's
    room`. `obj_to_room(pObj, pRoom)` is therefore necessarily arg3's room — Python
    keying placement off `arg3` is correct. No divergence.
- **Fix**: O-branch skips iff `existing_in_room` is non-empty (ROM
  `count_obj_list > 0`); `room_obj_targets`/`desired_total` removed; the
  `_resolve_reset_limit(arg2)` global cap removed for O. **The P
  key-refill-into-existing-container path is preserved** — the skip branch still
  points `last_obj` at the resident instance (advisor-flagged: ROM's P re-finds the
  container via `get_obj_type` = global last-created; Python's threaded `last_obj` +
  room-scan fallback achieves the same, but only if skip doesn't null it out).
- **Tests** (3 new + 1 redesigned, all pass):
  - `tests/test_db_resets_rom_parity.py::test_o_reset_same_room_duplicate_places_one`
    (divergence a, synthetic)
  - `::test_o_reset_ignores_global_arg2_cap` (divergence b, synthetic)
  - `::test_o_reset_population_matches_rom_on_shipped_areas` (**differential MUST**:
    real shipped world — rooms 1333/8915 → 1 copy, obj 3200 → 15 rooms one-each)
  - `tests/test_spawning.py::test_reset_P_targets_most_recent_container_instance`
    (redesigned from `test_reset_P_uses_last_container_instance_when_multiple`, whose
    2-desks-in-one-room premise is ROM-impossible → ROM-valid 1-desk-per-room across
    two rooms, asserting the key lands in the second/most-recently-created desk)
- **Gold-tier deferred (documented, not faked)**: a `tools/diff_harness/` C-run
  reset-population scenario is the enumeration-independent check, but the v1 harness
  has no reset/spawn scenario type (it covers look/movement/get-drop). Per-room
  object *counts* are RNG-independent (level-fuzzing only affects levels, not
  counts), so such a scenario would be deterministic if the harness gains reset
  support — left as future infra. The shipped-area test covers the must-tier.
- **Commit**: `f99fc78d` (v2.14.172).

## Files Modified

- `mud/spawning/reset_handler.py` — O-branch rewrite (one-per-room skip, drop arg2
  cap + `room_obj_targets` precompute); P refill path preserved
- `tests/test_db_resets_rom_parity.py` — +3 tests (2 synthetic, 1 differential)
- `tests/test_spawning.py` — redesigned the ROM-impossible P-container test
- `docs/parity/DB_C_AUDIT.md` — DB-003 row flipped 🔄 OPEN → ✅ FIXED
- `CHANGELOG.md` — added DB-003 `Fixed` entry
- `pyproject.toml` — 2.14.171 → 2.14.172

## Test Status

- Targeted: 5/5 (new + redesigned + existing O presence/nplayer checks)
- Reset/spawn/shop files: 145/145
- Full suite: **5889 passed, 4 skipped** (6:14)
- `ruff check` / `ruff format --check`: clean on changed files

## Next Steps

The reset/spawn divergence surface is nearly drained. The last entangled item is
**ARITH-208** (`mud/spawning/templates.py:172`, mob-hp `max(0, dice+bonus)` source
floor) — coupled to the policy-mandated UB-divisor floors
(`docs/divergences/UB_DIVISORS.md`); removing the source floor alone creates a new
sign divergence (`100*neg/1`), so it needs **coordinated source+divisor** treatment,
not a gap-closer commit. It is the natural follow-on to this reset/spawn audit.
Otherwise: pick up a feature-sized subsystem (BOARD-001 default board seeding, OLC
save paths) for fresh gap IDs, or open a new cross-file invariant probe (affect
ticks, position transitions, mob script triggers remain uncovered by an INV row).
