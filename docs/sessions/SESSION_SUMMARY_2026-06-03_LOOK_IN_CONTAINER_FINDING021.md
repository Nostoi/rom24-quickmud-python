# Session Summary — 2026-06-03 — `look in <container>` header/empty parity (FINDING-021)

## Scope

Picked up from the diff-harness Phase C / INV-039 session, which had completed its
work in the working tree but never committed it. This session committed that
intact INV-039 unit, then took the next concrete closable item from
`SESSION_STATUS` — FINDING-021 (`look in <container>` header not act-capitalized)
— and closed it. Reading the ROM block to fix the header surfaced an adjacent
divergence in the same branch (an invented "is empty" message), which was fixed in
the same commit as one root cause, and a third, separate divergence (contents-line
indent) that was filed open rather than fixed.

## Outcomes

### INV-039 OBJECT-LIST-HEAD-INSERT — committed (no new code)

The prior session's complete-but-uncommitted head-insert work (FINDING-017/018/019,
three placement chokepoints → `insert(0, obj)`, three corrected order tests, the
INV-039 tracker row, FINDINGS 017–021, and its own session summary) was verified
(focused slice 87/87, full suite green) and committed intact as `cdaaa31f`.

### FINDING-021 — `look in <container>` header act-capitalized + ROM empty rendering — ✅ FIXED

- **Python**: `mud/world/look.py:_look_in` (CONTAINER branch).
- **ROM C**: `src/act_info.c:1166-1167` — `act("$p holds:")` + `show_list_to_char(obj->contains, ch, TRUE, TRUE)`.
- **Gap**: the Python CONTAINER branch was a Python invention, not a port of the
  ROM block. It emitted a lowercase `a bag holds:` header (ROM's `act_new` caps the
  first visible char → `A bag holds:`, INV-029), and for an empty container it
  printed an invented `"a bag is empty."` line. ROM has no "is empty" branch for
  containers — `show_list_to_char` with `fShowNothing==TRUE`, `nShow==0` prints
  `Nothing.` (`act_info.c:227-231`).
- **Fix**: header now routes through `capitalize_act_line` (`A bag holds:`); empty
  container prints the header + `Nothing.`. The listed contents stay lowercase
  (they come from `format_obj_to_char`, not `act`). The drink-con `"It is empty."`
  path (`act_info.c:1143`) is genuine ROM and was left untouched.
- **Tests**: `tests/integration/test_finding021_look_in_container_header.py` — 2
  tests (capitalized header w/ contents; empty container → `Nothing.`, no "is
  empty"). Both fail pre-fix, pass post-fix.
- **Commit**: `f34efe75`.

### FINDING-022 — `look in <container>` contents lines carry a 2-space indent ROM omits for a PC — ⚠️ OPEN (filed)

Surfaced while reading `show_list_to_char` (`src/act_info.c:130-243`). For a
non-NPC char without `COMM_COMBINE`, ROM adds **no** indent to listed objects (the
indent block is gated on `IS_NPC || COMM_COMBINE`, `act_info.c:210-221`). Python's
`_look_in` prepends a fixed 2-space indent (`f"  {item_name}"`), matching neither
the no-indent PC path nor the 5-space COMBINE path. Not oracle-confirmed (the
generated machine still avoids `look in` for contents lines), so it was filed OPEN
in `FINDINGS.md` rather than fixed — a faithful fix also implies porting
`show_list_to_char`'s combine/count semantics, which needs deliberate scoping and
an oracle run.

## Files Modified

- `mud/world/look.py` — `_look_in` CONTAINER branch: capitalized header via
  `capitalize_act_line`, ROM `Nothing.` for empty (replaces invented "is empty").
- `tests/integration/test_finding021_look_in_container_header.py` — new, 2 tests.
- `tools/diff_harness/FINDINGS.md` — FINDING-021 → ✅ RESOLVED; FINDING-022 filed OPEN.
- `CHANGELOG.md` — Fixed: FINDING-021 entry.
- `pyproject.toml` — 2.13.1 → 2.13.2.
- (Committed from prior session as `cdaaa31f`: the full INV-039 file set.)

## Test Status

- New tests: `test_finding021_look_in_container_header.py` — 2/2 passing.
- Focused area slice (`-n0`): look/container suites 35/35 passing.
- Full suite: **5393 passed, 4 skipped** (`pytest`, 0 failures).
- `ruff check .` — clean repo-wide.

## Next Steps

1. **Class-13 bypass-site sweep** (`/rom-divergence-sweep`, roster to-do #7): the
   ~25 remaining `append` placement sites need a per-site ROM read — runtime
   placements should head-insert (route through the chokepoint), reconstruction
   paths (`from_orm`, `clone_object`, serializers) stay `append`. Not a lexical
   guard.
2. **FINDING-022** — confirm the contents-line indent against the live C oracle
   (add a `look in` step to the generated machine or a one-off capture), then port
   `show_list_to_char` PC semantics if confirmed divergent.
3. **FINDING-020** — equipment-dict carry-list-position divergence; needs a scoped
   architectural decision (ROM keeps equipped objects in the carry list).
4. Continue Phase C deterministic command/watch-set widening (light hold,
   money/shop paths); RNG-locked combat only after seed alignment is proven.
