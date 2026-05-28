# Session Summary — 2026-05-27 — GL-024 level-1 plague dormant (2.9.80)

## Scope

Immediately after pushing 2.9.77 → 2.9.79 to `origin/master`, closed
the **GL-024** follow-up that was filed during the 2.9.79 ARITH-203/204
plague-drain close. GL-024 was the smallest remaining next-target: a
single missing-branch divergence in the plague tick, fully scoped and
documented from the prior commit.

## Outcomes

### `GL-024` — ✅ FIXED (2.9.80)

- **Python**: `mud/game_loop.py:_char_update_tick_effects` (plague branch)
- **ROM C**: `src/update.c:818-819` (`char_update`, `if (af->level == 1) continue;`)
- **Gap**: ROM's plague tick prints the writhe messages, then `continue`s the char loop when the plague affect level is 1 — skipping spread, mana/move drain, and `damage()`. Confirmed by reading the full char-loop body (`src/update.c:803-872`): the affect if/else chain is the last thing in the loop body, so `continue` at line 819 skips exactly spread+drain+damage. Python gated only the *spread* on `if af_level > 1:`; the drain and `damage()` ran regardless, so a level-1 plague kept draining mana/move and dealing disease damage.
- **Fix**: Moved the drain + `damage()` block inside the existing `if af_level > 1:` guard (rather than adding a redundant always-true conditional or an early return). A level-1 plague now prints the writhe messages, then goes dormant — mirroring ROM's `continue`.
- **Tests**: `tests/integration/test_gl_024_level1_plague_dormant.py` — 1 case (level-1 plague NPC → mana/move/hit all unchanged by the tick). Verified failing pre-fix (mana drained 20→19), passing post-fix. Full integration suite: **2344 passed, 3 skipped** in 85.66s.

## Files Modified

- `mud/game_loop.py` — re-indent drain + `damage()` block under `if af_level > 1:`; add GL-024 ROM-cite comment.
- `tests/integration/test_gl_024_level1_plague_dormant.py` — new regression.
- `docs/parity/UPDATE_C_AUDIT.md` — flip GL-024 row to ✅ FIXED.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — update `update.c` row (GL-024 closed; no open follow-ups).
- `CHANGELOG.md` — new 2.9.80 section (GL-024 Fixed).
- `pyproject.toml` — 2.9.79 → 2.9.80.

## Test Status

- `pytest tests/integration/test_gl_024_level1_plague_dormant.py` — 1/1.
- `pytest tests/integration/test_arith_203_204_plague_drain_no_floor.py` + `tests/test_char_update_rom_parity.py` + lethal-tick — 33/33 (no plague-tick regressions).
- Full integration suite: **2344 passed, 3 skipped** in 85.66s.
- `ruff check` on edited files — clean.

## Next Steps

1. **Push approval needed** — local `master` is **1 commit** ahead of `origin/master` (`84113e1` GL-024 fix, 2.9.80). The handoff commit this produces will make 2. Verify with `git log origin/master..HEAD`.
2. **Remaining ARITH triage**: 11 ❌ MISSING. Cleanest straight fixes per the vetted survey (see `SESSION_SUMMARY_2026-05-27_ARITH_203_204_PLAGUE_DRAIN.md`):
   - **ARITH-202** (`game_loop.py:454`, room light decrement) — quick floor removal.
   - **ARITH-205** (`game_loop.py:813`, carry_number) — own test; function recalcs carry_weight separately so only carry_number diverges.
   - **ARITH-201** (`game_loop.py:426`, `_destroy_light`) — floor on a *fallback* path only reached by objects WITHOUT `pIndexData`; verify production reachability (may be N/A / test-double-only).
   - **ARITH-004/017/018/019** — `max(1, level)` floors flagged "reachable? No" — likely N/A reclassifications (verify dispatch gates, same pattern as ARITH-006/007/008/013/014).
   - **ARITH-104** (`movement.py:428`) — dead-code floor, strong N/A candidate.
   - **ARITH-206/207** (`reset_handler.py:405,665`) — need `db.c` reset arg=0 semantics re-read.
   - **ARITH-208** (`templates.py:172`) — UB-divisor class; check `docs/divergences/UB_DIVISORS.md` before fix-vs-N/A.
   - **ARITH-114** — PC stat ceiling; focused stat-table session.
3. **GitNexus**: stop-and-reindex honored after each commit; graph reindexed (background). 32KB scope-extraction failures persist on the documented file list (incl. `game_loop.py`); cross-check `gitnexus_impact` clean results with grep.
4. **Pre-existing lint** parked (B007/F841 cluster; F541 in `shop.py:798` area).
5. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
6. **Worktree hygiene** — locked worktrees still present in `.claude/worktrees/`.
