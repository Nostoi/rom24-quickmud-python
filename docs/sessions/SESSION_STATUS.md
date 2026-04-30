# Session Status — 2026-04-30 — `json_loader.py` IMPORTANT loader gaps closed (11/18)

## Current State

- **Active audit**: `json_loader.py` ↔ `src/db.c` / `src/db2.c` (Phase 4 in progress — 11/18 JSON loader gaps closed)
- **Last completed**: JSONLD-009, JSONLD-010, JSONLD-013, JSONLD-014 (area security, Format 1 credits, room clan lookup, boot-time D-reset discard)
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-04-30_JSON_LOADER_009_010_013_014.md](SESSION_SUMMARY_2026-04-30_JSON_LOADER_009_010_013_014.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.104 |
| JSON loader audit | 11/18 gaps closed (`JSON_LOADER_C_AUDIT.md`) |
| JSON loader integration tests | 27/27 passing |
| Full integration suite | 1813 passing / 10 skipped / 16 warnings |
| Known unrelated failure | `tests/test_area_loader.py::test_mob_flag_removal_lines_clear_flags` (`mob.form == "BC"` vs race-merged `"BCHMV"`) |
| Active focus | Continue JSON loader parity before schema/converter changes |

## Next Intended Task

Continue `JSON_LOADER_C_AUDIT.md` Phase 4. Recommended order: JSONLD-012
(mob `race` stored as string) after auditing consumers, then JSONLD-015
(type-specific object `value[]` coercion) with careful double-conversion tests.
After that, close the MINOR block JSONLD-016..018. Keep JSONLD-001 and
JSONLD-003 separate because they require schema/converter changes and JSON data
regeneration, not just loader fixes.
