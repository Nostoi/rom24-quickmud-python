# Session Summary — 2026-06-03 — FINDING-022 show_list_to_char parity (2.13.4)

## Scope

Picked up from the class-13 bypass sweep session (2.13.3). The next open item from
`SESSION_STATUS` was FINDING-022 (`look in <container>` contents lines carry a
2-space indent ROM omits for a PC). Confirmed the divergence against ROM C source
(`src/act_info.c:130-243 show_list_to_char`): ROM has two formatting paths —
non-COMBINE PCs see no indent on listed objects, while NPC/COMBINE viewers see
5-space padding on singles and `(N) ` count prefix on duplicates. Python's
`_look_in` prepended a fixed 2-space indent matching neither path. Fixed by porting
`show_list_to_char` and `format_obj_to_char` from ROM C into `mud/utils/act.py` as
shared utilities, then routing `_look_in` through `show_list_to_char`.

## Outcomes

### FINDING-022 — `look in <container>` contents-line indent — ✅ FIXED

- **Python**: `mud/world/look.py:_look_in` (container branch), `mud/utils/act.py:show_list_to_char` + `format_obj_to_char`
- **ROM C**: `src/act_info.c:130-243` `show_list_to_char` (formatting paths), `:87-126` `format_obj_to_char` (aura prefixes)
- **Gap**: `_look_in` container branch used a hand-rolled `for` loop with fixed
  `f"  {item_name}"` (2-space indent). ROM's `show_list_to_char` formats
  differently per viewer type:
  - NPC or `COMM_COMBINE`: coalesce duplicates by `short_descr`, prefix
    `(%2d) ` for counts > 1, `     ` (5 spaces) for singles; empty → `     Nothing.`
  - PC without `COMM_COMBINE`: one line per visible object, no indent; empty → `Nothing.`
- **Fix**: Ported `format_obj_to_char` (lines 87-126, aura prefixes: Invis/Red Aura/
  Blue Aura/Magical/Glowing/Humming + `f_short`/`f_long` toggle) and `show_list_to_char`
  (lines 130-243, full combine/duplicate coalescence logic, `fShowNothing` gate) into
  `mud/utils/act.py`. `_look_in` container branch now calls
  `show_list_to_char(contents, char, f_short=True, f_show_nothing=True)` instead of the
  hand-rolled loop, producing ROM-correct output for both viewer types.
- **Impact**: `_show_inventory_list` in `mud/commands/inventory.py` already implements
  the same COMBINE logic independently (called by `do_inventory`). Both now agree on
  behavior. A future refactor could unify them, but is not required for this fix.
- **Tests**: `tests/integration/test_finding022_show_list_to_char_parity.py` — 11 tests:
  7 unit tests for `show_list_to_char` (no-indent PC, 5-space COMBINE, count prefix,
  NPC, empty/Nothing variants, fShowNothing=False) + 4 end-to-end tests for
  `look in` (no-indent non-COMBINE, 5-space COMBINE, empty no-indent, empty 5-space).
  All pass.
- **No commit yet** — changes are in working tree, ready for commit.

### FINDING-021 — unchanged (already ✅ from prior session)

## Files Modified

- `mud/utils/act.py` — added `format_obj_to_char`, `_obj_flag`, `_char_affected`,
  `show_list_to_char` (ROM `src/act_info.c:87-243` port). Added `TYPE_CHECKING`
  import for `Character`.
- `mud/world/look.py` — `_look_in` container branch: replaced hand-rolled
  `for item in contents: f"  {item_name}"` loop with
  `show_list_to_char(contents, char, f_short=True, f_show_nothing=True)`.
  Header line still emits via `capitalize_act_line`.
- `tests/integration/test_finding022_show_list_to_char_parity.py` — new, 11 tests.
- `tools/diff_harness/FINDINGS.md` — FINDING-022 → ✅ RESOLVED.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — class 13 row: FINDING-022 resolved,
  remaining open items updated.
- `docs/sessions/SESSION_STATUS.md` — updated to current state.
- `CHANGELOG.md` — added FINDING-022 entry under `[Unreleased]`.
- `pyproject.toml` — 2.13.3 → 2.13.4.

## Test Status

- New tests: `test_finding022_show_list_to_char_parity.py` — 11/11 passing.
- Prior FINDING-021 tests: `test_finding021_look_in_container_header.py` — 2/2 passing.
- Related container tests: INV-024, INV-013 suite — all green.
- Area slice (`-k "inventory or look or container or show_list"`): 235 passed, 1 skipped.
- Full suite: **5400 passed, 4 skipped** (`pytest`, 0 failures).
- `ruff check mud/utils/act.py mud/world/look.py` — clean.
- `ruff format` — all files formatted.

## Next Steps

1. **FINDING-020** — equipment-dict carry-list position divergence; needs a scoped
   architectural decision (ROM keeps equipped objects in the carry list, Python
   separates them into `char.equipment` dict and re-appends on remove).
2. Continue Phase C deterministic command/watch-set widening (light hold,
   money/shop paths); add RNG-locked combat only after seed alignment is proven.
3. Port room-contents `look()` path through `show_list_to_char` (currently
   `for obj in room.contents: lines.append(description)` without
   COMBINE/aura/visibility logic — separate gap from FINDING-022 but now
   solvable using the shared `show_list_to_char` function).