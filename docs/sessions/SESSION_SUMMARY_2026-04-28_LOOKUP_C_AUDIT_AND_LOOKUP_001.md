# Session Summary — 2026-04-28 — `lookup.c` parity audit + LOOKUP-001 closure

## Scope

Picked up after `flags.c` reached ✅ AUDITED. Audited `src/lookup.c` (10 ROM functions, all simple table-search-by-name). Found a consistent gap pattern (ROM uses `str_prefix` prefix-match; Python equivalents use exact-match dict lookup) and one **latent runtime bug**: `mud/persistence.py:614` imports `race_lookup` from `mud/models/races.py`, but that function had never been ported — every pet load with a non-None race snapshot would crash with `ImportError`.

Closed LOOKUP-001 (the runtime bug) this session. LOOKUP-002..008 are documented OPEN gaps in `docs/parity/LOOKUP_C_AUDIT.md` for follow-up sessions; tracker stays ⚠️ Partial (70%) accordingly.

## Outcomes

### `LOOKUP-001` — ✅ FIXED

- **ROM C**: `src/lookup.c:110-122` (`race_lookup`).
- **Python**: new `mud/models/races.py:race_lookup`. Caller: `mud/persistence.py:614` (pet-restore path).
- **Fix**: added `race_lookup(name: str | None) -> int` mirroring ROM exactly — case-insensitive prefix-match against `RACE_TABLE`, fall-through `return 0` for unknown names (race index 0 is the "unique" sentinel).
- **Tests**: `tests/integration/test_lookup_parity.py` — 6 tests:
  - Symbol exists at module level
  - Full-name match returns the correct index
  - Prefix abbreviation (`hum` → `human`) matches per ROM
  - Case-insensitive (`HUMAN` works)
  - Unknown name returns 0 (ROM fall-through)
  - Persistence-style import smoke test

### LOOKUP-002..008 — 🔄 OPEN (deferred)

Documented in the audit doc with stable IDs. All are variants of the same problem: ROM `str_prefix` (prefix-match) not honored by Python equivalents.

- LOOKUP-002 (IMPORTANT): `_lookup_flag_bit` from yesterday's flags.c session uses exact-match.
- LOOKUP-003 (IMPORTANT): clan name lookup exact-match.
- LOOKUP-004..006 (IMPORTANT): no `position_lookup` / `sex_lookup` / `size_lookup` Python equivalents.
- LOOKUP-007 (IMPORTANT): no `item_lookup` Python equivalent.
- LOOKUP-008 (MINOR): private `_liq_lookup` exact-match.

A future session can land these as one cohesive change by introducing a shared `prefix_lookup(name, table)` helper and migrating each callsite.

## Files Modified

- `mud/models/races.py` — added `race_lookup` function (16 lines, ROM-faithful prefix-match + default-0 fallthrough).
- `tests/integration/test_lookup_parity.py` — new file, 6 tests.
- `docs/parity/LOOKUP_C_AUDIT.md` — created. Full Phase 1 inventory of all 10 ROM functions, Phase 2 analysis, Phase 3 gap table with 8 stable IDs (LOOKUP-001 ✅ FIXED, LOOKUP-002..008 🔄 OPEN), Phase 4 closure detail for LOOKUP-001.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `lookup.c` row updated (still ⚠️ Partial, 65% → 70%) with audit doc reference and gap status.
- `CHANGELOG.md` — added `Fixed: LOOKUP-001` entry under `[Unreleased]`.
- `pyproject.toml` — `2.6.22` → `2.6.23`.

## Test Status

- `pytest tests/integration/test_lookup_parity.py -v` — 6/6 passing.
- `ruff check mud/models/races.py tests/integration/test_lookup_parity.py` — 8 pre-existing errors in `races.py` (un-sorted import block, `typing.Tuple`/`Type` deprecations) **not caused by this change**; verified by stashing my edit and re-running ruff (same count). My new function and the test file are lint-clean.

## Next Steps

Tracker now 26/43 audited (lookup.c stays Partial). Strongest follow-up candidates:

1. **LOOKUP-002..008** as a single cohesive session: introduce `mud/utils/prefix_lookup.py:prefix_lookup(name, table)` helper, migrate all the existing exact-match lookups, ship one commit per gap.
2. **`tables.c`** (P3 70%) — sibling of lookup.c; flag-name string tables. Likely shares much of the work above.
3. **`const.c`** (P3 80%) — large; best as `stat_app` sub-audit first.
4. **Deferred NANNY trio** (008/009/010) — each architectural-scope session.
5. **`board.c`** (P2 35%) — boards subsystem.

## Notes

- The pre-existing 8 ruff errors in `mud/models/races.py` are out-of-scope housekeeping (typing.Tuple → tuple, typing.Type → type). Worth a separate cleanup commit if the modernization is wanted; they don't affect runtime.
- 4 pre-existing failures in `tests/test_commands.py` (alias / scan-directional / typo guards) from another in-flight session remain. Not caused by this work.
