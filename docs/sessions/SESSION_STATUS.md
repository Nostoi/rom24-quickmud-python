# Session Status — 2026-06-19 — /loop gap-closer: give/drink/value + group PERS (5/5)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (Layer C) — per-file audit
  tracker exhausted of actionable rows. This `/loop` session closed 1 documented
  gap (GROUP-005) + 4 **probe-surfaced** gaps from parallel C-vs-Python probes of
  `do_give`, `do_drink`, and the shop `value` command, each re-verified against ROM C.
- **Last completed** (this `/loop` session, target 5/5 met, master, **pushed**):
  - `55ae5626` v2.14.149 — **GROUP-005**: do_group display/broadcasts PERS-mask names ($n/$N/$s via act_format).
  - `a6bc1878` v2.14.150 — **GIVE-004**: money-changer gold exchange drops spurious `/100` (`95*amount`).
  - `8bb85e65` v2.14.151 — **GIVE-005**: give-to-shopkeeper refusal sets `ch->reply`.
  - `6d24b5c6` v2.14.152 — **DRINK-011**: drink condition deltas use `c_div` (negative liq_affect).
  - `02dcb93b` v2.14.153 — **VAL-005**: do_value keeper messages render `$n`/`$p` (not "The shopkeeper").
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_GIVE_DRINK_VALUE.md](SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_GIVE_DRINK_VALUE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.153 |
| Tests | 5867 passed, 4 skipped (full suite, `PYTEST_EXIT=0`, captured directly) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep (Layer C) |
| Open findings | None tracked OPEN; unmined probe candidates listed under Next Intended Task |

## Next Intended Task

Per-file audit tracker remains exhausted → keep probing fresh surfaces with
throwaway C-oracle-vs-pyreplay reads. **Unmined probe candidates surfaced this
session but NOT yet closed (verify against ROM C before treating as gaps):**
shop `do_buy`/`do_list` buyer + keeper `can_see_obj` filters (ROM `get_obj_keeper`,
`src/act_obj.c:2459-2460`); `get_cost` using `proto.cost` vs runtime `obj->cost`
after a haggle; `do_sell` 95% cap skipped when `buy_price == 0` (ROM clamps to 0).
Also flip the stale MOB_CMDS Phase-1 "⚠️ DIVERGENT" inventory labels to ✅ (the
Phase-3 gaps MOBCMD-001..021 are all closed — labels never updated).

**Durable lessons (reinforced this session):** (1) the per-gap `-k` suite is NOT
sufficient — run the FULL suite before pushing; VAL-005 broke a stale assertion in
`tests/test_shops.py`, a file the `-k` filter never touched. (2) Re-verify every
probe candidate against ROM C source before treating it as a gap — several
candidates (weather `\n\r` byte-order, `do_split` keyword parsing, changer
`IS_NPC`/`can_see`) were correctly rejected as non-divergences (delivery-layer
normalization / intentional legacy / non-observable). (3) Stale-✅ audit notes are
real: GIVE-004, DRINK-011, and VAL-005 each contradicted a prior "verified ✅".
Commits 55ae5626..02dcb93b on master.
