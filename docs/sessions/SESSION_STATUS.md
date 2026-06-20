# Session Status — 2026-06-19 — divergence-sweep probe (HEALER + GAIN/GROUPS)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  remains exhausted). This session ran probe-then-scope across several
  less-traveled subsystems and **closed 8 gaps** (incl. fully porting `do_gain`)
  and reconciled 3 stale doc surfaces. Recurring theme: **three files marked
  ✅/100% audited hid real gaps** (`healer.c`, `board.c` Phase-1 table, `skills.c`
  `do_gain`/`do_groups`) — the "100% on one slice ≠ 100% on all of it" pattern.
- **Closed this session** (master, pushed through v2.14.182):
  - **HEALER-005** (v2.14.176) — insufficient-funds refusal uses ROM's
    `act("$N says '...'")` wrapper (`src/healer.c:171-176`).
  - **HEALER-006** (v2.14.177) — healer match order follows ROM if/else (`mana`
    before `refresh`); `heal m` → mana not refresh.
  - **GAIN-002** (v2.14.178) — `gain points` lowers creation points per ROM
    (`src/skills.c:149-172`); was backwards (raised points, no `<=40` gate, no
    exp recalc).
  - **GROUPS-001** (v2.14.179) — `do_groups` no longer crashes
    (`AttributeError` on the `group_known` tuple treated as a dict).
  - **GAIN-001** (v2.14.180) — players can learn skills/groups at a trainer
    (runtime recursive `_gn_add`, group + skill branches, spell guard); the core
    trainer function was entirely missing.
  - **GAIN-003** (v2.14.181) — `gain list` shows the real two-table price list
    (was a stub).
  - **GAIN-004** (v2.14.182) — trainer speech lines ROM-capitalized via
    `_gain_trainer_name` (`capitalize_act_line`). `do_gain` is now fully ported
    (one bounded residual: no-arg `do_say`-to-room broadcast).
- **Doc reconciliations**: position-furniture + pet-persistence stale P2 rows
  (already implemented); `board.c` Phase-1 table flipped to match its closed
  Phase-3 gaps (+ 2 wrong gap-ID citations corrected); corrected a **stale
  handoff claim** that "FINDING-001" was an open mob-HP bug — it is FINDING-006,
  **RESOLVED 2026-05-28**, empirically re-verified (drunk #3064 hp 31, Hassan 1000).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_HEALER_005_006_DIVERGENCE_PROBE.md](SESSION_SUMMARY_2026-06-19_HEALER_005_006_DIVERGENCE_PROBE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.182 |
| Tests | 5913 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep |
| Open findings | None outstanding from this session — `do_gain` fully ported (1 bounded GAIN-004 residual); documented per-file surface drained |

## Next Intended Task

Documented per-file + ARITH gap surface stays drained; cross-file /
divergence-sweep is the primary pass. This session closed 8 gaps (HEALER-005/006,
GAIN-001/002/003/004, GROUPS-001). Paths for the next session:

1. **Continue probe-then-scope on fresh subsystems** — OLC save round-trips, shop
   `do_buy` haggle/credit edges, reset edge cases, mob-program trigger dispatch,
   `do_practice`. Exhausted this session: healer, weather/time, drink, `do_gain`/
   `do_groups`. Use `/rom-divergence-sweep` for the lens.
2. **GAIN-004 residual** (optional, bounded) — the no-arg `gain` case is ROM
   `do_function(trainer, &do_say, "Pardon me?")` (trainer says it to the *room*);
   Python returns it to the caller only. Closing it means a room broadcast, which
   changes `do_gain`'s string-return contract — defer unless the broader
   command-return-vs-broadcast architecture is revisited.

**Recurring lesson reinforced this session:** three files marked ✅/100% audited
hid real gaps (`healer.c`, `board.c` Phase-1 table, `skills.c` `do_gain`). A
"100% audited" row covers the slice someone checked, not the whole file —
re-verify against ROM C before trusting it. The stale "FINDING-001 = open mob-HP
bug" handoff claim (actually FINDING-006, resolved 2026-05-28) was the same trap.

**Infra note:** GitNexus MCP healthy; `detect_changes` returned LOW risk on every
commit (scope confined to the touched function + its audit doc). Three surfaces
(README/SESSION_STATUS/pyproject) reconcile at **2.14.182**.
