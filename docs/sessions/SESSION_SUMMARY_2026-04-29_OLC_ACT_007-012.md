# Session Summary — 2026-04-29 — `olc_act.c` IMPORTANT closures (OLC_ACT-007..012)

## Scope

Same-day continuation arc following the OLC_ACT-001..006 CRITICAL closures.
Goal: close the six IMPORTANT-severity gaps in `docs/parity/OLC_ACT_C_AUDIT.md`
covering `*_show` formatting parity (007/008/009/010), success-message
string drift (011), and missing `aedit_reset` (012). Per session strategy,
work was attempted with one-gap-per-subagent dispatch (Haiku for the small
string-drift gaps, Sonnet for the larger `_show` rewrites). Sonnet
subagents terminated mid-investigation as observed in the prior session,
so OLC_ACT-008/009/010 were closed inline instead.

## Outcomes

### `OLC_ACT-007` — `aedit show` flags row ✅ FIXED

- **Python**: `mud/commands/build.py` (`_aedit_show`).
- **ROM C**: `src/olc_act.c:644-646`.
- **Fix**: Flags line emitted via `flag_string(AreaFlag, area.area_flags)`
  for ADDED/CHANGED/LOADING.
- **Tests**: `tests/integration/test_olc_act_007_aedit_show_flags.py` (5).
- **Commit**: `658b725`.

### `OLC_ACT-008` — `redit show` byte-parity ✅ FIXED

- **Python**: `mud/commands/build.py` (`_SECTOR_NAMES`, `_room_summary`).
- **ROM C**: `src/olc_act.c:1068-1236` + `src/tables.c:391-392`.
- **Fix**: `_SECTOR_NAMES` `WATER_SWIM`/`WATER_NOSWIM` → `swim`/`noswim`
  (was Python enum-name form). Exit line in `_room_summary` now emits the
  ROM two-space gap between `Key: [%5d]` and `Exit flags:` (ROM lines
  1184/1196 — single sprintf trailing space + strcat leading space).
- **Tests**: `tests/integration/test_olc_act_008_redit_show_parity.py` (4).
- **Commit**: `76575c9`.

### `OLC_ACT-009` — `oedit show` byte-parity + `show_obj_values` ✅ FIXED

- **Python**: `mud/commands/build.py` (`_oedit_show`, `_show_obj_values`,
  `_WEAR_FLAG_DISPLAY`, `_EXTRA_FLAG_DISPLAY`, `_APPLY_NAMES`,
  `_WEAPON_CLASS_NAMES`, `_format_wear_flags`, `_format_extra_flags`,
  `_format_weapon_special`, `_format_container_flags`,
  `_format_furniture_flags`, `_format_portal_flags`, `_coerce_int`).
- **ROM C**: `src/olc_act.c:2733-2812` (`oedit_show`) +
  `src/olc_act.c:2210-2374` (`show_obj_values`) +
  `src/tables.c:434-483` + `src/merc.h:1205-1231` + `src/tables.c:489-516`.
- **Fix**: `_oedit_show` rewritten to ROM byte order (Vnum/Type/Name/Area/
  Short/Long/Wear/Extra/Material/Weight/Cost/Level/Affects/ExtraDesc).
  `_WEAR_FLAG_DISPLAY` (17 entries) and `_EXTRA_FLAG_DISPLAY` (23 entries,
  T-bit omitted) hand-tabled to ROM-faithful labels (`finger`/`nosac`/
  `wearfloat`/`antigood`/`rotdeath` — not Python enum names).
  `_APPLY_NAMES` covers 26 affect codes with the
  `APPLY_SAVES`/`APPLY_SAVING_PARA` index-20 collision resolved to
  `saves`. `_show_obj_values` ports 13 ITEM_* cases (LIGHT, WAND/STAFF,
  PORTAL, FURNITURE, SCROLL/POTION/PILL, ARMOR, WEAPON, CONTAINER,
  DRINK_CON, FOUNTAIN, FOOD, MONEY). WAND/STAFF/SCROLL/POTION/PILL spell
  fields emit raw value-index until a skill-by-index registry lands.
- **Tests**: `tests/integration/test_olc_act_009_oedit_show_parity.py` (8).
- **Commits**: `dfcdef3`, `a5a1c0a` (import sort).

### `OLC_ACT-010` — `medit show` byte-parity ✅ FIXED (partial)

- **Python**: `mud/commands/build.py` (`_medit_show`, `_format_intflag`,
  `_format_position`, `_format_size`, `_format_sex`).
- **ROM C**: `src/olc_act.c:3519-3699`.
- **Fix**: `_medit_show` rewritten to ROM row order: Name/Area, Act flags,
  Vnum/Sex/Race, Level/Align/Hitroll/DamType, conditional Group, Hit/Damage/
  Mana dice, Affected by, Armor (4 columns), Form/Parts/Imm/Res/Vuln/Off,
  Size, Material, Start/Default position, Wealth, Short/Long/Description.
- **Sub-gaps deferred** (recorded in `docs/parity/OLC_ACT_C_AUDIT.md`):
  - **OLC_ACT-010b** — dice/AC byte format (Python data model stores
    strings; ROM stores 3 ints per dice).
  - **OLC_ACT-010c** — shop/mprogs/spec_fun rendering (needs MobShop /
    MProg model alignment + `spec_name` lookup).
  - **OLC_ACT-010d** — ROM-faithful flag-table name strings for 10 mob
    flag tables (analogous to OLC_ACT-009's display tables).
- **Tests**: `tests/integration/test_olc_act_010_medit_show_parity.py` (8).
- **Commit**: `a962fc3`.

### `OLC_ACT-011` — `*_name` success messages ✅ FIXED

- **Python**: `mud/commands/build.py` (`_aedit_name`, `_redit_name`,
  `_oedit_name`, `_medit_name`).
- **ROM C**: `src/olc_act.c:683-700`/`1770-1787`/`2990-3010`/`3913-3931`.
- **Fix**: All four builders return ROM-exact `"Name set."` (was Python-
  verbose `"Area name set to: X"` / `"Room name set to X"` / `"Object
  name (keywords) set to: X"` / `"Player name set to: X"`).
  Existing assertions in `tests/test_olc_aedit.py` / `test_olc_medit.py`
  / `test_olc_oedit.py` updated.
- **Tests**: `tests/integration/test_olc_act_011_name_messages.py` (4).
- **Commit**: `d435650`.

### `OLC_ACT-012` — `aedit reset` subcommand ✅ FIXED

- **Python**: `mud/commands/build.py` (`_interpret_aedit` `reset` branch).
- **ROM C**: `src/olc_act.c:653-663` (`aedit_reset`).
- **Fix**: `reset` keyword wired — calls `apply_resets(area)` via the
  existing `_apply_resets_for_redit` wrapper, sets `area.changed=True`,
  returns ROM-exact `"Area reset."` (previously fell through to
  `"Unknown area editor command: reset"`).
- **Tests**: `tests/integration/test_olc_act_012_aedit_reset.py` (1).
- **Commit**: `3eec52e`.

## Files Modified

- `mud/commands/build.py` — substantial extensions: new imports
  (`ATTACK_TABLE`, `LIQUID_TABLE`, `ContainerFlag`, `ExtraFlag`,
  `FurnitureFlag`, `PortalFlag`, `Position`, `WeaponFlag`, `WeaponType`);
  display tables (`_WEAR_FLAG_DISPLAY`, `_EXTRA_FLAG_DISPLAY`,
  `_APPLY_NAMES`, `_WEAPON_CLASS_NAMES`); helpers
  (`_format_wear_flags`/`_format_extra_flags`/`_format_weapon_special`/
  `_format_container_flags`/`_format_furniture_flags`/
  `_format_portal_flags`/`_format_exit_flags_raw`/`_coerce_int`/
  `_show_obj_values`/`_format_intflag`/`_format_position`/
  `_format_size`/`_format_sex`); `_oedit_show` and `_medit_show`
  rewritten; `_SECTOR_NAMES` and `_room_summary` exit line corrected;
  four `*_name` success messages aligned; `aedit reset` wired.
- `tests/integration/test_olc_act_007_aedit_show_flags.py` — new (5).
- `tests/integration/test_olc_act_008_redit_show_parity.py` — new (4).
- `tests/integration/test_olc_act_009_oedit_show_parity.py` — new (8).
- `tests/integration/test_olc_act_010_medit_show_parity.py` — new (8).
- `tests/integration/test_olc_act_011_name_messages.py` — new (4).
- `tests/integration/test_olc_act_012_aedit_reset.py` — new (1).
- `tests/test_olc_aedit.py` / `tests/test_olc_medit.py` /
  `tests/test_olc_oedit.py` — assertions updated to ROM format.
- `docs/parity/OLC_ACT_C_AUDIT.md` — rows OLC_ACT-007..012 flipped
  🔄 OPEN → ✅ FIXED. Three sub-gaps OLC_ACT-010b/c/d recorded.
- `CHANGELOG.md` — six new entries under `[Unreleased] → Fixed`.
- `pyproject.toml` — 2.6.78 → 2.6.84 (six patch bumps, one per gap).

## Test Status

- 30 new integration tests this session, all green.
- 149 OLC integration tests passing total (up from 132 baseline + new).
- Pre-existing baseline failures in `tests/test_olc_oedit.py` /
  `tests/test_olc_medit.py` (`*_creates_new_*_if_vnum_in_range`,
  `*_vnum_not_in_area_range`) verified pre-existing via `git stash`
  round-trip. Not regressions.
- Pre-existing ruff import-order warnings in `mud/commands/build.py`
  also verified pre-existing; not introduced this session.

## Commits this session

| SHA | Gap | Severity |
|-----|-----|----------|
| `658b725` | OLC_ACT-007 `aedit show` flags row | IMPORTANT |
| `76575c9` | OLC_ACT-008 `redit_show` byte-parity | IMPORTANT |
| `dfcdef3` | OLC_ACT-009 `oedit_show` + `show_obj_values` | IMPORTANT |
| `a5a1c0a` | (style) sort imports in OLC_ACT-009 test | — |
| `d435650` | OLC_ACT-011 `*_name` success messages | IMPORTANT |
| `3eec52e` | OLC_ACT-012 `aedit reset` subcommand | IMPORTANT |
| `a962fc3` | OLC_ACT-010 `medit_show` byte layout | IMPORTANT |

## Subagent reliability note (continued)

This session's planned dispatch was Haiku for the small string-drift
gaps (007/011/012) and Sonnet for the `_show` rewrites (008/009/010).
The Sonnet subagent for OLC_ACT-008 terminated mid-investigation, same
failure mode as the prior session. Inline pivot worked cleanly. Going
forward: assume Sonnet subagents are unreliable in this codebase for
multi-step parity work and reach for inline execution by default.

## Next Steps

`olc_act.c` IMPORTANT severity tier is now closed. Carried forward:

1. **OLC_ACT-013 / OLC_ACT-014 (MINOR)** — last two structural gaps in
   `OLC_ACT_C_AUDIT.md`. Should be quick follow-ups to put `olc_act.c`
   on a path to ✅ AUDITED.
2. **OLC_ACT-010b / 010c / 010d** — three sub-gaps recorded during the
   `_medit_show` rewrite (dice/AC byte format; shop/mprogs/spec_fun
   rendering; ROM-faithful flag-table names for 10 mob enums). Defer
   until the data-model alignment they require is in scope.
3. **OLC_ACT TIER C deep-audit pass** — ~78 functions still at
   "🔄 NEEDS DEEP AUDIT". Required before `olc_act.c` row can flip
   ⚠️ Partial → ✅ AUDITED.
4. **`olc_save.c` / `olc_mpcode.c` / `hedit.c` audits** — three
   remaining ❌ Not Audited rows in the OLC cluster.

Recommended next-session start: clear OLC_ACT-013/014 (small) and
then begin the `olc_save.c` audit to keep the OLC cluster moving
toward fully retired.
