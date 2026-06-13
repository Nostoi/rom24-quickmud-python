# Session Summary — 2026-06-12 — INV-046 PHANTOM-REGISTRY: family 3b (fully closed → ✅ ENFORCED)

## Scope

Picked up from v2.14.20 where INV-046 (PHANTOM-REGISTRY) had families 1, 2, the Layer-A
grep-guard, and 3a closed, with family 3b still open. Family 3b was the remaining set of
phantom *stat-table* aliases: immortal/info commands that read `getattr(registry, "<name>",
default)` for attributes `mud/registry.py` never defines (`skill_table`, `object_list`,
`areas`, `rooms`, `helps`, `socials`, `social_table`, `social_registry`, `player_registry`,
`note_boards`, `group_table`). Unlike family 3a's `mfind`/`ofind` crashes, these returned the
empty default silently — so `slookup`/`owhere`/`socials`/`groups` listed nothing, `memory`/`dump`
printed zero areas/rooms/helps/socials, `sset` silently no-op'd, and `peek` always resolved
skills to 0, all while tests injected the attributes to make the dead reads observable. The
session rewired every reader to its real backing structure, extended the Layer-A guard to ban all
13 phantom names, and flipped INV-046 to ✅ ENFORCED. Landed v2.14.21, 11 new tests, full suite
5655 passed / 4 skipped.

---

## Outcomes

### INV-046 family 3b — all phantom stat-table aliases rewired — ✅ FIXED → ✅ ENFORCED (2.14.21)

- **`slookup` `skill_table`** → `mud.skills.registry.skill_registry.skills` (name-keyed; ROM `sn`
  preserved via `enumerate`, slot via `skill.slot`). `slookup all` now lists the loaded skills.
  - **Python**: `mud/commands/imm_search.py` (`do_slookup`)
  - **ROM C**: `src/act_wiz.c:3191`
- **`owhere` `object_list`** → `mud.models.obj.object_registry`.
  - **Python**: `mud/commands/imm_search.py` (`do_owhere`)
  - **ROM C**: `src/act_wiz.c:1886`
- **`memory`/`dump` `areas`/`rooms`/`helps`/`socials`** → `registry.area_registry` /
  `registry.room_registry` / `mud.models.help.help_entries` / `mud.models.social.social_registry`
  (counts were all silently 0 in production). The `dump` `areas`/`rooms` reads were **missed by the
  family-3a sweep** and caught here via the post-fix re-grep.
  - **Python**: `mud/commands/imm_search.py` (`do_memory`), `mud/commands/imm_server.py` (`do_dump`)
  - **ROM C**: `src/db.c:3289`
- **`count`/`whois` `player_registry` fallback** → `character_registry` PC filter (live PCs carry
  `pcdata`). `max_on_today` **promoted to a real `mud/registry.py` scalar** mirroring ROM's static
  `max_on`, so the dynamic stamp is legitimate rather than a phantom getattr.
  - **Python**: `mud/commands/info_extended.py` (`do_count`, `do_whois`), `mud/registry.py`
  - **ROM C**: `src/act_info.c:2228` (do_count + static `max_on`)
- **`unread` `note_boards` + `pcdata.last_read`** → `mud.notes.board_registry` + `pcdata.last_notes`.
  - **Python**: `mud/commands/misc_player.py` (`do_unread`)
- **`sset` + `peek` skill lookup `skill_table` + `pcdata.learned[sn]`** → the canonical name-keyed
  `char.skills` store. The old writes/reads hit a dict the game never consults, so `sset` silently
  no-op'd and `peek` always resolved to 0. A **dead duplicate `remaining_rom._get_skill`** (no
  callers) was removed; the canonical `_get_skill` reads `char.skills`.
  - **Python**: `mud/commands/imm_set.py` (`do_sset`), `mud/commands/misc_player.py` (`_get_skill`),
    `mud/commands/remaining_rom.py` (dead `_get_skill` deleted)
  - **ROM parsing note**: `do_sset` parses the skill as a single `one_argument` prefix word
    (str_prefix match), so `sset <victim> acid 75` prefix-matches `"acid blast"`.
- **`socials` `social_table`** → `mud.models.social.social_registry` (answered "No socials found."
  despite the loaded table).
  - **Python**: `mud/commands/misc_info.py` (`do_socials`)
  - **ROM C**: `src/act_info.c:606`
- **`groups all` / `groups <name>` `group_table`** → `mud.skills.groups` (`list_groups`/`get_group`);
  also fixed the `.spells` field name to the real `GroupType.skills`, so groups list their member
  skills instead of "(none)".
  - **Python**: `mud/commands/remaining_rom.py` (`do_groups`)

### Layer-A grep-guard — extended to all 13 phantom names

- **`tests/test_phantom_registry_convention.py`** — added `_PHANTOM_NAMES` (13 names) +
  `_NAMES_ALT`; the attribute and getattr/hasattr/setattr/delattr regexes now ban every phantom
  alias under both `mud/` and `tests/`. `max_on_today` and the five real `*_registry` dicts are
  deliberately allowed. Two stale doc-string mentions (`test_olc_alist.py`,
  `test_skills_spells_cast_listing.py`, and a `misc_player.py` docstring) were reworded so the guard
  stays green.

---

## Files Modified

- `mud/commands/imm_search.py` — `do_slookup` (skill_registry), `do_owhere` (object_registry), `do_memory` (area/room/help/social counts)
- `mud/commands/imm_server.py` — `do_dump` areas/rooms counts (the 2 sites family-3a missed)
- `mud/commands/imm_set.py` — `do_sset` writes `char.skills` with ROM prefix-match parsing
- `mud/commands/info_extended.py` — `do_count`/`do_whois` `character_registry` PC fallback; `max_on_today` stamp
- `mud/commands/misc_info.py` — `do_socials` → `social_registry`
- `mud/commands/misc_player.py` — `do_unread` → `board_registry`/`last_notes`; `_get_skill` → `char.skills`
- `mud/commands/remaining_rom.py` — `do_groups` → `mud.skills.groups`, `.spells`→`.skills`; dead `_get_skill` deleted
- `mud/registry.py` — added `max_on_today: int = 0` (ROM static `max_on`)
- `tests/integration/test_inv046_family3b.py` — NEW: 11 production-shape tests
- `tests/test_phantom_registry_convention.py` — guard extended to 13 phantom names
- `tests/integration/test_olc_alist.py`, `tests/test_skills_spells_cast_listing.py` — docstrings reworded
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-046 flipped ⚠️ PARTIAL → ✅ ENFORCED
- `CHANGELOG.md` — `[2.14.21]` Fixed entry
- `pyproject.toml` — 2.14.20 → 2.14.21

## Test Status

- `pytest tests/integration/test_inv046_family3b.py` — **11/11 passing**
- Full suite: **5655 passed / 4 skipped** (2026-06-12, v2.14.21), `ruff check .` clean
- `gitnexus_detect_changes()` — risk **low**, 0 affected processes

## Outstanding

- **WIZ-051** — `find_location` in `imm_commands.py` falls back to `get_obj_world` for object vnums
  but the world-object fallback is missing; surfaced earlier, not yet filed as a per-file gap in
  `ACT_WIZ_C_AUDIT.md`.
- **Two xdist flakes** — `test_ac_clamping_for_negative_values` and
  `test_hpcnt_fires_exactly_once_per_violence_tick` flaked under parallel execution in an earlier
  session; they did **not** appear in this session's full run. Root cause (likely cross-file fixture
  interaction or shared RNG state) still undiagnosed.
- **Process note (durable lesson):** the family-3a inventory missed 2 phantom sites that this
  session's post-fix re-grep caught (`do_dump` areas/rooms). After every phantom-class fix, re-grep
  the whole `mud/` tree before enabling the guard — a hand-built site inventory is not authoritative.

## Next Steps

1. INV-046 is fully closed (✅ ENFORCED). The phantom-registry bug class is locked by the Layer-A
   guard; no follow-up needed there.
2. **File WIZ-051** in `docs/parity/ACT_WIZ_C_AUDIT.md` (find_location missing `get_obj_world`
   fallback) and close it via `/rom-gap-closer`.
3. **Diagnose the two xdist flakes** — run each with `-n0` to isolate, then `-n auto` to reproduce.
4. Resume the cross-file invariants pass: fresh probe on mob memory (`src/fight.c` ATTACK_BACK /
   hunt), `weather_update` message fan-out order, and `update_handler` pulse cadence vs the Python
   tick scheduler.
