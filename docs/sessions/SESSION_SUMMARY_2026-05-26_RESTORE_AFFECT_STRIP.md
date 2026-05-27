# Session Summary — 2026-05-26 — `do_restore` strips negative affects (2.9.51)

## Scope

Continuation of the 2026-05-26 session series. After the slay/purge
cluster (2.9.48–2.9.50) brought the immortal load/purge/slay surface
to ROM parity, probed adjacent immortal commands in the same file
(`mud/commands/imm_load.py`). `do_restore` had a clear gap: the five
`affect_strip` calls ROM makes (plague/poison/blindness/sleep/curse)
were left as a TODO comment in Python's `_restore_char`.

## Outcomes

### `RESTORE-001` — ✅ FIXED (`21c92b8`, 2.9.51)

- **Python**: `mud/commands/imm_load.py:_restore_char` — added a loop
  calling `char.strip_affect(name)` for each of plague/poison/
  blindness/sleep/curse before refilling vitals.
- **ROM C**: `src/act_wiz.c:2807, 2839, 2861` — all three restore
  paths (room loop, "all" descriptor loop, named victim) call the
  same five `affect_strip` invocations before vitals reset.
- **Gap (pre-fix)**: Python's `_restore_char` only refilled
  hit/mana/move and clamped position. The affect strip was a TODO
  comment. A poisoned/plagued/blinded/sleeping/cursed character that
  got restored stayed afflicted, contrary to ROM.
- **Tests**: `tests/integration/test_restore_strips_affects.py`
  — 1/1:
  - `test_restore_strips_poison_plague_blindness_sleep_curse` —
    applies all five negative affects to a victim, calls
    `do_restore(immortal, "")` (room-restore path), asserts
    `has_spell_effect(name)` returns False for all five.
  Integration suite: **2239 passed, 3 skipped** in 72s.
- **No new INV row** — single-function intra-module fix.

### Deferred (next gap-closer candidates)

- **Position-transition adjacency** — `update_pos` callers probe
  (do_yell, do_emote-while-down).
- **Group-leader on logout vs persistence** — saved characters with
  `leader != self` reload with dangling pointer reconstituted from
  save format.
- **Other `imm_load.py` adjacent gaps** — `_restore_char` does not
  call `update_pos` (ROM does at the same line as the affect strips);
  current Python sets position to STANDING directly if below STANDING,
  which matches the post-hit>0 branch of update_pos. Benign as long
  as hit > 0 post-restore (always true since we just refilled), but
  the form is divergent.

## Files Modified

- `mud/commands/imm_load.py` — `_restore_char` strips five negative
  affects before refilling vitals
- `tests/integration/test_restore_strips_affects.py` — NEW (1 test)
- `CHANGELOG.md` — 2.9.51 section
- `pyproject.toml` — 2.9.50 → 2.9.51

## Test Status

- `tests/integration/test_restore_strips_affects.py` — 1/1 ✅
- Adjacent suites (slay broadcast / slay raw_kill / purge extract /
  act_wiz parity) — 112/112 ✅
- Integration suite: **2239 passed, 3 skipped** in 72s wall-clock
- Full suite **not run this commit** (last run 1242s for 2.9.50;
  RESTORE-001 is a low-blast-radius single-function fix touching a
  helper used only by `do_restore`)

## Next Steps

1. **Push approval** required for 2.9.51 (`21c92b8`). Per standing
   rule: do NOT push without explicit per-cluster approval
   ("yes push v2.9.51 to origin/master").
2. **GitNexus refresh** — index multiple commits stale. Run
   `npx gitnexus analyze --skip-agents-md` before next probe.
3. **Probe-then-scope candidates remaining**:
   - **Position-transition adjacency** — `update_pos` callers.
   - **Group-leader on logout vs persistence**.
