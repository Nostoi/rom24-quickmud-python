# Session Summary — 2026-05-28 — room_registry xdist isolation leak (2.9.91)

## Scope

Picked up the #1 "Next Intended Task" from the prior handoff
(`SESSION_SUMMARY_2026-05-28_FIGHT_018_DAM_MESSAGE_ACT_TRIGGER.md`): pin the
intermittent xdist isolation failure in
`tests/integration/test_group_combat.py::TestGroupExperienceSharing::test_group_xp_split_between_members`.
It failed non-deterministically with `AttributeError` at
`mud/spawning/reset_handler.py:178` (`exit_obj.exit_info = base_flags`) depending
on worker grouping. Per the prior session's note, the failing test was the
*victim*, not the leaker — the bug was a sibling test polluting the global
`room_registry`. This session found the leaker, fixed it, and verified the fix
across 6 full parallel runs. Not a ROM parity gap — purely test infrastructure.

Also a methodology discussion (no code): how to make the cross-file invariant
(INV) layer systematic rather than judgment-driven — static call-site
enumeration (GitNexus/`ast`) + always-on runtime invariant assertions
(icontract/deal) + Hypothesis stateful testing + differential testing against
compiled `src/` (uniquely viable here because the Mitchell-Moore RNG and C
integer math are already bit-matched). Captured here for the next agent; nothing
filed in a tracker yet.

## Outcomes

### `room_registry` isolation leak — ✅ FIXED

- **Leaker**: `tests/integration/test_flee_moves_character.py:59`
- **Victim (crash site)**: `mud/spawning/reset_handler.py:178`
  (`_restore_exit_states`), triggered via
  `tests/integration/test_group_combat.py` `game_tick()` → `reset_tick()`.
- **Root cause**: `test_flee_moves_character_to_new_room` calls
  `initialize_world()` (which `clear()`s and reloads `room_registry` /
  `area_registry` from disk), then sets the **real registered** room 3001's
  `.exits` to a dict — `{"north": {"to_room": dst_vnum, "closed": False}}` — to
  exercise `do_flee`'s `isinstance(exit_data, dict)` branch, and never restored
  it. Neither conftest resets `room_registry`/`area_registry` between tests, so
  under xdist `--dist loadscope` both the populated registries and the
  dict-shaped exits persisted on the worker. When a later test on the same
  worker ran `game_tick()`, `reset_tick()` iterated the leaked `area_registry`,
  reset the limbo area once its `age` had accumulated to ≥3 across prior ticks,
  and `_restore_exit_states` did `for idx, exit_obj in enumerate(exits)` over the
  dict — yielding the **string key `"north"`** — then `"north".exit_info = 0` →
  `AttributeError: 'str' object has no attribute 'exit_info'`. The age-threshold
  + worker-grouping dependency is why it was intermittent and why a 2-file repro
  didn't trigger it.
- **Fix**: added an autouse snapshot-before / restore-after fixture
  (`_restore_world_registries`) in the flee test file that captures
  `dict(room_registry)` / `dict(area_registry)` before the test and
  `clear()`+`update()`s them back after. This discards the test's
  freshly-created+corrupted Room 3001 and returns the registries to their
  pre-test state — the AGENTS.md "Parallel test execution & isolation" pattern,
  matching `tests/conftest.py` `_reset_object_registry` / `_reset_descriptor_list`.
- **Why test-side, not production hardening**: production `room.exits` is always
  a `list[Exit | None]` (the loader guarantees it); the dict shape only arises
  from this test's deliberate mutation. Hardening `_restore_exit_states` to skip
  non-Exit entries would mask this and future leakers. Fixed the leaker.
- **Verification**:
  - Deterministic mechanism repro (one-off script): `initialize_world()`, set
    room 3001 `.exits` to the dict, call `_restore_exit_states(room.area)` →
    `REPRODUCED AttributeError: 'str' object has no attribute 'exit_info'`.
  - Sentinel test (throwaway): asserted every `room_registry` room has list-typed
    exits after the flee test — **failed** pre-fix (`room 3001 leaked non-list
    exits: dict`), **passed** post-fix.
  - Stashed baseline (HEAD without the fix), full parallel suite: `1 failed,
    4897 passed, 4 skipped` — the flake reproduced.
  - With the fix, full parallel suite **6/6 runs green**: `4898 passed, 4
    skipped` each. Total test count stable at 4902 (fix adds/removes zero tests).

## Files Modified

- `tests/integration/test_flee_moves_character.py` — added autouse
  `_restore_world_registries` snapshot/restore fixture for
  `room_registry`/`area_registry`.
- `CHANGELOG.md` — 2.9.91 `Fixed` entry.
- `pyproject.toml` — 2.9.90 → 2.9.91.
- Commit `5396c067`.

## Test Status

- Full suite (parallel, `-n auto --dist loadscope`): **4898 passed, 4 skipped, 0
  failed**, consistent across 6 consecutive runs (~81–116s each).
- Stashed-baseline confirmation (no fix): 1 failed (the flake), 4897 passed.
- `ruff check tests/integration/test_flee_moves_character.py` — clean.

## Outstanding

- **Broader `initialize_world()` leak (not fixed, low severity)**: 49 integration
  files call `initialize_world()` and most don't restore the registries
  afterward. They leave a *structurally valid* world (list-typed exits), so they
  don't crash `_restore_exit_states` — only the flee test corrupted a room into
  an invalid shape. The general leak is pre-existing accepted behavior; a
  conftest-level autouse clear is **unsafe** as-is because 3 files
  (`test_get_room_messages.py`, `test_room_retrieval.py`,
  `test_put_room_messages.py`) use module-scoped world fixtures that a
  function-scoped clear would wipe mid-module. If revisited, the safe shape is a
  function-scoped snapshot/restore in `tests/integration/conftest.py` that
  excludes module-scoped-fixture files, or migrating those 3 files to per-test
  init.
- **INV-systematization plan** (discussion only, see Scope): candidate first step
  is an always-on `game_tick` invariant-assertion checker (autouse fixture or
  wrapper) so the existing ~4900 tests double as continuous INV probes. Not yet
  scoped into a tracker.

## Next Steps

1. **Push approval** — `master` is now **3 commits ahead** of `origin/master`
   (`dbcd5735` FIGHT-017 / 2.9.89, `f2bd9723` FIGHT-018 / 2.9.90, `5396c067`
   room_registry leak / 2.9.91). Not pushed (awaiting approval).
2. **INV-025 non-combat narration sweep** (optional, ad-hoc) — the
   `_push_message` / `broadcast_room` surface for non-combat ROM `act()` lines
   that should feed `mp_act_trigger_room`. One callsite per commit, gated on
   whether the ROM site carries a `MOBtrigger = FALSE` wrap.
3. **INV-layer systematization** (optional) — prototype the always-on
   `game_tick` invariant checker if pursuing the de-judgment-ification plan.
4. **GitNexus** — MCP query path read-only all session (`Cannot execute write
   operations in a read-only database`); on-disk graph stale (`last indexed:
   2272b2e`). Re-run `npx gitnexus analyze --skip-agents-md` once the DB lock
   clears.
