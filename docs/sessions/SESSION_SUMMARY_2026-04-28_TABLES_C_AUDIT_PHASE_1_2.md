# Session Summary — 2026-04-28 — `tables.c` audit Phase 1 + Phase 2 (⚠️ Partial)

## Scope

Audit of `src/tables.c` (750 lines, 38 data tables) — pure data file consumed by ROM's flag-name `flag_lookup`/`flag_string` machinery. Goal: verify each ROM table has a Python equivalent in `mud/models/constants.py` and that bit values + names match. Audit framework adapted: `tables.c` is data-shaped, not function-shaped, so Phase 2 verifies value/name equivalence rather than function-by-function behavior.

## Outcomes

### Phase 1 inventory — ✅ COMPLETE
All 38 ROM tables catalogued in `docs/parity/TABLES_C_AUDIT.md` with Python equivalents.

### Phase 2 spot-checks — ✅ PARTIAL
- `ActFlag`, `PlayerFlag`, `OffFlag`, `CommFlag`, `RoomFlag`, `AreaFlag` — values match ROM letter assignments (verified by inline `# (X)` comments).
- `AffectFlag` — **values DIVERGE** from ROM `merc.h:953-982`. CRITICAL finding.
- 30+ remaining tables marked ⚠️ to verify in follow-up.

### `TABLES-001` — 🔄 OPEN (deferred, CRITICAL)
- **ROM C**: `src/merc.h:953-982` (AFF_* defines), `src/tables.c:130-160` (affect_flags table).
- **Python**: `mud/models/constants.py:548-580` (`AffectFlag`).
- **Bug**: ROM `AFF_DETECT_GOOD=G=1<<6`, but Python `AffectFlag.SANCTUARY=1<<6`. All bits 6..29 are misaligned. `mud/models/constants.py:1027-1044:convert_flags_from_letters` decodes ROM letters with the ROM-correct A→0/G→6 mapping, so any area-file `AFF G` (DETECT_GOOD in ROM) silently becomes `AffectFlag.SANCTUARY` in Python.
- **Why deferred**: closure requires renumbering `AffectFlag` plus a persistence migration plan (character pfiles, mob/object protos, race definitions all carry `affected_by` ints). Out of scope for an opportunistic single-session fix.
- **Reproducer**: `tests/integration/test_tables_parity.py::test_affect_flag_letters_match_rom_merc_h` (xfail, strict).

### `TABLES-002` — 🔄 OPEN (deferred, IMPORTANT)
ROM table names like `npc`/`healer`/`changer`/`can_loot`/`dirt_kick` do not prefix-match Python IntFlag member names (`IS_NPC`/`IS_HEALER`/`IS_CHANGER`/`CANLOOT`/`KICK_DIRT`). Breaks ROM-style abbreviations in `do_flag` and OLC. Closure: add ROM-name aliases.

### `TABLES-003` — 🔄 OPEN (deferred, IMPORTANT)
Per-table value-equivalence audit not yet completed for ~30 remaining tables (`imm_flags`, `form_flags`, `part_flags`, `mprog_flags`, `extra_flags`, `wear_flags`, `apply_flags`, `wear_loc_flags`, `container_flags`, `weapon_class`, `weapon_type2`, `res_flags`, `vuln_flags`, `portal_flags`, `furniture_flags`, `apply_types`, etc.). Apply same letter→bit verification as for `AffectFlag`.

## Files Modified

- `docs/parity/TABLES_C_AUDIT.md` — created; Phase 1 inventory + Phase 2 spot-checks + 3-gap table.
- `tests/integration/test_tables_parity.py` — created; 4 passing value-equivalence tests + 1 xfail strict reproducer for TABLES-001.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `tables.c` row updated (70% → 75%, descriptive note).
- `CHANGELOG.md` — `Added` entry under `[Unreleased]` documenting the audit + reproducer.
- `pyproject.toml` — `2.6.30` → `2.6.31`.

## Test Status

- `pytest tests/integration/test_tables_parity.py -v` — 4 passed, 1 xfailed (strict — flips to xpass on closure).
- `tests/integration/test_lookup_parity.py` 12/12, `test_flag_command_parity.py` 10/10 still green.
- Pre-existing failures in `tests/test_commands.py` (4) and `tests/test_building.py` (14) unchanged.

## Next Steps

1. **TABLES-001** — most impactful next move; needs persistence migration design (pfile schema version bump? on-load translation table?). One focused session.
2. **TABLES-002** — close in one or two sessions by attaching ROM-name aliases on each diverging IntFlag (no persistence risk).
3. **TABLES-003** — iterate per-table; can interleave with TABLES-002.
4. Continuing the broader 43-file audit: 27/43 still ✅ AUDITED. Strong remaining picks: `board.c` (P2 35%), `nanny.c` deferred trio (008/009/010), OLC cluster.
