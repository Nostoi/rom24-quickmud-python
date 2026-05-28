# Session Summary — 2026-05-27 — ARITH-203/204 plague-tick mana/move drain (2.9.79)

## Scope

Continued the META Class 2 ARITHMETIC_BOUNDARY close-out. Two pieces
this session:

1. Wrote the deferred handoff for the prior session's ARITH-115 close
   (2.9.78) — `SESSION_STATUS.md` had still been showing ARITH-115 as
   ❌ FILED at version 2.9.77, even though the fix was committed
   (`3e94e6b`). Produced `SESSION_SUMMARY_2026-05-27_ARITH_115_KEEPER_WEALTH_FLOOR.md`
   and refreshed `SESSION_STATUS.md` (committed `8d5be82`).
2. Closed **ARITH-203 + ARITH-204** as a paired single-commit TDD fix
   (`8dea45a`, 2.9.79), and filed one out-of-scope finding (**GL-024**).

A Sonnet research subagent surveyed all 13 then-open ❌ MISSING ARITH
gaps and ranked ARITH-203/204 as the cleanest next target (same tick,
same ROM line family, no policy ambiguity). Its survey also flagged
ARITH-104/208 as likely-N/A or UB-policy candidates and ARITH-114 as
needing a focused stat-table session.

## Outcomes

### `ARITH-203` / `ARITH-204` — ✅ FIXED (2.9.79)

- **Python**: `mud/game_loop.py:626-627` (`_char_update_tick_effects`, plague branch)
- **ROM C**: `src/update.c:843-845` (`char_update`, plague tick)
- **Gap**: Python clamped `character.mana = max(0, mana - dam)` and the same for `move`. ROM does `dam = UMIN(ch->level, af->level/5 + 1); ch->mana -= dam; ch->move -= dam;` raw — pools may go negative and regenerate back toward zero next tick.
- **Fix**: Both floors removed (one commit — same tick, same ROM line family). ROM C reference confirmed by reading the full plague block at `src/update.c:794-846`, not just the cited line.
- **Tests**: `tests/integration/test_arith_203_204_plague_drain_no_floor.py` — 1 case (level=10, af.level=10 → dam=3; mana 1 → −2, move 2 → −1). Verified failing pre-fix (got 0), passing post-fix. Full integration suite: **2343 passed, 3 skipped** in 82.29s.

### `GL-024` — ❌ OPEN (filed, not closed)

- **Python**: `mud/game_loop.py:_char_update_tick_effects` (plague branch, `if af_level > 1:` gate)
- **ROM C**: `src/update.c:818-819` — `if (af->level == 1) continue;`
- **Divergence**: ROM skips the *entire* plague block (spread + mana/move drain + `damage()`) when the plague affect level is 1. Python gates only the spread on `if af_level > 1:`, so a level-1 plague keeps draining mana/move and dealing disease damage where ROM goes dormant. Surfaced while reading the plague block for ARITH-203/204. Filed per AGENTS.md "out-of-scope bugs surfaced mid-audit" rule as a local missing-branch divergence.
- **Filed in**: `docs/parity/UPDATE_C_AUDIT.md` Gap Table (new row GL-024); `update.c` subsystem-tracker row annotated with the open follow-up.

## Files Modified

- `mud/game_loop.py:626-627` — drop `max(0, ...)` floors on plague mana/move drain; add ROM-cite comment.
- `tests/integration/test_arith_203_204_plague_drain_no_floor.py` — new regression (plagued NPC with mana/move below dam → negative pools).
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — flip rows 22/23 (ARITH-203/204) to ✅ FIXED; update status header (19 FIXED / 17 N/A / 11 ❌ MISSING) and Batch C summary.
- `docs/parity/UPDATE_C_AUDIT.md` — new GL-024 ❌ OPEN row.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — annotate `update.c` row with ARITH-203/204 closure + open GL-024.
- `CHANGELOG.md` — new 2.9.79 section (ARITH-203/204 Fixed, GL-024 Changed).
- `pyproject.toml` — 2.9.78 → 2.9.79.
- (prior commit `8d5be82`) `docs/sessions/SESSION_SUMMARY_2026-05-27_ARITH_115_KEEPER_WEALTH_FLOOR.md` + `SESSION_STATUS.md`.

## Test Status

- `pytest tests/integration/test_arith_203_204_plague_drain_no_floor.py` — 1/1 passing.
- `pytest tests/test_char_update_rom_parity.py` + `tests/integration/test_char_update_lethal_tick_iteration.py` — 32/32 (no tick regressions).
- Full integration suite: **2343 passed, 3 skipped** in 82.29s.
- `ruff check mud/game_loop.py <new test>` — clean.

## Next Steps

1. **Push approval needed** — local `master` is now **5 commits** ahead of `origin/master` (2.9.77 ARITH-111 + handoff, 2.9.78 ARITH-115 + handoff, 2.9.79 ARITH-203/204). Verify with `git log origin/master..HEAD`. Shipping covers 2.9.77 → 2.9.79.
2. **GL-024** — close the level-1 plague `continue` skip. Small fix: wrap the drain + `damage()` (and skip the whole block) when `af_level == 1`, mirroring ROM `update.c:818-819`. Test: plagued NPC with `af.level == 1` must take no damage and no mana/move drain that tick.
3. **Remaining ARITH triage**: 11 ❌ MISSING. Subagent survey notes (verify before closing):
   - **ARITH-201** (`game_loop.py:426`, `_destroy_light`) — the carry_weight floor is on a *fallback* path only reached by objects WITHOUT `pIndexData`; real objects extract via `_extract_obj` (floor already removed via ARITH-108/109). Check production reachability — may be N/A or test-double-only.
   - **ARITH-205** (`game_loop.py:813`) — carry_number floor; the function recalculates carry_weight via `_recalculate_carry_weight()` afterward, so only the carry_number side diverges. Own test needed (not a batch with 201).
   - **ARITH-202** (`game_loop.py:454`, room light decrement) — quick floor removal; harmless in practice but a divergence.
   - **ARITH-004/017/018/019** — `max(1, level)` floors in combat/skills; all flagged "reachable? No" at triage (level-0 dispatch structurally impossible) — likely N/A reclassifications, not fixes. Verify dispatch gates first (same pattern as ARITH-006/007/008/013/014).
   - **ARITH-104** (`movement.py:428`) — `max(0, move_cost // 2)`; movement table values ≥1 so floor is dead-code — strong N/A candidate.
   - **ARITH-206/207** (`reset_handler.py:405,665`) — room_limit / arg4 floors; ROM arg=0 semantics unclear, need `db.c` reset re-read before touching.
   - **ARITH-208** (`templates.py:172`) — `max(0, dice+bonus)`; negative `max_hit` at spawn is the same UB-divisor class as ARITH-001/002/003 — check `docs/divergences/UB_DIVISORS.md` policy before deciding fix vs N/A.
   - **ARITH-114** — PC stat ceiling on `get_curr_stat`; genuine stat-table wiring task (`pc_race_table[race].max_stats` + prime/human bonuses), needs a focused session.
4. **GitNexus**: stop-and-reindex honored after each commit; graph reindexed (background, exit 0). 32KB scope-extraction failures persist on the documented file list (incl. `game_loop.py`) — `gitnexus_impact` on `_char_update_tick_effects` returned 0 callers/LOW (untrustworthy), cross-checked via grep (single caller at `game_loop.py:720`).
5. **Pre-existing lint** parked: B007/F841 cluster (see prior summaries); two F541 in `mud/commands/shop.py:798` area.
6. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
7. **Worktree hygiene** — locked worktrees still present in `.claude/worktrees/`.
