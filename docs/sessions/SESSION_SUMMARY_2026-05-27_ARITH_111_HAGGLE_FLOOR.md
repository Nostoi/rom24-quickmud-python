# Session Summary — 2026-05-27 — ARITH-111 close + ARITH-115 follow-on filing (2.9.77)

## Scope

Continued the META Class 2 ARITHMETIC_BOUNDARY close-out. Picked up
from `SESSION_STATUS.md` after the 9-commit push to `origin/master`
covering 2.9.70–2.9.76. ARITH-111 was the held-back item-shop
haggle floor at `mud/commands/shop.py:822`; the previous session
had documented its reachability (`profit_buy < 50`) but flagged the
`deduct_cost(ch, negative_cost)` interaction as needing analysis
before close.

This session:

1. Pushed the 9 accumulated parity commits to `origin/master`
   (2.9.70 → 2.9.76).
2. Probed ROM `deduct_cost` at `src/handler.c:2397-2422` with a
   negative-cost input — confirmed ROM refunds the player via
   `ch->silver -= silver` (line 2410, with `silver` being the
   negative `UMIN` result). Python's `mud/handler.py:885`
   `deduct_cost` already mirrors that arithmetic exactly. Only the
   upstream `max(0, unit_price - discount)` clamp at `shop.py:822`
   blocked the divergence.
3. Closed ARITH-111 with a TDD-first commit.
4. Surfaced a *second* divergence on the same path —
   `_set_keeper_total_wealth` / `_set_character_total_wealth` clamp
   at `shop.py:462,474` — and filed it as **ARITH-115** per
   AGENTS.md "out-of-scope bugs surfaced mid-audit, file durably"
   rule. Held back from the ARITH-111 commit because it bites only
   on the narrower sub-condition `|negative total_cost| > keeper
   current wealth` and the two helpers serve both buy and sell
   paths.

## Outcomes

### `ARITH-111` — ✅ FIXED (2.9.77)

- **Python**: `mud/commands/shop.py:822` (now line 827 post-comment-insert)
- **ROM C**: `src/act_obj.c:2722-2729` (`do_buy`, item-shop branch)
- **Gap**: ARITH-111 — Python clamped `unit_price = max(0, unit_price - discount)`; ROM does raw `cost -= obj->cost / 2 * roll / 100;` and allows `cost` to go negative.
- **Fix**: Floor removed; ROM-cite comment added. Downstream `deduct_cost(ch, total_cost)` (Python `mud/handler.py:885`) already mirrors ROM's negative-cost-refund semantics.
- **Tests**: `tests/integration/test_arith_111_haggle_no_floor.py` — 1 case (profit_buy=40, cost=100, roll=99 → unit_price = 40 − 49 = −9; player wealth 100 → 109). Full integration suite: **2341 passed, 3 skipped** in 89.17s.

### `ARITH-115` — ❌ FILED (2.9.77, not closed)

- **Python**: `mud/commands/shop.py:462` (`_set_keeper_total_wealth`) and `:474` (`_set_character_total_wealth`)
- **ROM C**: `src/act_obj.c:2747-2748` (keeper bookkeeping in `do_buy`)
- **Divergence**: ROM keeper update is `keeper->gold += cost*number/100; keeper->silver += cost*number - (cost*number/100)*100;` raw — no clamp. Python's helper clamps `total = max(total, 0)`. On the ARITH-111 refund path with a near-broke keeper, ROM lets keeper gold drift negative; Python silently floors at 0, swallowing the refund-side wealth loss. ROM's actual safety net is `deduct_cost`'s end-of-function `gold < 0 / silver < 0` clamp at `src/handler.c:2412-2421`, which Python's `deduct_cost` already mirrors at `mud/handler.py:918-923`.
- **Audit row**: `docs/parity/audits/ARITHMETIC_BOUNDARY.md` row 32 (Batch B).

## Files Modified

- `mud/commands/shop.py:822` — drop `max(0, ...)` floor on haggle-discounted `unit_price`; add ROM-cite comment.
- `tests/integration/test_arith_111_haggle_no_floor.py` — new regression for ARITH-111 (negative unit_price + player-refund assertion).
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — flip ARITH-111 row to ✅ FIXED; file ARITH-115 as new row 32; update status header (16 FIXED / 17 N/A / 14 ❌ MISSING of 47 total).
- `CHANGELOG.md` — new 2.9.77 section with ARITH-111 Fixed entry and ARITH-115 Changed entry.
- `pyproject.toml` — 2.9.76 → 2.9.77.

## Test Status

- `pytest tests/integration/test_arith_111_haggle_no_floor.py` — 1/1 passing.
- `pytest tests/test_shops.py` — 36/36 passing (no haggle-floor regressions).
- Full integration suite: **2341 passed, 3 skipped** in 89.17s.
- Pre-existing skips/flake (`tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`) unchanged.

## Next Steps

1. **Push** — 1 commit ahead of `origin/master` (`8d3c89c fix(parity): ARITH-111 …`). Together with the session-handoff commit this session will produce, push covers `2.9.77`.
2. **ARITH-115** — keeper-side / character-side wealth clamps in `mud/commands/shop.py:462,474`. Smallest closing test: same setup as ARITH-111 but with `keeper.gold = 0, keeper.silver = 0` so the refund drives keeper wealth negative. Assert `keeper.silver < 0` (or `keeper.gold < 0`). Floor removed from both helpers in one commit since they share the same ROM-mismatch pattern.
3. **ARITH-114** — PC stat ceiling (per-race/class `max_stat` vs Python flat 25). Stat-table work session — separate from shop/haggle line.
4. **Remaining ARITH triage**: 14 ❌ MISSING. The remaining MISSING entries are mostly higher-context floors requiring downstream effect analysis, not single-line removals. Triage doc has the full list.
5. **Pre-existing lint** parked: B007/F841 at `mud/skills/handlers.py:672/1734/3469/3616/6249`, `mud/handler.py:566-567,960`, `tests/integration/test_do_practice_command.py:255`, `mud/commands/combat.py:685`, `mud/commands/consumption.py:11,164-166`.
6. **GitNexus**: PostToolUse stop-and-reindex rule fired after the ARITH-111 commit; reindex launched in background via the `gitnexus-cli` skill. Verify graph is current at start of next session.
7. **Pre-existing flake** at `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs` — unrelated; safe to ignore.
8. **Worktree hygiene** — locked worktrees still present in `.claude/worktrees/`.
