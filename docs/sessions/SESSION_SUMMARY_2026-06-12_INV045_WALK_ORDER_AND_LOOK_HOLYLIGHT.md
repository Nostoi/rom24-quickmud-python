# Session Summary — 2026-06-12 — INV-045 walk-order class (GL-040/041/042) + LOOK-005/006 holylight bypasses

## Scope

Continuation from v2.14.9 (GL-039 closed). The session ran the three cross-file invariant probe
candidates listed in the previous handoff — `obj_update` timer-decay ordering, `affect_update`
count-down ordering, and `do_look`/`do_exits` room-darkness precedence.

Probe 1's ordering was clean, but inspecting the loop surfaced a whole divergence **class**: ROM
head-inserts every new entity into `char_list`/`object_list` (`src/db.c:2256-2257`,
`src/db.c:2482-2483`, `src/nanny.c:757-758`), so every ROM tick-loop walks **newest-first**, while
Python's `character_registry`/`object_registry` are append-order (oldest-first). With a shared
Mitchell-Moore RNG stream, walk order determines which entity consumes which roll — so every
forward walk desyncs all subsequent rolls vs C. Filed as **INV-045 (CHAR-LIST-WALK-ORDER)** and
closed its three tick-loop offenders (GL-040/041/042). Probe 2 was clean. Probe 3 found two
holylight gaps hidden behind stale-✅ audit rows (LOOK-005/006), both closed.

Five commits, five gap closures, one new INV row. v2.14.9 → 2.14.14; 5616 → 5626 tests.

## Probe Results

| Candidate | ROM C reference | Python equivalent | Verdict |
|-----------|----------------|-------------------|---------|
| `obj_update` timer-decay ordering | `src/update.c:913-1059` (gate `if (obj->timer <= 0 \|\| --obj->timer > 0) continue;`) | `mud/game_loop.py:obj_update` | ✅ ordering CLEAN — but the walk itself was oldest-first → **GL-040** |
| `affect_update` count-down ordering | `src/update.c:762-786` (NOT 330-420 as the handoff said — that's `gain_condition`/`move_gain`) | `mud/affects/engine.py:tick_spell_effects` | ✅ CLEAN — decrement-first contract matches; unconditional `number_range(0,4)` roll (GL-026) and same-type wear-off suppression preserved |
| `do_look` / `do_exits` room-darkness | `src/handler.c:2535-2550` (`room_is_dark`), `src/act_info.c:1065-1074`, `src/act_info.c:1404` | `mud/world/vision.py:room_is_dark`, `mud/world/look.py`, `mud/commands/inspection.py:do_exits` | ⚠️ `room_is_dark` precedence CLEAN (light → ROOM_DARK → INSIDE/CITY → SUN_SET/DARK); `do_exits` darkness handling CLEAN — but **LOOK-005/LOOK-006** holylight bypasses missing |

## Outcomes

### `GL-040` — ✅ FIXED (2.14.10, commit `2c631e41`)

- **Python**: `mud/game_loop.py:obj_update`
- **ROM C**: `src/update.c:919` + `src/db.c:2482-2483` (object_list head-insertion)
- **Gap**: `obj_update` iterated `object_registry` oldest-first; ROM walks `object_list`
  newest-first. Decay messages broadcast in reversed order and, with ≥2 decaying objects, any
  RNG-bearing path desyncs the shared Mitchell-Moore stream vs C.
- **Fix**: `for obj in list(reversed(object_registry))` with mid-loop extraction skip
  (`if obj not in object_registry: continue`) — a container's decay extracts its contents, which
  must then not be ticked, mirroring ROM's list re-linking.
- **Tests**: `tests/integration/test_update_c_parity.py::TestObjUpdateIterationOrder` (2 cases:
  newest-first decay-message order; extracted contents not ticked).

### `GL-041` — ✅ FIXED (2.14.11, commit `6b33ef1c`)

- **Python**: `mud/game_loop.py:char_update`
- **ROM C**: `src/update.c:661-786` + `src/db.c:2256-2257`, `src/nanny.c:757-758`
- **Gap**: `char_update` main walk was oldest-first — per-affect `number_range(0,4)` fade rolls,
  wander-home `number_percent`, plague/poison rolls consumed the RNG stream in reversed character
  order vs C whenever ≥2 characters were live.
- **Fix**: reversed walk + extraction skip. The GL-034 autoquit selection flipped from first-wins
  (forward-walk compensation) back to ROM's plain `ch_quit = ch` overwrite — last-wins on the
  newest→oldest walk lands on the OLDEST idler, exactly ROM.
- **Tests**: `tests/integration/test_update_c_parity.py::TestCharUpdateIterationOrder`
  (seed 20 → fade-roll draw order: newest char gets draw 0).

### `GL-042` — ✅ FIXED (2.14.12, commit `e7fbff20`)

- **Python**: `mud/ai/__init__.py:mobile_update`
- **ROM C**: `src/update.c:416` + `src/db.c:2256-2257`
- **Gap**: `mobile_update` walked oldest-first — shop-wealth `number_range(1,20)` pairs,
  scavenger `number_bits(6)`, wander `number_bits(3)`/door rolls drawn in reversed mob order.
- **Fix**: reversed walk + extraction skip, same pattern.
- **Tests**: `tests/integration/test_mob_ai.py::TestMobileUpdateIterationOrder`
  (seed 12345 → draws [1,19,13,12]; newest shopkeeper gets [1,19]).

### `INV-045` — ⚠️ PARTIAL (filed, 3 of 5 known sites closed)

- **Tracker**: `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — CHAR-LIST-WALK-ORDER
- **Contract**: every ROM `char_list`/`object_list` walk visits newest-first; Python registry
  walks must iterate `list(reversed(...))` wherever order is observable (RNG draws, first-match
  selection, select-one-per-tick).
- **Conforming**: `violence_tick` (pre-existing), `obj_update` (GL-040), `char_update` (GL-041),
  `mobile_update` (GL-042).
- **Remaining offenders** (next session): `mud/ai/aggressive.py:57` aggr walk (RNG-bearing);
  `mud/world/char_find.py:103` `get_char_world` first-match (returns OLDEST match where ROM
  returns NEWEST). Lower-stakes forward walks (broadcasts/wiznet/info listings) deferred —
  no RNG, order rarely observable.

### `LOOK-005` — ✅ FIXED (2.14.13, commit `a4954702`)

- **Python**: `mud/world/vision.py:check_blind`, `mud/commands/inspection.py:do_exits`
- **ROM C**: `src/act_info.c:542-556` (`check_blind`), `src/act_info.c:1404` (`do_exits` gate)
- **Gap**: ROM `check_blind` returns TRUE for `!IS_NPC && IS_SET(act, PLR_HOLYLIGHT)` *before*
  testing AFF_BLIND — blind holylight immortals still see. Python only tested AFF_BLIND, and
  `do_exits` bypassed `check_blind` entirely with a raw AFF_BLIND check. The audit row claimed
  "100% PARITY" at `mud/rom_api.py:check_blind` — a module that **no longer exists** (stale-✅).
- **Fix**: holylight short-circuit in `check_blind` (with the `!IS_NPC` guard — `ch->act` holds
  ACT_* bits on NPCs); `do_exits` now routes through `check_blind`.
- **Tests**: `tests/integration/test_look_holylight_rom_parity.py::TestCheckBlindHolylight`
  (4 cases incl. NPC-not-rescued guard).

### `LOOK-006` — ✅ FIXED (2.14.14, commit `237e894a`)

- **Python**: `mud/world/look.py` (`look`, dark-room gate)
- **ROM C**: `src/act_info.c:1068-1069`
- **Gap**: ROM's pitch-black gate is `!IS_NPC && !IS_SET(act, PLR_HOLYLIGHT) && room_is_dark`;
  the port dropped the holylight conjunct — a stale `TODO: Add PLR_HOLYLIGHT check` comment sat
  in its place even though `PlayerFlag.HOLYLIGHT` has existed in constants all along. The audit
  doc marked the gate ✅ FIXED while *quoting the ROM line containing the missing flag*.
- **Fix**: added the holylight conjunct to the gate.
- **Tests**: `tests/integration/test_look_holylight_rom_parity.py::TestDarkGateHolylight` (2 cases).

## Files Modified

- `mud/game_loop.py` — GL-040/GL-041 reversed walks + extraction skips; GL-034 autoquit overwrite
- `mud/ai/__init__.py` — GL-042 reversed walk + extraction skip
- `mud/world/vision.py` — LOOK-005 `check_blind` holylight bypass
- `mud/commands/inspection.py` — LOOK-005 `do_exits` routed through `check_blind`
- `mud/world/look.py` — LOOK-006 dark-gate holylight conjunct (stale TODO removed)
- `tests/integration/test_update_c_parity.py` — +2 test classes (GL-040/041)
- `tests/integration/test_mob_ai.py` — +1 test class (GL-042)
- `tests/integration/test_look_holylight_rom_parity.py` — new file (LOOK-005/006, 6 cases)
- `docs/parity/UPDATE_C_AUDIT.md` — GL-040/041/042 rows ✅ FIXED
- `docs/parity/ACT_INFO_C_AUDIT.md` — `check_blind` row corrected (stale `mud/rom_api.py` pointer
  + false "100% PARITY"), LOOK-005/006 filed and flipped ✅
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-045 CHAR-LIST-WALK-ORDER filed ⚠️ PARTIAL
- `CHANGELOG.md` — `[2.14.10]`–`[2.14.14]` entries
- `pyproject.toml` — 2.14.9 → 2.14.14

## Test Status

- `pytest tests/integration/test_update_c_parity.py` — green (incl. 3 new iteration-order cases)
- `pytest tests/integration/test_mob_ai.py` — green (incl. shop-wealth draw-order case)
- `pytest tests/integration/test_look_holylight_rom_parity.py -n0` — 6/6 passing
- Full suite: **5626 passed, 4 skipped** (after LOOK-006, 2026-06-12)

## Outstanding

- **INV-045 remaining offenders** (need own gap IDs + probe/close cycles):
  - `mud/ai/aggressive.py:57` — aggr_update walk is forward; RNG-bearing (attack rolls follow).
  - `mud/world/char_find.py:103` — `get_char_world` first-match walk returns the OLDEST matching
    character where ROM's newest-first walk returns the NEWEST (observable via `summon`, `gate`,
    immortal `goto` name targeting with duplicate names).
- Background GitNexus reindex flaked once with a silent exit-1 (7-line log, no error beyond the two
  known-benign `src/recycle.h`/`src/olc.h` header warnings); immediate retry succeeded. Watch for
  recurrence — if it repeats, capture the log before it's overwritten.

## Next Steps

Cross-file invariants pass continues. Concrete next tasks, in order:

1. **Close INV-045's `get_char_world` offender** — `mud/world/char_find.py:103`. ROM
   `src/handler.c:get_char_world` walks head-inserted `char_list`, so duplicate-name lookups
   resolve to the NEWEST character. Probe: two same-named mobs, assert `get_char_world` returns
   the newer. File as a gap ID in the relevant audit doc (HANDLER_C_AUDIT or char_find's home).
2. **Close INV-045's aggr-walk offender** — `mud/ai/aggressive.py:57`. ROM `aggr_update`
   (`src/update.c:1130+`) walks `char_list` newest-first; reverse the registry walk + extraction
   skip, same pattern as GL-040/041/042. Then flip INV-045 to ✅ ENFORCED (deferred forward walks
   documented as out-of-scope in the row).
3. **Fresh probe candidates** after INV-045 closes: mob memory (`src/fight.c` ATTACK_BACK / hunt),
   `update_handler` pulse cadence vs Python tick scheduler, `weather_update` message fan-out order.
