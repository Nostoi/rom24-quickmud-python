# Session Status — 2026-06-19 — /loop gap-closer: shop visibility + runtime cost (5/5)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (Layer C) — per-file audit
  tracker exhausted of actionable rows. This `/loop` session closed 5 shop-pricing
  / visibility gaps in `do_buy`/`do_list`/`do_sell`/`get_cost`, each verified
  against ROM C `src/act_obj.c` (two were stale-✅ audit claims).
- **Last completed** (this `/loop` session, target 5/5 met, master, **committed** — not yet pushed):
  - `ee7a325d` v2.14.154 — **BUY-007**: `do_buy` applies `can_see_obj(keeper)&&can_see_obj(ch)` in the candidate loop.
  - `47f3e4cb` v2.14.155 — **LIST-004**: `do_list` hides items the buyer can't see (buyer-only filter).
  - `6470150a` v2.14.156 — **GETCOST-001**: `_get_cost` uses runtime `obj.cost` (closes haggle-resell exploit; room-reset objects resell for 0).
  - `0e31d009` v2.14.157 — **BUY-009**: buy-haggle discount base uses runtime `obj.cost`.
  - `fdaddbe2` v2.14.158 — **SELL-005**: sell-haggle 95% cap applied unconditionally.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_SHOP_VISIBILITY_COST.md](SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_SHOP_VISIBILITY_COST.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.158 |
| Tests | 5872 passed, 4 skipped (full suite, `PYTEST_EXIT=0`, captured directly) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep (Layer C) |
| Open findings | SELL-006 (🔄 OPEN, `ACT_OBJ_C_AUDIT.md`) — sell-haggle bonus base proto→obj |

## Next Intended Task

Close **SELL-006** (`docs/parity/ACT_OBJ_C_AUDIT.md`, 🔄 OPEN): `do_sell`
sell-haggle bonus base reads `proto.cost` (`shop.py:954`) where ROM uses runtime
`obj->cost` (`src/act_obj.c:2930`) — the sell-side mirror of BUY-009/GETCOST-001.
Close failing-test-first; choose `profit_buy` high enough that the 95% cap
(:2931) doesn't bind and mask the difference.

Then continue the shop / `act_obj.c` probe sweep: flip the stale MOB_CMDS Phase-1
"⚠️ DIVERGENT" inventory labels to ✅ (MOBCMD-001..021 all closed — doc hygiene
only), and probe `get_cost` ITEM_INVENTORY dupe-discount interactions.

**Durable lessons (reinforced this session):** (1) the per-gap `-k` suite is NOT
sufficient — GETCOST-001 broke 5 sibling tests across 3 files (shop + arith) that
only the FULL suite surfaced. (2) Test fixtures that `spawn_object` then mutate
the SHARED prototype leak into the keeper's default stock of the same vnum — sync
each live object's runtime cost to the proto cost (the ROM spawn invariant).
(3) Re-verify every ✅ before relying on it: BUY-007 was a stale "visibility
filter applied" claim. (4) When you forward-reference a not-yet-closed sibling
gap, file it 🔄 OPEN — do NOT pre-write its ✅ (caught mid-session for BUY-009).
