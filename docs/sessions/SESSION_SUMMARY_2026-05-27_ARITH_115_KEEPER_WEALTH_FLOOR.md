# Session Summary — 2026-05-27 — ARITH-115 keeper/character wealth floor removed (2.9.78)

## Scope

Continued the META Class 2 ARITHMETIC_BOUNDARY close-out. Picked up
from `SESSION_STATUS.md` at "Next Intended Task" item 2 — ARITH-115,
the companion divergence surfaced (and filed) during the 2.9.77
ARITH-111 close. The previous session removed the item-shop haggle
floor at `mud/commands/shop.py:822` but held back the keeper-side
bookkeeping clamp because the two wealth helpers serve both buy and
sell paths and needed their own focused regression test.

This session closed ARITH-115 with a single TDD-first commit
(`3e94e6b`, 2.9.78).

## Outcomes

### `ARITH-115` — ✅ FIXED (2.9.78)

- **Python**: `mud/commands/shop.py:461` (`_set_keeper_total_wealth`) and `:473` (`_set_character_total_wealth`)
- **ROM C**: `src/act_obj.c:2747-2748` (keeper bookkeeping in `do_buy`)
- **Gap**: ARITH-115 — both helpers clamped `total = max(total, 0)` and split via Python `//`/`%`. ROM adds keeper gold/silver raw (`keeper->gold += cost*number/100; keeper->silver += cost*number - (cost*number/100)*100;`) with no floor. On the ARITH-111 player-refund branch (`shop.profit_buy < 50` + winning haggle → negative `cost`) with a near-broke keeper, ROM lets keeper wealth drift below zero; Python silently floored at 0, swallowing the refund-side loss.
- **Fix**: Floors removed from both helpers; `//`/`%` switched to `c_div`/`c_mod` so negative totals split ROM-faithfully (e.g. `cost = -9 → gold = 0, silver = -9`, matching ROM's incremental adds). ROM has no keeper-side safety net; the only clamp is `deduct_cost`'s end-of-function rebalance at `src/handler.c:2412-2421`, which applies to the *character* and is already mirrored at `mud/handler.py:918-923`.
- **Tests**: `tests/integration/test_arith_115_keeper_wealth_no_floor.py` — 1 case (profit_buy=40, cost=100, roll=99, keeper starts at 0 wealth → drifts to −9). Verified failing pre-fix (got 0, want −9), passing post-fix. Full integration suite: **2342 passed, 3 skipped** in 87.45s (+1 from 2.9.77).

## Files Modified

- `mud/commands/shop.py:461,473` — drop `max(total, 0)` floor in both wealth helpers; switch `//`/`%` to `c_div`/`c_mod`; add ROM-cite comments. Also imported `c_mod` from `mud.math.c_compat`.
- `tests/integration/test_arith_115_keeper_wealth_no_floor.py` — new regression (near-broke keeper + negative haggle cost → keeper wealth drifts negative).
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — flip ARITH-115 row 32 to ✅ FIXED; update status header (17 FIXED / 17 N/A / 13 ❌ MISSING of 47 total).
- `CHANGELOG.md` — new 2.9.78 section with ARITH-115 Fixed entry.
- `pyproject.toml` — 2.9.77 → 2.9.78.

## Test Status

- `pytest tests/integration/test_arith_115_keeper_wealth_no_floor.py` — 1/1 passing.
- `pytest tests/test_shops.py` — 36/36 passing (no wealth-floor regressions).
- `pytest tests/integration/test_arith_111_haggle_no_floor.py` — 1/1 passing (companion path unaffected).
- Full integration suite: **2342 passed, 3 skipped** in 87.45s.
- Pre-existing flake (`tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`) unchanged.

## Next Steps

1. **Push** — 3 commits ahead of `origin/master` (2.9.77 ARITH-111 fix, 2.9.77 handoff, 2.9.78 ARITH-115 fix). Push needs user approval. Together they ship 2.9.77 + 2.9.78. A 2.9.78 handoff commit (this summary + SESSION_STATUS) will make 4.
2. **ARITH-114** — PC stat ceiling divergence on `get_curr_stat` (Python flat 25 vs ROM per-race/class `max_stat` at `src/handler.c:861-869`). Only matters above stat-22; best handled in a focused stat-table session, separate from the shop/haggle line.
3. **Remaining ARITH triage**: 13 ❌ MISSING. The remaining entries are mostly higher-context floors requiring downstream effect analysis rather than single-line removals. Triage doc `docs/parity/audits/ARITHMETIC_BOUNDARY.md` has the list.
4. **Pre-existing lint** parked: B007/F841 at `mud/skills/handlers.py:672/1734/3469/3616/6249`, `mud/handler.py:566-567,960`, `tests/integration/test_do_practice_command.py:255`, `mud/commands/combat.py:685`, `mud/commands/consumption.py:11,164-166`. Also two pre-existing F541 (extraneous `f` prefix) in `mud/commands/shop.py:798` and one nearby — unrelated to this work.
5. **GitNexus**: PostToolUse stop-and-reindex fired after the ARITH-115 commit and was honored — graph reindexed (40,918 nodes / 68,585 edges, 24.1s). The documented 32KB-per-file scope-extraction failures persist on the known file list but did not block. Graph current at HEAD `3e94e6b`.
6. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs` — unrelated; safe to ignore.
7. **Worktree hygiene** — locked worktrees still present in `.claude/worktrees/`.
