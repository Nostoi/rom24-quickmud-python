# Session Summary — 2026-04-30 — `olc_save.c` CRITICAL block fully closed (OLC_SAVE-007/008)

## Scope

Continuation of the prior session that closed OLC_SAVE-001..006 (commits
`cdfa149`..`a950b13`). This session picked up the two remaining
structured-data CRITICAL gaps — both involving dataclass↔dict round-trip
handling on object prototypes — and closed them inline (Sonnet
subagents continue to be unreliable in this codebase per the
carried-forward note). With these two closures the `olc_save.c`
round-trip data-loss block is **8/8 CRITICAL closed**.

## Outcomes

### `OLC_SAVE-007` — ✅ FIXED

- **Python**: `mud/olc/save.py` — new `_serialize_affect` helper; `_serialize_object` now routes affects through it.
- **ROM C**: `src/olc_save.c:399-429`
- **Gap**: Object affect chain serialized via raw `list(...affects, [])` pass-through — opaque, dropped fields beyond `location`/`modifier`, crashed `json.dump` on `Affect` dataclass values.
- **Fix**: New helper accepts either a plain dict (A-line `{location, modifier}` or F-line `{where, location, modifier, bitvector}` per `mud/loaders/obj_loader.py:425-475`) or an `Affect` dataclass instance and emits a json-safe dict. Defaults follow ROM (`type=-1`, `duration=-1`, `bitvector=0`).
- **Tests**: `tests/integration/test_olc_save_007_object_affects.py` — 5/5 passing.
- **Commit**: `1bae80a`

### `OLC_SAVE-008` — ✅ FIXED

- **Python**: `mud/olc/save.py` — `_serialize_extra_descr` now dict-aware; `_serialize_object` now routes extras through it.
- **ROM C**: `src/olc_save.c:431-435`
- **Gap**: Object extra_descr serialized via raw `list(...extra_descr, [])` pass-through; let stray dict keys leak and crashed `json.dump` on `ExtraDescr` dataclass values.
- **Fix**: Helper now branches on `isinstance(extra, dict)` and produces a flat `{"keyword", "description"}` payload regardless of input shape.
- **Tests**: `tests/integration/test_olc_save_008_object_extra_descr.py` — 3/3 passing.
- **Commit**: `c88403e`

## Files Modified

- `mud/olc/save.py` — added `_serialize_affect`; made `_serialize_extra_descr` dict-aware; rewired `_serialize_object` to route both lists through the helpers.
- `tests/integration/test_olc_save_007_object_affects.py` — new, 5 cases.
- `tests/integration/test_olc_save_008_object_extra_descr.py` — new, 3 cases.
- `docs/parity/OLC_SAVE_C_AUDIT.md` — flipped rows: OLC_SAVE-007, OLC_SAVE-008 (both ✅ FIXED). With these the CRITICAL block is fully closed (8/8).
- `CHANGELOG.md` — two `Fixed` entries.
- `pyproject.toml` — 2.6.93 → 2.6.95 (two patch bumps).

## Test Status

- `pytest tests/integration/test_olc_save_001..008*.py` — **26/26 passing**.
- Full integration suite — 1765 passing, 14 failures: 13 are the documented pre-existing `tests/test_olc_save.py` baseline; 1 (`test_kill_mob_grants_xp_integration`) is an order-dependent flake that passes in isolation, unrelated to this session.

## Next Steps

CRITICAL round-trip data-loss block is now **complete (8/8)**. The next
batch is the **IMPORTANT** block — five gaps in
`docs/parity/OLC_SAVE_C_AUDIT.md`:

- **OLC_SAVE-009** — no help-save path (port of ROM `save_helps`/`save_other_helps`).
- **OLC_SAVE-010** — `cmd_asave area` only handles `redit` editor; ROM dispatches on AEDIT/REDIT/OEDIT/MEDIT/HELP via `ch->desc->editor`.
- **OLC_SAVE-011** — autosave entry: ROM `if (!ch) sec = 9` allows `do_asave(NULL, "world")`; Python requires non-null `char`.
- **OLC_SAVE-012** — NPC security gate (`IS_NPC(ch) → sec = 0`).
- **OLC_SAVE-013** — `save_area_list` missing `social.are` prepend and HELP_AREA filenames.

Recommended start: **OLC_SAVE-010** (dispatcher coverage). It's the
narrowest user-visible gap (`@asave area` from aedit/oedit/medit/hedit
sessions silently no-ops or errors today) and a clean lead-in to 011/012
which sit on the same code path. OLC_SAVE-009 (help-save) is a larger
port and a natural standalone follow-up.

After IMPORTANT block, the MINOR block (OLC_SAVE-014..020) covers
string drifts and JSON-equivalence-documented divergences — all
mechanical.

### Carried-forward notes

- **Subagent reliability**: Sonnet subagents continue to terminate
  mid-investigation in this codebase (now five sessions reproduced).
  Both closures this session ran inline.
- **GitNexus index** is stale (last analyzed at 6899cc7). The 32 KB-cap
  caveat in CLAUDE.md still applies for `mud/commands/build.py` if a
  closure touches the asave dispatcher (OLC_SAVE-010..012).
