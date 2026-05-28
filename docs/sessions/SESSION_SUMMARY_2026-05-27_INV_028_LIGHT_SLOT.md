# Session Summary — 2026-05-27 — INV-028 light-slot coherence + stale-test cleanup (2.9.84–2.9.86)

## Scope

Closed **INV-028 (LIGHT-SLOT-KEY-COHERENCE)** — the highest-value follow-up
filed at the end of the previous session (ARITH-202 close). Then ran the **full**
`pytest` suite (not just the integration subset prior sessions ran), which
surfaced 5 pre-existing unit-test failures; triaged and fixed all 5 as stale
tests left behind by ARITH-105 (2.9.72).

GitNexus remained unavailable all session (read-only index DB —
`Cannot execute write operations`); impact analysis used grep + targeted test
runs per CLAUDE.md's documented fallback. A `stash`/test side-effect twice
dirtied `data/areas/area.lst` (a test mutates it); reverted before each commit.

## Outcomes

### `INV-028` — ✅ ENFORCED (2.9.85; filing 2.9.84)

- **ROM C**: `src/act_obj.c:1415-1422 wear_obj` dispatches `ITEM_LIGHT` **first** (before any wear-flag branch) into the single `WEAR_LIGHT` slot via `equip_char(ch, obj, WEAR_LIGHT)`. `do_hold`/`do_wield`/`do_wear` all alias `wear_obj`. Readers: `src/handler.c:1504-1573` (room light) and `src/update.c:721-730` (PC burnout decay).
- **Bug**: the Python worn-light slot was keyed three inconsistent ways — `do_wear` routed `ITEM_LIGHT` through the HOLD-flag branch into `WearLocation.HOLD`; `Room._has_lit_light_source` read str `"0"`; `_find_equipped_light` matched only `"light"`/int-`LIGHT`. Net: PC lights never burned out and PC-held lights were mis-counted in room lighting vs ROM. (This is why the 2.9.81 ARITH-202 burnout fix could not take effect in live play.)
- **Fix** (`mud/commands/equipment.py`, `mud/models/room.py`, `mud/game_loop.py`):
  - `do_wear` gets an `item_type == ItemType.LIGHT` branch before the HOLD branch (mirroring ROM dispatch order) that equips into `int(WearLocation.LIGHT)` with the "lights $p and holds it" messages; removed the now-dead LIGHT special-case inside the HOLD branch.
  - `Room._has_lit_light_source` and `_find_equipped_light` now tolerate both the live `int(WearLocation.LIGHT)` key and the post-JSON-reload str `"0"` key.
- **Test**: `tests/integration/test_inv028_light_slot_key_coherence.py` (3 cases — do_wear → LIGHT slot **by key**; room.light increments on enter / decrements on leave; burnout tick decrements room.light and destroys the torch). All 3 verified failing pre-fix.
- **Collateral**: `tests/integration/test_equipment_system.py::test_wear_011_do_hold_auto_replaces_existing_held` asserted a held torch lands in HOLD — stale, since lights now correctly route to WEAR_LIGHT. Updated it to use non-light holdables (wands), preserving the HOLD auto-replace mechanic under test.
- **Followup (NOT closed by INV-028, documented in the tracker row + CHANGELOG)**: the broader `character.equipment` key-type inconsistency — live `int` keys vs reloaded `str` keys for *every* slot — remains open. INV-028 only reconciles the LIGHT slot (by making both LIGHT readers tolerant). A future pass should normalize equipment keys on load.

### 5 stale stat-floor tests — ✅ FIXED (2.9.86)

Root cause (one): ARITH-105 (2.9.72) changed `Character.get_curr_stat` to floor
at **3** (ROM `URANGE(3,...,25)`, `src/handler.c:872`); `MobInstance.get_curr_stat`
still floors at 0 (ROM-faithful for NPCs). Tests that set `perm_stat=[0,...]`
expecting stat 0 now see a +3 (PC) residual. No implementation bug. Each
expected value was re-derived from the actual handler formula (not trusted from
the triage subagent):

- `test_player_stats.py::...test_get_curr_stat_clamps_to_minimum_0` → renamed `..._minimum_3`; STR 5−10=−5 and INT 3−5=−2 now read **3**.
- `test_skill_combat_rom_parity.py::test_bash_size_modifier_when_larger` → +3 (PC STR floor); 70 → 73.
- `...::test_bash_pc_dodge_penalty_applied` → both PCs floor STR/DEX to 3: pre-dodge 50+3−4=49, penalty 3*(75−49); −25 → −29.
- `...::test_disarm_weapon_skill_differential_modifier` → +`DEX(3)−2*STR(0)`; 70 → 73.
- `...::test_dirt_kicking_terrain_modifiers` → +3 DEX; 30 → 33. Replaced the brittle `assert_called_once()` (the success path calls `number_range`, a 2nd `number_percent`) with a blind-effect success check.

## Files Modified

- `mud/commands/equipment.py` — `do_wear` LIGHT branch; removed dead HOLD-branch LIGHT case.
- `mud/models/room.py` — `_has_lit_light_source` tolerates int + str LIGHT key.
- `mud/game_loop.py` — `_find_equipped_light` matches numeric-str LIGHT key.
- `tests/integration/test_inv028_light_slot_key_coherence.py` — new (3 cases).
- `tests/integration/test_equipment_system.py` — `test_wear_011` uses wands.
- `tests/test_player_stats.py`, `tests/test_skill_combat_rom_parity.py` — 5 stale tests.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-028 row ✅ ENFORCED + candidate block struck through.
- `CHANGELOG.md` — 2.9.84 / 2.9.85 / 2.9.86. `pyproject.toml` — 2.9.83 → 2.9.86.

## Test Status

- INV-028 suite 3/3; `test_equipment_system.py` + `test_room_light_tracking.py` + `test_player_stats.py` + `test_skill_combat_rom_parity.py` green (124 in the two skill/stats files).
- **Full suite (all layers) re-run at session end: 4889 passed, 4 skipped, 0 failed** in 486s — the 5 prior stat-floor failures resolved, no regressions.
- `ruff check` on changed files clean (pre-existing F401/F841 in `test_equipment_system.py` lines 22–653 and I001 in `mud/world/movement.py:1-17` remain parked).

## Outstanding / Next Steps

1. **Push approval** — local `master` is **9 commits ahead** of `origin/master` (GL-024 2.9.80 → this session's 2.9.86). Verify `git log origin/master..HEAD`. Not pushed.
2. **Equipment-dict key-type normalization** (the INV-028 followup) — live `int` vs reloaded `str` slot keys affect every slot, not just LIGHT. A focused pass should normalize on load (e.g. coerce keys to `int(wear_loc)` in `mud/models/conversion.py`/persistence restore) and drop the per-reader tolerance shims. Candidate INV or a persistence gap.
3. **`_wear_all` light handling** — `mud/commands/equipment.py:_wear_all` skips HOLD-flag items and has no LIGHT branch, so `wear all` won't equip a light (ROM's `wear all` → `wear_obj` → WEAR_LIGHT would). Minor adjacent gap; not covered by INV-028's single-item path.
4. **ARITH triage remaining** (7 ❌ MISSING): ARITH-004 (real level-0-weapon divergence), ARITH-017/018/019 (need scroll/wand/potion/mobprog dispatch verification before any N/A reclass), ARITH-114 (get_curr_stat per-race/class ceiling), ARITH-206/207 (`reset_handler` arg=0 semantics), ARITH-208 (UB-divisor policy).
5. **GitNexus read-only DB** — `gitnexus_impact`/`detect_changes` unavailable; reindex can't write. Fix DB perms/lock outside the session.
6. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`. **Test side-effect**: some test mutates `data/areas/area.lst` (removes the `test.json` line) — revert before committing.
