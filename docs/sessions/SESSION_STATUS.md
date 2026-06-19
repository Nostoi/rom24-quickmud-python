# Session Status — 2026-06-19 — /loop gap-closer: get_cost runtime-state parity (5/5)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (Layer C) — per-file audit
  tracker exhausted of actionable rows. This `/loop` session closed 5 shop-pricing
  gaps in `_get_cost`/`do_sell`, each verified against ROM C `src/act_obj.c` —
  all in the proto→runtime divergence class (ROM prices from live object/list
  state; Python read the prototype).
- **Last completed** (this `/loop` session, target 5/5 met, master, **committed** — not yet pushed):
  - `6e6674ac` v2.14.159 — **SELL-006**: sell-haggle bonus base uses runtime `obj.cost`.
  - `90e47f9e` v2.14.160 — **GETCOST-003**: `ITEM_SELL_EXTRACT` objects skip the same-item discount.
  - `44fe1a93` v2.14.161 — **GETCOST-002**: same-item discount compounds per matching copy (no `break`); fixed a latent `1<<18`≠`ITEM_INVENTORY` test bug.
  - `5161ce01` v2.14.162 — **GETCOST-004**: same-item discount requires a matching `short_descr` (ROM ANDs pIndexData + descr).
  - `f3233408` v2.14.163 — **GETCOST-005**: wand/staff charge pricing uses runtime `obj.value` (depleted charges).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_GETCOST_RUNTIME.md](SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_GETCOST_RUNTIME.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.163 |
| Tests | 5877 passed, 4 skipped (full suite, captured directly) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep (Layer C) |
| Open findings | None in `ACT_OBJ_C_AUDIT.md` — `get_cost` runtime-state class fully reconciled |

## Next Intended Task

Per-file tracker remains exhausted; continue the cross-file / divergence-class
sweep. Candidate next probes in `act_obj.c`: (1) `do_value` — confirm it mirrors
every `get_cost`/visibility gate now in `do_sell`; (2) the `get_obj_keeper` /
buy-side cost-inheritance path — does a bought item's runtime `obj.cost` get
clamped and re-stocked exactly as ROM `do_buy` :2765-2766? Otherwise pick a fresh
divergence-class area (affect ticks, position transitions) via
`/rom-divergence-sweep`.

**Durable lessons (reinforced this session):** (1) the per-gap `-k` suite is NOT
sufficient — GETCOST-002's no-break change altered sell pricing across every test
where a keeper carries matching stock; only the FULL suite surfaced the one
sibling it broke. (2) Hardcoded hex flags are a real bug source: the wand test's
`1<<18` was never `ITEM_INVENTORY` (8192/bit 13), so it silently tested the wrong
discount path — use the enum (AGENTS.md rule). (3) Test fixtures that set
`proto.value`/`proto.cost` but not the runtime `obj.value`/`obj.cost` break once
the implementation correctly reads runtime state — sync both (the spawn
invariant). (4) Probe-then-scope (read ROM C → read Python → one failing test)
mined 4 genuine gaps from a single `get_cost` function once the documented OPEN
list was exhausted.
