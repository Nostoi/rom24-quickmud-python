# Session Summary — 2026-06-12 — INV-046 PHANTOM-REGISTRY: families 1, 2, Layer-A guard, family 3a

## Scope

Picked up from v2.14.16 where INV-046 (PHANTOM-REGISTRY) had just been filed but not started.
The full site inventory: `imm_commands.py` carried a divergent duplicate `get_char_world`/`get_char_room`
pair scanning `registry.char_list`/`registry.players` (attributes that do not exist on `mud/registry.py`
in production — only tests injected them); 17 additional reads spread across `imm_server.py`,
`imm_search.py`, `imm_emote.py`, `imm_load.py`, and `player_config.py`. The session closed the bug
class family-by-family across four commits, reaching v2.14.20 and 5648 tests.

---

## Outcomes

### Family 1 — `imm_commands.py` duplicate lookup pair removed — ✅ FIXED (2.14.17, `7bf297f2`)

- **Python**: `mud/commands/imm_commands.py` (`get_char_world`, `get_char_room` removed; re-exported from `mud.world.char_find`)
- **ROM C**: `src/handler.c:2194-2243` (`get_char_world`), `src/handler.c:2155-2192` (`get_char_room`)
- **Fix**: Deleted the divergent duplicate pair that read `getattr(registry, "char_list", [])` /
  `getattr(registry, "players", {})`. Replaced with `from mud.world.char_find import get_char_world, get_char_room`
  so all 25 callers (`imm_punish.py`, `imm_load.py`, `remaining_rom.py`, and the 22 intra-module
  commands) pick up the ROM-correct pair (can_see + whole-word `is_name` + roomless-skip + HANDLER-006
  newest-first walk) at no per-caller cost. Also fixed `CON_PLAYING` constant: `force all` was checking
  `connected != 0` but the port uses `CON_PLAYING = 1`; the old check skipped every live connection.
- **Tests**: `tests/integration/test_inv046_phantom_registry.py` — 6 new production-shape tests covering
  `do_freeze`, `do_notell`, `do_transfer`, `do_force` (by name), `do_force all`, `do_force players`.

### Family 2 — all phantom `char_list`/`players` walk sites rewritten — ✅ FIXED (2.14.18, `967fdb88`)

- **Python**: `mud/commands/imm_commands.py`, `mud/commands/imm_server.py`, `mud/commands/imm_search.py`,
  `mud/commands/imm_emote.py`, `mud/commands/imm_load.py`, `mud/commands/player_config.py`
- **ROM C**: `src/act_wiz.c:816-831` (transfer all), `src/act_wiz.c:4233-4278` (force players/gods),
  `src/act_wiz.c:2027-2084` (reboot/shutdown announce + save walk), `src/act_wiz.c:1950-2015` (mwhere),
  `src/db.c:3307,3358-3367` (do_memory/do_dump counts), `src/interp.c:331` (gecho),
  `src/act_comm.c:1658-1680` (die_follower)
- **Fix**:
  - `transfer all`: now walks `registry.descriptor_list` newest-first (ROM's `descriptor_list` walk
    with the optional location argument preserved).
  - `force players`/`force gods`: walk `character_registry` reversed (INV-045 newest-first order).
  - `force all`: additionally gated on `CON_PLAYING = 1` (the old `!= 0` accepted every state).
  - reboot/shutdown: announce via `do_echo` (the real descriptor walk), save via `descriptor_list`.
  - `mwhere`: no-arg branch walks `descriptor_list` with `can_see` + `can_see_room` + switched-body
    display; named branch walks `character_registry` reversed with `is_name`.
  - `do_memory`/`do_dump`: counts now read `character_registry` (live chars + pcdata players),
    `mob_registry`, `obj_registry` instead of phantom attrs (were silently 0 in production).
  - `gecho`: delegates to `do_echo` per `src/interp.c:331`.
  - `restore all`: phantom fallback deleted.
  - `player_config._die_follower`: replaced with canonical `mud.characters.follow.die_follower`.
- **Tests**: 6 additional production-shape tests appended to `tests/integration/test_inv046_phantom_registry.py`
  (tests 7–12 covering `do_reboot`, `do_shutdown`, `mwhere`, `do_force gods`, `do_gecho`, `do_restore`).

### Layer-A grep-guard — ✅ LANDED (2.14.19, `2d853ba4`)

- **New file**: `tests/test_phantom_registry_convention.py`
- **Pattern**: Forbids `registry.char_list` / `registry.players` attribute reads and
  `getattr/hasattr/setattr/delattr(..., "char_list"/"players")` calls under BOTH `mud/` (production)
  AND `tests/` (the test-injection side of the feedback loop). Same scanner shape as
  `test_equipment_key_convention.py`.
- **Cleaned**: ~60 phantom injection sites removed from 10 test files:
  `test_act_wiz_command_parity.py`, `test_flag_command_parity.py`, the four `test_inv025_*` files,
  `test_inv025_command_broadcast_pers_sweep.py`, `test_inv029_act_first_letter_cap.py`,
  `test_order_broadcasts.py`, `test_purge_broadcasts.py`. All fixtures/helpers now populate only the
  real `character_registry` (and the legitimate lazily-attached `registry.descriptor_list`).
- **Net**: the feedback loop is broken — new code reading a phantom attr will fail the guard before
  reaching CI; test authors cannot accidentally re-create a fake attr to paper over it.

### Family 3a — `mfind`/`ofind` crash + `memory`/`dump` zero counts — ✅ FIXED (2.14.20, `ac118d1d`)

- **Python**: `mud/commands/imm_search.py` (`do_mfind`, `do_ofind`, `do_memory`),
  `mud/commands/imm_server.py` (`do_dump`)
- **ROM C**: `src/act_wiz.c:1100-1140` (`do_mfind`), `src/act_wiz.c:1180-1220` (`do_ofind`),
  `src/db.c:3307,3340,3355` (`do_memory`/`do_dump`)
- **Fix**:
  - `do_mfind`/`do_ofind`: were reading `registry.mob_prototypes` / `registry.obj_prototypes`
    directly — `AttributeError` crash for every immortal `mfind`/`ofind` call in production.
    Rewired to `mob_registry` / `obj_registry` (the real names). Match logic also corrected:
    substring search on a nonexistent `name` field → ROM `is_name()` whole-word prefix match on
    `player_name` (mobs) / `name` (objects) per `src/act_wiz.c` argument handling.
  - `do_memory` / `do_dump`: `getattr(registry, "mob_prototypes/obj_prototypes", {})` silently
    returned `{}` (0 count) in production despite ~986 loaded mobs / ~1200 loaded objects.
    Corrected to `registry.mob_registry` / `registry.obj_registry` with ROM citation comments.
- **Tests**: `tests/integration/test_inv046_phantom_registry.py` — 3 new tests (13–15) covering
  `mfind` whole-word match (and non-match on mid-word), `ofind`, and `memory`/`dump` non-zero counts.

---

## Files Modified

- `mud/commands/imm_commands.py` — removed duplicate `get_char_world`/`get_char_room`; re-exported from `mud.world.char_find`; fixed `CON_PLAYING` guard in `force all`
- `mud/commands/imm_server.py` — `do_reboot`/`do_shutdown` announce + save via real structures; `do_dump` counts corrected
- `mud/commands/imm_search.py` — `mwhere` both branches rewritten; `do_mfind`/`do_ofind` crash fixed + `is_name` parity; `do_memory` counts corrected
- `mud/commands/imm_emote.py` — `gecho` → `do_echo` delegation
- `mud/commands/imm_load.py` — restore-all phantom fallback deleted
- `mud/commands/player_config.py` — `_die_follower` → canonical `die_follower`
- `tests/test_phantom_registry_convention.py` — NEW: Layer-A grep-guard
- `tests/integration/test_inv046_phantom_registry.py` — 15 production-shape tests (was 0)
- 10 test files cleaned of phantom injections (see Layer-A above)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-046 status updated through family 3a
- `CHANGELOG.md` — `[2.14.17]`–`[2.14.20]` entries
- `pyproject.toml` — 2.14.16 → 2.14.20

## Test Status

- `pytest tests/integration/test_inv046_phantom_registry.py` — **15/15 passing**
- Full suite: **5648 tests collected** (2026-06-12, v2.14.20)

## Outstanding

- **INV-046 family 3b** — remaining phantom stat-table aliases (all `getattr`-with-default, print
  zero/empty in production; not crash-severity):
  - `imm_search.py:157,201,357-362` — `areas`, `rooms`, `helps`, `socials`, `skill_table`,
    `object_list`, `social_registry`
  - `info_extended.py:127,131,252` — `player_registry`, `max_on_today`
  - `misc_player.py:236` — `note_boards`; `misc_player.py:272` — `skill_table`
  - `imm_set.py:354,363` — `skill_table`
  - `remaining_rom.py:303,323` — `group_table`
  - `misc_info.py:75` — `social_table`
- **WIZ-051** — `find_location` in `imm_commands.py` falls back to `get_obj_world` for object vnums
  but the world-object fallback is missing; surfaced mid-session, not yet filed as a per-file gap.
- **Two xdist flakes** — `test_ac_clamping_for_negative_values` and
  `test_hpcnt_fires_exactly_once_per_violence_tick` flake under parallel execution; root cause not
  yet diagnosed (likely cross-file fixture interaction or shared RNG state).

## Next Steps

1. **Close INV-046 family 3b** — extend the Layer-A guard in
   `tests/test_phantom_registry_convention.py` to also ban the family-3b aliases, then fix each
   call site (most map to real registry attributes or to "feature not yet ported" stubs that
   should return `"Not yet implemented.\n\r"`).
2. **File WIZ-051** in `docs/parity/ACT_WIZ_C_AUDIT.md` if not already present.
3. **Diagnose the two xdist flakes** — run them with `-n0` to isolate, then with `-n auto` to
   confirm the reproduction path.
4. After INV-046 is fully closed: fresh probe on mob memory (`src/fight.c` ATTACK_BACK / hunt),
   `weather_update` message fan-out order, and `update_handler` pulse cadence vs Python tick
   scheduler.
