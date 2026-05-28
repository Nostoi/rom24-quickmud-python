# Session Summary — 2026-05-28 — differential harness first catch (LOOK-001/002) + invariant checker → opt-in

## Scope

Continuation of the same day's tooling work
(`SESSION_SUMMARY_2026-05-28_INVARIANT_CHECKER_AND_DIFF_HARNESS.md`). That session
built the always-on `game_tick` invariant checker (2.10.0) and the differential
testing harness v1 (branch `diff-harness`). This session: executed the harness
plan to completion on the branch, used its **first real catch** to close two
ROM-parity gaps on `master`, and — after the always-on invariant checker proved
flaky — converted it to opt-in.

## Outcomes

### Differential harness v1 — completed on branch `diff-harness`

All 10 plan tasks done (schema, comparator, pysnap, scenario loader, additive C
shim `src/diffshim` built on macOS via flags only, capture tool, committed golden,
replay smoke test, README, finalize). The instrumented ROM C binary drives real
`interpret()` from stdin and emits JSON state/output; the pure-Python replay diffs
it. Branch kept unmerged (v1 with an open finding). The C shim was built by an
Opus subagent (3 commits); I verified the binary by hand.

### `FINDING-001` → `LOOK-001` ✅ FIXED (master, 2.10.1)

The harness's **first run flagged a real divergence**: room `look` showed an NPC's
name (`Hassan`) where ROM shows its `long_descr`
(`Hassan is here, waiting to dispense some justice.`).
- **Root cause**: `mud/world/look.py` rendered room occupants via
  `describe_character` (ROM `PERS`/brief path); ROM `show_char_to_char_0`
  (`src/act_info.c`) shows an NPC's `long_descr` when `position == start_pos`. And
  `MobInstance` never carried `long_descr` from its prototype (ROM `create_mobile`,
  `src/db.c:2040`, copies it).
- **Fix**: `MobInstance.from_prototype` copies `long_descr`; new
  `look.py:_room_occupant_line` implements the long_descr branch.
- **Significance**: the `act_info.c` audit had this row marked **"100% PARITY"**
  (validated by `do_look 9/9` smoke tests that never asserted NPC long_descr) — a
  concrete demonstration that engine-vs-engine comparison catches contracts the
  per-file audit misses. Audit row corrected.
- **Zero existing-test fallout** (nothing covered this). Test:
  `tests/integration/test_look_long_descr_rom_parity.py`. Commit `506d2633`.

### `LOOK-002` ✅ FIXED (master, 2.10.2)

Sibling of LOOK-001, found while closing it: `MobInstance` likewise didn't carry
`description`, so `look <mob>` printed "You see nothing special about X" instead of
the ROM mob description (`show_char_to_char_1`; `create_mobile` copies it).
`from_prototype` now copies `description`. Zero fallout. Commit `3888ff2a`.

### Invariant checker → opt-in ✅ (master, 2.10.3)

While hunting a recurring `test_group_combat` xdist flake, the investigation found
there was **no single "second leaker"**: the always-on invariant checker (2.10.0)
walks the GLOBAL `character_registry`/`room_registry` after every `game_tick`, but
the suite never fully isolates those (tests call `initialize_world`, mutate shared
`room.people` in place, leave registered chars). A *fresh* `initialize_world` is
fully coherent, so the violations were cross-test pollution, not real bugs — the
checker fired in whichever sibling `game_tick`-ed after a polluting test, with the
victim shifting by xdist grouping (`test_group_combat` → `test_skills_integration`
as fixes were attempted). Per systematic-debugging's "question the architecture"
rule (two fixes, each surfacing a new symptom), this was escalated to a design
decision: **make the checker opt-in**.
- `tests/conftest.py`: checker enabled only for tests marked
  `@pytest.mark.check_invariants` (default off). Removed the `no_invariant_check`
  opt-out marker and the three marks added for the always-on rollout; reverted the
  temporary diagnostics and the exploratory `character_registry` fixture.
- Checker code (`mud/diagnostics/invariants.py`), the `game_tick` hook, and the
  unit tests are retained (repointed to the opt-in marker). Commit `7cb1194a`.

## Files Modified (master)

- `mud/world/look.py`, `mud/spawning/templates.py` (LOOK-001/002 engine fixes)
- `tests/integration/test_look_long_descr_rom_parity.py` (new; 4 cases)
- `tests/conftest.py`, `tests/test_invariant_checker.py`, `tests/test_resets.py`,
  `tests/test_game_loop.py`, `tests/test_game_loop_wait_daze.py` (opt-in checker)
- `docs/parity/ACT_INFO_C_AUDIT.md` (LOOK-001/002 rows; corrected the false
  "100% PARITY" `show_char_to_char_0` row)
- `CHANGELOG.md`, `pyproject.toml` (2.10.1 → 2.10.3)

## Test Status

- Full suite green: **4909 passed, 4 skipped, 0 failed**, verified across 3
  consecutive runs after the opt-in change (the flake is gone).
- `diff-harness` branch: 4911 passed / 1 xfailed (FINDING-001, self-clearing once
  the branch gets the master LOOK-001 fix).

## Loop closure (post-fix)

`master` was pushed to origin (`b3f52e2d`) and merged into `diff-harness`
(`c878dd41`). Re-running the differential harness on the branch confirmed the
LOOK-001 fix: **the room/output divergence is gone — the Python replay now matches
the C reference exactly.** The harness then advanced to the next divergence,
**FINDING-002** (test-character hp: C=20 vs py=0) — a harness char-creation
asymmetry (C shim `new_char` vs Python `create_test_character`), not a parity bug;
the scenario stays xfailed on it. FINDING-001 marked ✅ RESOLVED in
`tools/diff_harness/FINDINGS.md`. This is the full end-to-end demonstration: build
→ catch → fix on master → re-run → confirmed clean → next finding queued.

## Outstanding

- **`diff-harness` branch — 2 soundness follow-ups** before it produces fully
  trustworthy diffs and can merge: **FINDING-002** (reconcile the C-shim and
  Python test-character creation) and the input-source asymmetry below.
- **Harness input-source asymmetry** (harness soundness, separate from FINDING-001):
  the C side reads `.are` files (repaired midgaard overlay) while Python reads
  `data/areas/*.json`. Reconcile before trusting midgaard-based divergences broadly.
  See `tools/diff_harness/FINDINGS.md`.
- **`area/midgaard.are` is malformed** vs stock ROM (bare `#`/`~ROOMS`); Python's
  JSON path is unaffected, but the data file is corrupt. Noted in FINDINGS.md.
- **INV-025 non-combat narration sweep** — still open from earlier.

## Next Steps

1. Push `master` (3 commits ahead: 2.10.1 + 2.10.2 + 2.10.3) — awaiting approval.
2. Merge `master` → `diff-harness` to clear the differential xfail (closes the loop).
3. Reconcile the harness C/Python input-source asymmetry; consider repairing
   `area/midgaard.are`.
4. Extend the harness (combat/RNG slice; generated scenarios) per the spec's
   future-paths — each as its own spec→plan.
