# Session Summary — 2026-06-19 — diff-harness widening: examine/compare command coverage

## Scope

Picked up from the fully-closed INV-050 work (prior session). The per-file audit
tracker is exhausted (all P0/P1/P2 at 100%), so the active mode is the
cross-file / divergence-class sweep. Per `DIVERGENCE_CLASS_ROSTER.md`, the only
**enumeration-independent** lever (guardrail 3 — finds unknown-unknowns) is
widening `tools/diff_harness/` against the live ROM C oracle. Class 11 (mobprog
dispatch) is COMPLETE; the open frontier is **non-mobprog command coverage**.
This session widened the harness with the `examine` and `compare` commands,
chosen (per advisor steer) as read-only paths with the lowest setup cost and the
highest output-rendering surface (the FINDING-021/022/033 class).

## Outcomes

### `do_examine` differential coverage — ✅ CLEAN (no divergence)

- **ROM C**: `src/act_info.c` `do_examine` — runs `do_look <obj>`, then for
  ITEM_CONTAINER / ITEM_DRINK_CON / ITEM_MONEY / ITEM_CORPSE_* peeks inside
  (`look in <obj>`).
- **Coverage**: container (bag 3032), drink-con (bottle 3001), weapon (sword
  3021 — default branch).
- **Result**: Python and the live C oracle converge on the **first pass**.
  Notably both reproduce ROM's verbatim `"It's more than half-filled with  a
  amber liquid."` (double-space + "a amber", not "an amber") drink-level wording.
- **Tests**: `tests/test_diff_harness_generated.py::test_generated_examine_object_branches_matches_live_c`
  (fixed scenario, passes) + `examine_bag`/`examine_bottle`/`examine_sword`
  read-only rules on `DeterministicNoRngDiffMachine`.

### `do_compare` differential coverage — ✅ CLEAN (no divergence)

- **ROM C**: `src/act_info.c` `do_compare` — fully deterministic; compares
  weapon dice (`(1+value[2])*value[1]` new-format) or armor AC, with act-
  substituted `$p`/`$P` output.
- **Coverage**: item-type mismatch (sword vs jacket → `"You can't compare $p and
  $P."`), value comparison (small sword value 6 > dagger value 5 → `"$p looks
  better than $P."`), same-object (`compare sword sword` → `"You compare $p to
  itself.  It looks about the same."`).
- **Result**: convergence on the first pass — locks the `$p`/`$P` substitution +
  first-letter cap.
- **Tests**: `tests/test_diff_harness_generated.py::test_generated_compare_objects_matches_live_c`
  (fixed scenario, passes) + `compare_sword_to_jacket` read-only rule.

### Recall note (why fixed scenarios, not just rules)

An instrumented 40×14 exploration of the generated state machine showed only
`examine bag` (×4) and `examine bottle` (×1) actually fired — `examine sword`
and `compare sword jacket` never reached their preconditions. Generated rules
with rare preconditions fire unreliably, so the two **fixed scenarios** are the
guaranteed per-run lock; the rules add opportunistic coverage on top.

## Files Modified

- `tools/diff_harness/generated.py` — 4 read-only `examine_*`/`compare_*` rules
  added to `DeterministicNoRngDiffMachine`.
- `tests/test_diff_harness_generated.py` — 2 fixed C-oracle scenario tests.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — Class 11 Phase-C narrative extended
  with the 2.14.134 non-mobprog command-widening note.
- `CHANGELOG.md` — `Added` entry under `[Unreleased]`.
- `pyproject.toml` — 2.14.133 → 2.14.134.

## Test Status

- New scenarios: `test_generated_examine_object_branches_matches_live_c`,
  `test_generated_compare_objects_matches_live_c` — both pass against the live
  C oracle (`src/diffshim` present and exercised, not skipped).
- Diff-harness suite (generated + smoke + unit): 88 passed.
- Full suite: **5843 passed, 4 skipped, 0 failed** (278s).
- `ruff check` / `ruff format` clean. gitnexus detect_changes: LOW, 0 affected
  processes (harness/test-only, no production code).

## Next Steps

The examine/compare surface is clean — continue non-mobprog command widening of
the diff harness (the enumeration-independent lever). Unexercised deterministic
candidates surveyed this session but not yet done: container open/close/lock/
unlock (the do_open/do_close OBJECT branch, distinct from the door-EXIT branch
already covered), `wear all`/`get all`/`drop all` bulk loops, and `sacrifice`
(state-mutating — Class 10 lifecycle; verify whether `do_sacrifice` draws RNG in
`src/act_obj.c` before deciding on a `__seed` bracket). Lower priority:
`mud/entrypoint.py` dead-code cleanup. Reminder (guardrail 3): a clean sweep here
means "this known surface is locked," never "close to ROM parity."
