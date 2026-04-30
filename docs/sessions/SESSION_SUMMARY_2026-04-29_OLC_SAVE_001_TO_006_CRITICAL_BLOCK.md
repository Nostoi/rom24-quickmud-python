# Session Summary — 2026-04-29 — `olc_save.c` CRITICAL block (OLC_SAVE-001..006)

## Scope

Continuation of the same calendar day. Picked up immediately after the
prior session filed the `olc_save.c` audit (OLC_SAVE-001..020). This
session closed 6 of the 8 CRITICAL round-trip data-loss gaps in
sequence (OLC_SAVE-001 through OLC_SAVE-006), each as a single-gap TDD
commit with a paired loader-side change where the closure required it.
Two CRITICAL gaps remain (OLC_SAVE-007 affect chain, OLC_SAVE-008
extra_descr) — both involve dataclass-to-dict structured serialization
and were deferred to a fresh session for clear scope separation.

## Outcomes

### `OLC_SAVE-001` — ✅ FIXED

- **Python**: `mud/olc/save.py:_serialize_mobile`
- **ROM C**: `src/olc_save.c:205-208`
- **Gap**: Mob `off_flags`/`imm_flags`/`res_flags`/`vuln_flags` not persisted on JSON save.
- **Fix**: Serializer now emits `offensive`/`immune`/`resist`/`vuln` letter-strings, matching the keys the loader already consumes (`mud/loaders/json_loader.py:448-451`).
- **Tests**: `tests/integration/test_olc_save_001_mob_defensive_flags.py` — 3/3 passing.
- **Commit**: `cdfa149`

### `OLC_SAVE-002` — ✅ FIXED

- **Python**: `mud/olc/save.py:_serialize_mobile`
- **ROM C**: `src/olc_save.c:213-219`
- **Gap**: Mob `form`/`parts`/`size`/`material` not persisted.
- **Fix**: Serializer emits all four as strings; `Size` enum coerced to lowercase name (`Size.MEDIUM` → `"medium"`) to match loader contract. Round-trip is asserted at the JSON-write level rather than full Python-equality because the loader's `merge_race_flags` unions race-default bits into form/parts on read.
- **Tests**: `tests/integration/test_olc_save_002_mob_form_parts_size_material.py` — 3/3 passing.
- **Commit**: `1aebc02`

### `OLC_SAVE-003` — ✅ FIXED

- **Python**: `mud/olc/save.py:save_area_to_json` + new `_collect_mob_programs` helper
- **ROM C**: `src/olc_save.c:151-169` (save_mobprogs) + `src/olc_save.c:245-250` (per-mob MPROG_LIST)
- **Gap**: Mob mprog assignments dropped on JSON save.
- **Fix**: New helper walks every mob in the area, groups `mprogs` by program vnum, emits structured `mob_programs` list (matching the loader's existing reader at `_load_mob_programs_from_json`). Triggers serialize via `mud.mobprog.format_trigger_flag` (int → ROM keyword).
- **Tests**: `tests/integration/test_olc_save_003_mob_mprogs.py` — 3/3 passing.
- **Commit**: `912ebf8`

### `OLC_SAVE-004` — ✅ FIXED

- **Python**: `mud/olc/save.py` (new `_collect_shops`) + `mud/loaders/json_loader.py` (new `_load_shops_from_json`)
- **ROM C**: `src/olc_save.c:786-824`
- **Gap**: Mob `pShop` (keeper, buy_types[5], profit_buy/sell, open_hour/close_hour) not persisted; loader had no JSON-shops path.
- **Fix**: Serializer emits a top-level `shops` list per area; paired loader rehydrates `mud.registry.shop_registry` keyed by keeper vnum and re-attaches `MobIndex.pShop`. Both sides land in one commit per the audit's locked closure rule.
- **Tests**: `tests/integration/test_olc_save_004_mob_shops.py` — 3/3 passing.
- **Commit**: `835bd82`

### `OLC_SAVE-005` — ✅ FIXED

- **Python**: `mud/olc/save.py:save_area_to_json` + new `_collect_specials` helper
- **ROM C**: `src/olc_save.c:578-606` (save_specials)
- **Gap**: Mob `spec_fun` bindings dropped on JSON save.
- **Fix**: Serializer emits a top-level `specials` list (`{"mob_vnum", "spec"}`); the loader (`apply_specials_from_json` in `mud/loaders/specials_loader.py`) was already in place — this closure adds the missing serialize half.
- **Tests**: `tests/integration/test_olc_save_005_mob_spec_fun.py` — 3/3 passing.
- **Commit**: `8f83005`

### `OLC_SAVE-006` — ✅ FIXED

- **Python**: `mud/olc/save.py:_serialize_object` + `mud/loaders/json_loader.py:_load_objects_from_json`
- **ROM C**: `src/olc_save.c:378`
- **Gap**: Object `level` not persisted.
- **Fix**: Serializer emits `level` int; paired loader hydrates `ObjIndex.level`. Without this, every reload reset object levels to 0.
- **Tests**: `tests/integration/test_olc_save_006_object_level.py` — 3/3 passing.
- **Commit**: `a950b13`

## Files Modified

- `mud/olc/save.py` — added `_collect_specials`, `_collect_shops`, `_collect_mob_programs` helpers; expanded `_serialize_mobile` (4 closures: 001/002 plus mprogs/shops/specials orchestration) and `_serialize_object` (006).
- `mud/loaders/json_loader.py` — added `_load_shops_from_json`, hydrated `ObjIndex.level` on object load.
- `tests/integration/test_olc_save_001_mob_defensive_flags.py` — new, 3 cases.
- `tests/integration/test_olc_save_002_mob_form_parts_size_material.py` — new, 3 cases.
- `tests/integration/test_olc_save_003_mob_mprogs.py` — new, 3 cases.
- `tests/integration/test_olc_save_004_mob_shops.py` — new, 3 cases.
- `tests/integration/test_olc_save_005_mob_spec_fun.py` — new, 3 cases.
- `tests/integration/test_olc_save_006_object_level.py` — new, 3 cases.
- `docs/parity/OLC_SAVE_C_AUDIT.md` — flipped rows: OLC_SAVE-001/002/003/004/005/006 (all ✅ FIXED).
- `CHANGELOG.md` — six `Fixed`/`Added` entries (one per gap).
- `pyproject.toml` — 2.6.87 → 2.6.93 (six patch bumps, one per commit).

## Test Status

- `pytest tests/integration/test_olc_save_001..006*.py` — **18/18 passing**.
- `pytest tests/test_olc_save.py` — 13 failures are **pre-existing baseline** (verified by stash/unstash before commits 001 and after commit 006); not introduced by this session.
- Full integration suite not re-run; changes were additive (new fields/sections in JSON output, plus a new shops loader path) and are covered by the new round-trip tests.

## Next Steps

Two CRITICAL gaps remain in the round-trip data-loss block:

1. **OLC_SAVE-007** (object structured affect chain). `_serialize_object` does `list(...affects, [])` raw pass-through; ROM emits structured `where`/`location`/`modifier`/`bitvector` tuples (TO_OBJECT vs TO_AFFECTS/IMMUNE/RESIST/VULN per src/olc_save.c:399-429). Closure needs both:
   - Serializer: convert `Affect` dataclasses → dict with structured fields.
   - Loader: hydrate dicts back into `Affect` instances on read.
2. **OLC_SAVE-008** (object structured extra_descr). Same shape: pass-through becomes opaque if items are `ExtraDescr` dataclass instances rather than dicts. Closure: route through the existing `_serialize_extra_descr` helper on save and hydrate dicts → `ExtraDescr` on load.

Both require careful dataclass↔dict round-trip handling (likely a small `_dump_affect`/`_load_affect` pair). Recommended order: 007 first (larger blast radius — combat balance), then 008 (descriptive text only).

After 007/008, the IMPORTANT block (OLC_SAVE-009..013) is the next batch:
- OLC_SAVE-009: no help-save path
- OLC_SAVE-010: `cmd_asave area` only handles `redit` editor
- OLC_SAVE-011: no autosave entry (`!ch → sec=9` path)
- OLC_SAVE-012: NPC security gate
- OLC_SAVE-013: `save_area_list` missing `social.are` + HELP_AREA prepend

### Carried-forward notes

- **Subagent reliability**: Sonnet subagents continue to terminate mid-investigation in this codebase. All six closures this session ran inline. Haiku remains reliable only for trivial single-keyword fixes; this work was field-by-field structural and not suitable.
- **Registry namespace gotcha**: `mud.models.mob.mob_registry` and `mud.registry.mob_registry` are separate dict instances. The OLC save module imports from `mud.registry`. Tests must do the same — caught and fixed in OLC_SAVE-001's first round-trip test.
- **GitNexus index** is stale (last analyzed at 6899cc7); the in-progress `npx gitnexus analyze` started at session open completed with exit 0 partway through. Re-run at next session start if `gitnexus_impact` results look implausible.
