# Session Summary — 2026-04-30 — `json_loader.py` IMPORTANT loader gaps closed (JSONLD-009/010/013/014)

## Scope

Continued the JSON loader parity audit after the v2.6.103 single-commit loader
batch. This session closed the next single-commit IMPORTANT gaps that did not
require schema or converter rewrites: area security defaults, Format 1 area
credits, room clan lookup, and boot-time `D` reset handling.

## Outcomes

### `JSONLD-009` — ✅ FIXED

- **Python**: `mud/loaders/json_loader.py`
- **ROM C**: `src/db.c:452`, `src/db.c:531`
- **Gap**: JSON-loaded areas defaulted `security` to 0 instead of ROM's OLC security default 9.
- **Fix**: Format 1 and Format 2 JSON area loads now default to security 9 while preserving explicit JSON `security` values.
- **Tests**: `tests/integration/test_json_loader_parity.py` adds 3 area-security cases.

### `JSONLD-010` — ✅ FIXED

- **Python**: `mud/loaders/json_loader.py`
- **ROM C**: `src/db.c:457`
- **Gap**: Format 1 JSON area `credits` were never hydrated.
- **Fix**: Format 1 area loads now read `credits` from JSON when present.
- **Tests**: `tests/integration/test_json_loader_parity.py` adds 1 credits case.

### `JSONLD-013` — ✅ FIXED

- **Python**: `mud/loaders/json_loader.py`
- **ROM C**: `src/db.c:1192`
- **Gap**: JSON room `clan` values could remain raw strings instead of ROM clan ids.
- **Fix**: Room clan values now pass through `lookup_clan_id`, preserving integers and resolving string names/prefixes with ROM `clan_lookup` semantics.
- **Tests**: `tests/integration/test_json_loader_parity.py` adds 3 clan cases; `tests/test_area_loader.py` now uses a real ROM clan and expects the resolved id after JSON load.

### `JSONLD-014` — ✅ FIXED

- **Python**: `mud/loaders/json_loader.py`
- **ROM C**: `src/db.c:1058-1104`
- **Gap**: JSON `D` resets were stored in `area.resets` / `room.resets` and reprocessed each reset cycle.
- **Fix**: JSON `D` resets now apply boot-time door state to `rs_flags` / `exit_info` and are discarded, matching ROM `free_reset_data`.
- **Tests**: `tests/integration/test_json_loader_parity.py` adds 1 D-reset boot-state/discard case.

## Files Modified

- `mud/loaders/json_loader.py` — added `_apply_door_reset`; defaulted area security to 9; loaded Format 1 credits; resolved room clans through `lookup_clan_id`; discarded `D` resets after boot-state application.
- `tests/integration/test_json_loader_parity.py` — added 8 integration tests covering JSONLD-009, 010, 013, and 014.
- `tests/test_area_loader.py` — adjusted the clan round-trip expectation to ROM lookup semantics.
- `docs/parity/JSON_LOADER_C_AUDIT.md` — flipped JSONLD-009, 010, 013, and 014 to ✅ FIXED; 11/18 JSON loader gaps now closed.
- `CHANGELOG.md` — added v2.6.104 JSON loader parity release notes.
- `pyproject.toml` — 2.6.103 → 2.6.104.

## Test Status

- `pytest tests/integration/test_json_loader_parity.py` — 27/27 passing.
- `pytest tests/integration/test_json_loader_parity.py tests/test_area_loader.py::test_convert_area_preserves_clan_and_owner tests/test_area_loader.py::test_json_loader_populates_room_resets tests/test_area_loader.py::test_json_loader_applies_defaults_and_law_flag -q` — 30/30 passing.
- `pytest tests/integration/ -q` — 1813 passing, 10 skipped, 16 warnings.
- `ruff check mud/loaders/json_loader.py tests/integration/test_json_loader_parity.py tests/test_area_loader.py` — clean.
- `pytest tests/test_area_loader.py -q` — 27 passing, 1 known pre-existing failure (`test_mob_flag_removal_lines_clear_flags`, `mob.form == "BC"` vs race-merged `"BCHMV"`).

## Next Steps

Continue `JSON_LOADER_C_AUDIT.md` Phase 4 with the remaining single-risk gaps:
JSONLD-012 (mob race stored as string), JSONLD-015 (object value coercion), and
the MINOR block JSONLD-016..018. Schema/converter gaps JSONLD-001 and
JSONLD-003 should remain separate multi-commit work because they require JSON
schema and converter updates, not just loader changes.
