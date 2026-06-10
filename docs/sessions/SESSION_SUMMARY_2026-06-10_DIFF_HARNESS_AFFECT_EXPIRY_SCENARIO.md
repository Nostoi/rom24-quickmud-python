# Session Summary — 2026-06-10 — diff-harness affect_expiry_lifecycle scenario

## Scope

Continuation from v2.13.61 (FINDINGS.md numbering cleanup). The active pass is
cross-file invariants. The previous SESSION_STATUS.md identified authoring a new
diff-harness scenario as the most concrete next step — specifically one exercising
sanctuary+haste affect bitvectors with tick expiry. This session delivered that
scenario plus the `__mana=N` meta-command required to make it work.

## Outcomes

### `affect_expiry_lifecycle` scenario — ✅ AUTHORED

- **Scenario**: `tools/diff_harness/scenarios/affect_expiry_lifecycle.json`
- **Surface covered**: spell affect bitvector set/clear across the full expiry lifecycle
- **Steps**: `__mana=500` → `__learn=sanctuary` → `cast sanctuary` → `__learn=haste` →
  `cast haste` → `affects` → `__set_affect_duration=0` → `__char_update` → `affects`
- **Python result (verified)**: steps 4 and 6 show `affects=['sanctuary', 'haste']`
  and `affect_flags=['SANCTUARY', 'HASTE']`; steps 9 and 10 show both cleared on expiry.
- **Status**: skips until a C golden is captured against the instrumented binary. This
  is the first harness coverage of the affect bitvector lifecycle — the only prior
  coverage was via `affect_armor` (apply only; no expiry).

**Debugging path**: Two issues were discovered and resolved during authoring:

1. `cast sanctuary` at level 12 with `ch_class=0` (mage) failed — sanctuary requires
   mage level 36. Fixed by raising the scenario character to level 40.
2. `cast haste` failed at level 40 with 100 mana — haste at level 40 costs more than
   the harness default. Fixed by adding the `__mana=` meta-command.

### `__mana=N` meta-command — ✅ ADDED

- **Python**: `tools/diff_harness/pyreplay.py` — sets `char.mana` and raises
  `char.max_mana` if lower; follows the `__gold=`/`__silver=` pattern
- **C shim**: `src/diff_shim/diffmain.c` — same semantics via `atoi(line+7)`
  with `ch->max_mana` guard; placed adjacent to `__silver=` handler
- **Unit test**: `tests/test_diff_harness_unit.py` —
  `test_drive_python_replay_mana_meta_sets_mana_and_max_mana` verifies mana=500
  after `__mana=500` step

`★ Insight`: The diff-harness `drive_python_replay` always starts with 100 mana
(mirroring C shim defaults). High-level spells like haste (105 mana at level 40) can't
be tested without a mana override. `__mana=N` is now available for any multi-spell
scenario. The `max_mana` raise ensures the character doesn't inadvertently regen
past the set value.

## Files Modified

- `tools/diff_harness/scenarios/affect_expiry_lifecycle.json` — new scenario file
- `tools/diff_harness/pyreplay.py` — added `__mana=N` handler in `_run_python_command`
- `src/diff_shim/diffmain.c` — added `__mana=N` handler adjacent to `__silver=`
- `tests/test_diff_harness_unit.py` — added `test_drive_python_replay_mana_meta_sets_mana_and_max_mana`
- `CHANGELOG.md` — added [2.13.62] entries
- `pyproject.toml` — 2.13.61 → 2.13.62

## Test Status

- Diff harness: 39 passed, 2 skipped (`affect_expiry_lifecycle` no golden + `shop_sell_keeper_broke`)
- Full suite: 5501 passed, 6 skipped (no regressions)

## Next Steps

The cross-file invariants pass remains active. The `affect_expiry_lifecycle` scenario
is authored but ungolden — capturing the C golden requires the instrumented binary
(`cd src && make -f Makefile.diffshim diffshim`, then
`python3 -m tools.diff_harness.capture --scenario affect_expiry_lifecycle`).

Two concrete candidates for the next session:

1. **Capture the golden** for `affect_expiry_lifecycle` if the C build environment is
   available. Once captured, the scenario becomes a live C-oracle guard for affect expiry.

2. **Author a second scenario** on an untested surface — `drink`/`eat`/`food`
   consumption (condition decay + THIRST/FULL/HUNGER bitvectors) or
   charm/follower wear-off lifecycle are the remaining unexercised surfaces called out
   in the prior SESSION_STATUS.

3. **MATH-002/003/004** — documented ⚠️ OPEN hygiene items (LOW severity) in
   `docs/parity/audits/MATH_AND_RNG.md`. Held for a future PARITY008 lint rule; no
   observable behavioral gap.
