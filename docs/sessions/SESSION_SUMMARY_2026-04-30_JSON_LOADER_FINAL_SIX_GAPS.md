# Session Summary — 2026-04-30 — JSON loader parity audit complete (final 6 gaps)

## Scope

Closed the remaining 6 gaps in `docs/parity/JSON_LOADER_C_AUDIT.md`, completing
the JSON loader ROM parity audit (18/18 gaps closed).

## Outcomes

### JSONLD-001 (CRITICAL) — Object keyword list
- `mud/scripts/convert_are_to_json.py`: `object_to_dict` now emits a `keywords`
  field from `obj.name` (the ROM keyword list) alongside the display `name`.
- `mud/loaders/json_loader.py:_load_objects_from_json`: reads `keywords` key
  into `ObjIndex.name`, falling back to display `name` if absent.
- All 44 area JSON files regenerated with `keywords` for every object (e.g.
  Hassan's scimitar: `keywords='scimitar blade'`).
- 3 integration tests in `TestJSONLD001ObjectKeywords`.

### JSONLD-003 (CRITICAL) — Object level field
- `mud/scripts/convert_are_to_json.py`: `object_to_dict` now emits `level` from
  `obj.level` (ROM `src/db2.c:479`).
- Loader already read `level` correctly when present; now the JSON has it.
- All area JSONs regenerated with `level` for every object.
- 2 integration tests in `TestJSONLD003ObjectLevel`.

### JSONLD-015 (IMPORTANT) — Per-type value coercion
- `mud/loaders/json_loader.py:_load_objects_from_json`: now calls
  `_parse_item_values` from `obj_loader` to apply per-type value coercion at
  load time, mirroring ROM `src/db2.c:429-478`.
- `mud/models/constants.py:attack_lookup`: updated to handle numeric string
  inputs (in-range → return int, out-of-range → prefix-match), consistent with
  `_skill_lookup`, `_liq_lookup`, `_weapon_type_lookup`.
- 6 integration tests in `TestJSONLD015ValueCoercion`.

### JSONLD-016 (MINOR) — Case normalization
- JSON loader now lowercases-first `short_descr` and uppercases-first
  `description` at load time, mirroring ROM `src/db2.c:869-870`.
- 2 integration tests in `TestJSONLD016CaseNormalization`.

### JSONLD-017 (MINOR) — Room light
- Verified `Room.light` dataclass default is 0 (matching ROM `src/db.c:1164`).
  Closed-by-design — explicit init is redundant.
- 1 integration test in `TestJSONLD017RoomLight`.

### JSONLD-018 (MINOR) — ROOM_NO_MOB auto-add
- Removed the JSON-only behavior in `_link_exits_for_area` that auto-added
  `ROOM_NO_MOB` to rooms without exits. ROM does not do this.
- 1 integration test in `TestJSONLD018NoMobOnNoExitRooms`.

### Side fixes
- `tests/test_area_exits.py:test_midgaard_room_3001_exits_and_keys`: fixed
  stale assertion that expected a ghost NORTH exit to room 3054 that was never
  in the `.are` file (old JSON had stale data; regenerated JSON matches `.are`).

### Files changed
| File | Change |
|------|--------|
| `mud/loaders/json_loader.py` | JSONLD-001/003/015/016/018 — keyword, level, value coercion, case norm, ROOM_NO_MOB removal |
| `mud/models/constants.py` | JSONLD-015 — `attack_lookup` numeric-string handling |
| `mud/scripts/convert_are_to_json.py` | JSONLD-001/003 — emit `keywords` and `level` |
| `data/areas/*.json` (44 files) | Regenerated with `keywords`, `level`, correct race flags |
| `tests/integration/test_json_loader_parity.py` | +15 tests (44 total) |
| `tests/test_area_exits.py` | Fixed stale ghost-exit assertion |
| `docs/parity/JSON_LOADER_C_AUDIT.md` | All 18 gaps → FIXED |
| `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` | Re-audit triggers resolved |
| `CHANGELOG.md` | v2.6.108 entries |
| `pyproject.toml` | 2.6.107 → 2.6.108 |

### Test results
- `tests/integration/test_json_loader_parity.py`: 44 passed
- `tests/integration/ -k "boot or json or obj or equip or combat or spell"`: 321 passed
- `tests/test_area_exits.py`: 1 passed
- `tests/integration/test_character_advancement.py`: 19 passed (3 runs — RNG stable)
