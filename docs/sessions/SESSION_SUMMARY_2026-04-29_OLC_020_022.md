# Session Summary — 2026-04-29 — `olc.c` OLC-020 + OLC-022 closures

## Scope

Continuation after the `string.c` 100% closure + OLC-023 session. Closed the
two remaining *unblocked* OLC gaps that did not require lifting the
`olc_act.c` sibling-audit hold: OLC-020 (`display_resets` per-command
formatting + pet-shop overlay + wear-loc/door flag decoding) and OLC-022
(`do_resets` `inside`/`room`/wear-loc/`random` subcommands + 6-line syntax
help). Both delegated to a single Sonnet subagent running sequentially in
the main repo (no worktree) — same file ownership avoided lane conflict.

OLC-016/017/018/019 remain gated on `olc_act.c` audit (held).

## Outcomes

### `OLC-020` — ✅ FIXED

- **Python**: `mud/commands/imm_olc.py:_display_resets` (extracted helper);
  shared lookups in new `mud/utils/olc_tables.py`.
- **ROM C**: `src/olc.c:973-1183`.
- **Fix**: faithful per-command (M/O/P/G/E/D/R) formatting with ROM `sprintf`
  column widths preserved (`%-13.13s` → `f"{s:<13.13s}"`). Pet-shop overlay
  re-splices `final[5]` to `'P'` when `vnum-1` has `RoomFlag.PET_SHOP`. M-reset
  tracks `pMob` across iterations so the next G/E reset prints its
  `short_descr`/`vnum`/`pShop` branch correctly. G uses
  `flag_string(wear_loc_strings, WEAR_NONE)` ("in the inventory"); E uses
  `arg3` decode. D-reset capitalizes `dir_name[arg2]` only — `door_resets`
  string stays lowercase per ROM `flag_string`. **ROM bug preserved**: bad
  mob/object/room references emit `strcat` + `continue`, which jumps past the
  `send_to_char` at ROM line 1179 — the error line is never displayed.
  Documented inline (`# mirroring ROM src/olc.c:1015 continue — skip send_to_char`).
- **Tests**: `tests/integration/test_olc_display_resets.py` (16 cases, green).
- **Commit**: `2db19de`.

### `OLC-022` — ✅ FIXED

- **Python**: `mud/commands/imm_olc.py:do_resets`.
- **ROM C**: `src/olc.c:1232-1469`.
- **Fix**: full ROM subcommand coverage:
  - `<n> obj <vnum> inside <containerVnum> [limit] [count]` → P-reset, with
    `ItemType.CONTAINER`/`CORPSE_NPC` validation ("Object 2 is not a
    container.\n\r" on miss).
  - `<n> obj <vnum> room` → O-reset; "Vnum doesn't exist.\n\r" on bad vnum.
  - `<n> obj <vnum> <wear-loc>` → G (WEAR_NONE) or E split via
    `wear_loc_flag_lookup`; "Resets: '? wear-loc'\n\r" on miss.
  - `<n> random <#exits>` → R-reset; 1..6 inclusive ("Invalid argument.\n\r"
    otherwise).
  - `<n> mob <vnum> [max#area] [max#room]` → optional max args (default 1).
  - 6-line syntax block on unrecognized subcommand under numeric arg1.
  - All terminators / line endings `\n\r` per ROM convention.
  - Removed pre-existing "obj action without subcommand → naive O reset" bug.
  - **Drive-by fix**: pre-existing code referenced
    `registry.mob_prototypes`/`obj_prototypes` — actual attributes are
    `mob_registry`/`obj_registry`. Corrected.
- **Tests**: `tests/integration/test_olc_do_resets_subcommands.py` (27 cases, green).
- **Commit**: `236fc15`.

## Files Modified

- `mud/utils/olc_tables.py` — NEW. `WEAR_LOC_STRINGS`/`WEAR_LOC_FLAGS`/
  `DOOR_RESETS`/`DIR_NAMES` data tables from `src/tables.c:355-572`, plus
  `wear_loc_string_for` / `wear_loc_flag_lookup` (prefix-lookup mirroring
  ROM `flag_value` stat-table behavior, src/bit.c:118-119) /
  `door_reset_string_for` helpers.
- `mud/commands/imm_olc.py` — `_display_resets` helper extracted; `do_resets`
  rewritten to ROM dispatch shape.
- `tests/integration/test_olc_display_resets.py` — NEW (16 cases).
- `tests/integration/test_olc_do_resets_subcommands.py` — NEW (27 cases).
- `docs/parity/OLC_C_AUDIT.md` — OLC-020 and OLC-022 rows 🔄 OPEN → ✅ FIXED.
- `CHANGELOG.md` — entries under `[Unreleased] Fixed`.
- `pyproject.toml` — 2.6.71 → 2.6.73 (one patch bump per gap).

## Test Status

- `pytest tests/integration/test_olc_*.py tests/integration/test_bit_*.py` —
  **99 / 99 passing** (~1.5s).
- Full suite not re-run this session.

## Commits this session

| SHA | Gap | Severity |
|-----|-----|----------|
| `2db19de` | OLC-020 `display_resets` | IMPORTANT |
| `236fc15` | OLC-022 `do_resets` subcommands | IMPORTANT |

## Next Steps

OLC-020 and OLC-022 close the unblocked OLC work. Carried-forward in priority
order:

1. **`olc_act.c` audit decision point** — OLC-016/017/018/019 (CRITICAL,
   `aedit`/`redit`/`oedit`/`medit` `create` subcommands) require
   `aedit_create`/`redit_create`/`oedit_create`/`medit_create` builders from
   `src/olc_act.c`. Lifting the hold means starting
   `/rom-parity-audit olc_act.c` next.
2. **OLC-021** (MINOR) — `add_reset` linked-list edge cases on negative/zero
   indices. Low priority cosmetic.
3. **README/AGENTS/SESSION_STATUS coordinated refresh** — README still says
   "13 of 43 files at 100%"; actual is now ~21/43 with `string.c` flipped
   the prior session. Per AGENTS.md Repo Hygiene, single coordinated commit
   (NOT bundled with parity work).
