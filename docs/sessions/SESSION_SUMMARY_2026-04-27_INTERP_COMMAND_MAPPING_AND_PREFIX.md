# Session Summary — 2026-04-27 — `interp.c` command-mapping cleanup, formatting, and prefix-order sweep

## Scope

Continuation of the same-day `interp.c` audit (release 2.6.9 closed
the dispatcher-hook cluster: INTERP-002/003/007/008). This session
worked through the remaining correctness gaps named in the previous
SESSION_STATUS Next Steps:

- INTERP-009/010/011/012/014 — command-mapping cleanup. Each routes a
  ROM cmd_table alias (`hit`, `take`, `junk`, `tap`, `go`, `:`) to its
  canonical handler instead of a Python stub.
- INTERP-013 — `wield`/`hold` vs `do_wear`. Audit-first.
- INTERP-024 — `do_commands`/`do_wizhelp` formatting verification.
- INTERP-017 — prefix-match table-order divergence (the largest
  remaining gap).

One gap = one parametrized test = one commit, per `rom-gap-closer`
discipline. Sub-agents (Explore) used for the two investigation-heavy
gaps (INTERP-013 audit and INTERP-024 formatting verification) so the
main thread stayed on closure work.

## Outcomes

### `INTERP-009` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py:300` (kill Command)
- **ROM C**: `src/interp.c:88`
- **Gap**: `"hit"` was routed to a separate `do_hit` stub in
  `mud/commands/player_info.py`; ROM cmd_table maps it to `do_kill`.
- **Fix**: added `"hit"` to `do_kill` Command's `aliases`; removed
  `do_hit` stub and dispatcher import.
- **Tests**: 1 (`test_interp_009_hit_routes_to_do_kill`).
- **Commit**: `64c4adf`.

### `INTERP-010` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py:269` (get Command)
- **ROM C**: `src/interp.c:226`
- **Gap**: `"take"` routed to `do_take` stub instead of `do_get`.
- **Fix**: added `"take"` to `do_get` Command's `aliases`; removed
  `do_take` stub and dispatcher import.
- **Tests**: 1 (`test_interp_010_take_routes_to_do_get`).
- **Commit**: `97fdec1`.

### `INTERP-011` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py:402` (sacrifice Command)
- **ROM C**: `src/interp.c:228-229`
- **Gap**: `"junk"`/`"tap"` routed to `do_junk`/`do_tap` stubs instead
  of `do_sacrifice`.
- **Fix**: added both to `do_sacrifice` Command's `aliases`; removed
  both stubs from `remaining_rom.py`.
- **Tests**: 2 cases parametrized
  (`test_interp_011_junk_tap_route_to_do_sacrifice`).
- **Commit**: `324bd1d`.

### `INTERP-012` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py:260` (enter Command)
- **ROM C**: `src/interp.c:263`
- **Gap**: `"go"` routed to `do_go` stub instead of `do_enter`.
- **Fix**: added `"go"` to `do_enter` Command's `aliases`; removed
  `do_go` stub and dispatcher import.
- **Tests**: 1 (`test_interp_012_go_routes_to_do_enter`).
- **Commit**: `5db5f00`.

### `INTERP-013` — ⚠️ DEFERRED

- **Python**: `mud/commands/equipment.py:279, 410` (`do_wield`,
  `do_hold`)
- **ROM C**: `src/interp.c:103, 215, 232`; `src/act_obj.c:1616-1736`
- **Gap (audit-first)**: ROM dispatches `wield`/`hold`/`wear` all to
  `do_wear`, which internally routes via `wear_obj()` based on item
  type. Python has separate `do_wield`/`do_hold` functions.
- **Investigation outcome**: Python `do_wear` is **missing** ROM
  behavior that `do_wield`/`do_hold` currently encapsulate:
  STR wield-weight check, weapon-skill flavor message, two-hand vs
  shield conflict (all in `do_wield`), and HOLD auto-unequip
  (`do_hold` rejects with "already holding" instead of removing the
  existing item). Collapsing now would regress behavior.
- **Resolution**: gap row flipped to ⚠️ DEFERRED with a note pointing
  at `ACT_OBJ_C_AUDIT.md` follow-ups (WEAR-001/WEAR-002) — port the
  missing pieces into `do_wear` first, then revisit the routing gap.
- **Tests**: none (audit only).
- **Commits**: none (investigation only; audit row update was bundled
  into the release commit).

### `INTERP-014` — ✅ FIXED

- **Python**: `mud/commands/dispatcher.py:294` (immtalk Command)
- **ROM C**: `src/interp.c:356`
- **Gap**: `":"` routed to `do_colon` stub whose
  `"Say what on the immortal channel?"` placeholder masked ROM's
  empty-arg NOWIZ toggle behavior in `do_immtalk`.
- **Fix**: added `":"` to `do_immtalk` Command's `aliases`; removed
  `do_colon` stub from `typo_guards.py` and dispatcher import; removed
  the standalone `Command(":", do_colon, …)` row.
- **Tests**: 1 (`test_interp_014_colon_routes_to_do_immtalk`).
- **Commit**: `e1fd782`.

### `INTERP-024` — ✅ FIXED

- **Python**: `mud/commands/info.py:42-54` (`_chunk_commands`)
- **ROM C**: `src/interp.c:815-823`
- **Gap (Explore-investigated)**: invariants 1–3 (iteration order,
  `show` filter, mortal/immortal trust split at `LEVEL_HERO`) were
  already correct. Invariant 4 (column padding) failed: Python called
  `.rstrip()` on each row, compressing the trailing column whenever a
  command name was shorter than 12 characters.
- **Fix**: removed both `.rstrip()` calls so columns preserve full
  12-char ROM `%-12s` padding.
- **Tests**: 1
  (`test_interp_024_do_commands_preserves_12char_column_padding`).
- **Commit**: `bc707ee`.

### `INTERP-017` — ✅ FIXED (largest gap)

- **Python**: `mud/commands/dispatcher.py` (`_ROM_CMD_TABLE_NAMES`,
  `_build_prefix_table`, `_prefix_table`, `resolve_command`)
- **ROM C**: `src/interp.c:63-381` (cmd_table) and `442-453`
  (`interpret()` prefix scan)
- **Gap**: ROM hand-orders cmd_table at the top so common 1- and
  2-letter abbreviations resolve to canonical commands ("Placed here
  so one and two letter abbreviations work" — `src/interp.c:76`).
  Python's `COMMANDS` list was grouped by feature, and
  `resolve_command` did exact-name lookup before prefix scan, so
  abbreviations diverged in 17 cases (e.g. `h`→hold not hit,
  `go`→go not goto, `sp`→split not spells, `sh`→shout not show).
- **Fix**: introduced `_ROM_CMD_TABLE_NAMES` — a 250-entry tuple in
  ROM declaration order — and `_build_prefix_table` mapping each ROM
  name to its Python `Command` via `COMMAND_INDEX`. `resolve_command`
  now walks this table linearly with **no** exact-match shortcut,
  mirroring ROM `interpret()`. Python-only commands (admin, OLC, IMC)
  are appended after so their abbreviations still work.
  `_prefix_table()` rebuild uses an identity-keyed cache so production
  callers pay zero rebuild cost; tests that monkeypatch `COMMANDS` /
  `COMMAND_INDEX` get a fresh table automatically.
- **Tests**: 45 parametrized cases in
  `tests/integration/test_interp_prefix_order.py` — parses
  `src/interp.c` cmd_table at collection time, computes ROM winner
  for every single-letter prefix and 20 curated 2-letter prefixes,
  asserts Python resolves to a `Command` whose name OR aliases
  include the ROM expected name (ROM cmd_table rows that share a
  do_fun are modelled in Python as Command + aliases).
- **Regression**: full `pytest tests/integration tests/test_alias_parity tests/test_help_system` —
  **1202 passed, 10 skipped, 0 failed** in 75.8s.
- **Commit**: `69e5cab`.

## Files Modified

- `mud/commands/dispatcher.py` — five alias additions
  (`hit`/`take`/`junk`/`tap`/`go`/`:` collapsed onto canonical
  Commands), removed five corresponding standalone Command rows and
  imports, added `_ROM_CMD_TABLE_NAMES` (250 entries),
  `_build_prefix_table`, `_prefix_table` cache, and rewrote
  `resolve_command` to walk the ROM-faithful table without an
  exact-match shortcut.
- `mud/commands/player_info.py` — deleted `do_hit`, `do_take` stubs.
- `mud/commands/remaining_rom.py` — deleted `do_go`, `do_junk`,
  `do_tap` stubs.
- `mud/commands/typo_guards.py` — deleted `do_colon` stub.
- `mud/commands/info.py` — removed `.rstrip()` from `_chunk_commands`
  rows so 12-char column padding is preserved.
- `tests/integration/test_interp_dispatcher.py` — added 6 new test
  functions (one per fixed gap) totaling 13 parametrized cases.
- `tests/integration/test_interp_prefix_order.py` — new file, parses
  ROM cmd_table at collection time, drives 45 parametrized prefix
  assertions.
- `docs/parity/INTERP_C_AUDIT.md` — flipped rows: INTERP-009,
  INTERP-010, INTERP-011, INTERP-012, INTERP-014, INTERP-017,
  INTERP-024 → ✅ FIXED; INTERP-013 → ⚠️ DEFERRED with rationale.
- `CHANGELOG.md` — added `[2.6.10]` section with seven entries.
- `pyproject.toml` — `2.6.9` → `2.6.10`.

## Recent Commits (this session)

- `64c4adf` — `fix(parity): interp.c:INTERP-009 — route 'hit' to do_kill`
- `97fdec1` — `fix(parity): interp.c:INTERP-010 — route 'take' to do_get`
- `324bd1d` — `fix(parity): interp.c:INTERP-011 — route 'junk'/'tap' to do_sacrifice`
- `5db5f00` — `fix(parity): interp.c:INTERP-012 — route 'go' to do_enter`
- `e1fd782` — `fix(parity): interp.c:INTERP-014 — route ':' to do_immtalk`
- `bc707ee` — `fix(parity): interp.c:INTERP-024 — preserve 12-char column padding`
- `69e5cab` — `fix(parity): interp.c:INTERP-017 — prefix scan walks ROM cmd_table order`
- (handoff commit follows: `chore(release): 2.6.10 — interp.c command-mapping + prefix-order`)

## Test Status

- `pytest tests/integration tests/test_alias_parity tests/test_help_system` →
  **1202 / 1202 passing, 10 skipped** (75.8s wall-clock).
- New test files / cases: 6 test functions (13 cases) in
  `test_interp_dispatcher.py`, 45 cases in `test_interp_prefix_order.py`.
- Pre-existing RNG-isolation flake in
  `tests/test_mobprog_commands.py::test_combat_cleanup_commands_handle_inventory_damage_and_escape`
  unchanged from prior sessions (still no autouse `rng_mm.seed_mm`
  fixture in the unit-test conftest).

## Audit Progress

- `interp.c`: **17 / 24 gaps closed** (71%, up from 11/24=46%). Tracker
  row stays ⚠️ Partial — 7 gaps remain (`INTERP-004`/`-005`/`-006`
  position/trust gates, `INTERP-013` deferred, `INTERP-015` shlex
  semantics, `INTERP-016` tail_chain hook documentation, `INTERP-021`
  social prefix-lookup audit per the row's verify suffix — actually
  already FIXED in v2.6.x; status table still honest).
- ROM C files audited overall: **16 / 43**.

## Next Steps

Remaining `interp.c` work is correctness-only:

1. **`INTERP-004`/`-005`/`-006`** — set missing `min_trust` on `shout`
   (ROM 3), `murder` (ROM 5), and fix `music`'s `min_position` to
   `POS_SLEEPING`.
2. **`INTERP-013`** — port the missing wield/hold behavior into
   `do_wear` (STR check, weapon-skill flavor, two-hand conflict, HOLD
   auto-unequip) under new gap IDs in `ACT_OBJ_C_AUDIT.md`, then
   collapse `do_wield`/`do_hold` into aliases on `do_wear`.
3. **`INTERP-015`** — replace `shlex.split` in `_split_command_and_args`
   with a ROM-faithful `one_argument` port, so backslash semantics
   match.
4. **`INTERP-016`** — document `tail_chain()` as a no-op extension
   hook; defer.
5. **Pre-existing RNG-isolation flake** — add a session-scoped
   `rng_mm.seed_mm` autouse fixture to `tests/conftest.py`.
