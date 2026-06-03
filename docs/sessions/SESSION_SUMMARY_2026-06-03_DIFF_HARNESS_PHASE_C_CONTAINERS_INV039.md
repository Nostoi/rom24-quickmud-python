# Session Summary — 2026-06-03 — diff-harness Phase C containers → INV-039 object-list head-insert

## Scope

Continued `diff_harness` Hypothesis widening (Phase C) from the prior object-lifecycle
session. The plan was to widen the generated no-RNG state machine into container
`put`/get-from-container paths. Adding an open container (ROM bag `3032`) to the
machine immediately surfaced a structural divergence class — ROM head-inserts
objects into every list (`obj_to_{char,room,obj}`, LIFO) while the Python port
appended (FIFO). The session closed the three placement chokepoints under a new
cross-file invariant (**INV-039**), filed two distinct open siblings, and added
container coverage to the generated machine.

## Outcomes

### INV-039 OBJECT-LIST-HEAD-INSERT — ✅ ENFORCED (chokepoints only)

ROM's three placement primitives all head-insert (`obj->next_content = list;
list = obj;`), so carry lists, room contents, and container contents are LIFO —
observable via `inventory`/`look`/`look in` listings, `get all`/`drop
all`/`sacrifice` iteration, and numbered selectors (`2.lantern`, `enter
2.portal`, `sell 2.x`). All three Python chokepoints appended; fixed to
`insert(0, obj)` and verified against the live instrumented C oracle.

- **FINDING-017** — `Character.add_object` (carry list).
  - **Python**: `mud/models/character.py:678` (`insert(0, obj)`).
  - **ROM C**: `src/handler.c:1626 obj_to_char`.
  - Surfaced by the generated container round-trip: `get bag; get sword` → C
    `[sword, bag]`, py `[bag, sword]`.
- **FINDING-018** — `Room.add_object` (room contents).
  - **Python**: `mud/models/room.py:188` (`insert(0, obj)`).
  - **ROM C**: `src/handler.c:1953 obj_to_room`.
  - Surfaced via the `look` output order (the `room.contents` snapshot field is
    SORTED, so only the order-preserved output caught it).
- **FINDING-019** — `_obj_to_obj` (container contents).
  - **Python**: `mud/commands/obj_manipulation.py:628` (`insert(0, obj)`).
  - **ROM C**: `src/handler.c:1968 obj_to_obj`.
  - Source-confirmed (no container-contents snapshot field); guarded via `get
    all bag` against the live C oracle.
- **Tests**: `tests/integration/test_inv013_add_object_carrier.py::test_add_object_head_inserts_lifo`
  + three `tests/test_diff_harness_generated.py` order tests (container
  round-trip, room-drop, container-contents). 3× generative flush runs
  (`max_examples=25`, `step_count=8`) clean.
- **Corrected non-ROM-order tests** (asserted old append order → ROM LIFO):
  `test_do_inventory.py::test_inventory_duplicate_order_is_rom_lifo`,
  `test_shops.py::test_sell_numbered_selector`,
  `test_act_enter_gaps.py::...test_numbered_syntax_finds_second_portal`.

### FINDING-020 — `remove` re-append loses ROM carry-list position — ⚠️ OPEN (filed)

Distinct from INV-039: the equipment-storage architecture. ROM keeps equipped
objects in `ch->carrying` (only `wear_loc` changes), so a removed item keeps its
position; Python stores equipped objects in a separate `equipment` dict and
re-appends on remove. A faithful fix needs re-architecting equipment storage —
out of scope. The generated machine is gated to only `remove` when nothing else
is carried, so it exercises the matching single-item path. Filed in
`FINDINGS.md` + `DIVERGENCE_CLASS_ROSTER.md`.

### FINDING-021 — `look in <container>` header not capitalized — ⚠️ OPEN (filed)

ROM yields `A bag holds:` (act-cap, INV-029); Python emits `a bag holds:`.
Separate class (message capitalization). Filed for a follow-up gap-closer.

## Files Modified

- `mud/models/character.py` — `add_object` head-inserts (FINDING-017).
- `mud/models/room.py` — `add_object` head-inserts (FINDING-018).
- `mud/commands/obj_manipulation.py` — `_obj_to_obj` head-inserts (FINDING-019).
- `tools/diff_harness/generated.py` — added bag container (`3032`) with
  put/get-from-container rules; gated `remove` rules around FINDING-020.
- `tests/test_diff_harness_generated.py` — 3 deterministic order tests.
- `tests/integration/test_inv013_add_object_carrier.py` — head-insert LIFO test.
- `tests/integration/test_do_inventory.py`, `tests/test_shops.py`,
  `tests/integration/test_act_enter_gaps.py` — corrected to ROM LIFO order.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-039 (scoped to chokepoints).
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — class 13 row + to-do #7 (bypass sweep).
- `tools/diff_harness/FINDINGS.md` — 017/018/019 resolved, 020/021 open.
- `tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md` — Phase C status.
- `CHANGELOG.md` — Added (container coverage) + Fixed (INV-039) entries.
- `pyproject.toml` — 2.13.0 → 2.13.1.

## Test Status

- Focused regression slice (`-n0`): 100 passed.
- Full suite: **5391 passed, 4 skipped** (`pytest`, 0 failures).
- `ruff check .` — clean repo-wide.

## Next Steps

1. **Class-13 bypass-site sweep** (`/rom-divergence-sweep`, roster to-do #7):
   ~25 `append` placement sites need a per-site ROM read — runtime placements
   should head-insert (route through the chokepoint), reconstruction paths
   (`from_orm`, `clone_object`, serializers) must stay `append`. Not a lexical
   guard.
2. **FINDING-021** — close the `look in <container>` header-cap gap (INV-029
   territory, likely a one-line act-cap fix in the do_look-in path).
3. **FINDING-020** — the equipment-dict carry-list-position divergence; needs a
   scoped architectural decision, not a quick fix.
4. Continue Phase C deterministic command/watch-set widening (light hold,
   money/shop paths); add RNG-locked combat only after seed alignment is proven.
