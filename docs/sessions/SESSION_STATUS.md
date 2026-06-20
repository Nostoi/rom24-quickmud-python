# Session Status — 2026-06-19 — divergence-sweep probe (HEALER + GAIN/GROUPS)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  remains exhausted). This session ran probe-then-scope across several
  less-traveled subsystems and **closed 4 gaps**, filed 4 more for scoping, and
  reconciled 3 stale doc surfaces. Recurring theme: **three files marked ✅/100%
  audited hid real gaps** (`healer.c`, `board.c` Phase-1 table, `skills.c`
  `do_gain`/`do_groups`) — the "100% on one slice ≠ 100% on all of it" pattern.
- **Closed this session** (master, pushed through v2.14.179):
  - **HEALER-005** (v2.14.176) — insufficient-funds refusal uses ROM's
    `act("$N says '...'")` wrapper (`src/healer.c:171-176`).
  - **HEALER-006** (v2.14.177) — healer match order follows ROM if/else (`mana`
    before `refresh`); `heal m` → mana not refresh.
  - **GAIN-002** (v2.14.178) — `gain points` lowers creation points per ROM
    (`src/skills.c:149-172`); was backwards (raised points, no `<=40` gate, no
    exp recalc).
  - **GROUPS-001** (v2.14.179) — `do_groups` no longer crashes
    (`AttributeError` on the `group_known` tuple treated as a dict).
- **Doc reconciliations**: position-furniture + pet-persistence stale P2 rows
  (already implemented); `board.c` Phase-1 table flipped to match its closed
  Phase-3 gaps (+ 2 wrong gap-ID citations corrected); corrected a **stale
  handoff claim** that "FINDING-001" was an open mob-HP bug — it is FINDING-006,
  **RESOLVED 2026-05-28**, empirically re-verified (drunk #3064 hp 31, Hassan 1000).
- **Filed for scoping** (`docs/parity/SKILLS_C_DO_GAIN_AUDIT.md`):
  **GAIN-001** (gain skill/group not implemented — feature work, gated on a
  recursive `gn_add` equivalent), **GAIN-003** (`gain list` stub), **GAIN-004**
  (trainer-line act-cap class).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_HEALER_005_006_DIVERGENCE_PROBE.md](SESSION_SUMMARY_2026-06-19_HEALER_005_006_DIVERGENCE_PROBE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.179 |
| Tests | 5905 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep |
| Open findings | GAIN-001/003/004 (do_gain feature work, scoped); documented per-file surface otherwise drained |

## Next Intended Task

Documented per-file + ARITH gap surface stays drained; cross-file /
divergence-sweep is the primary pass. This session closed HEALER-005/006,
GAIN-002, GROUPS-001 and filed GAIN-001/003/004. Paths for the next session:

1. **GAIN-001 / GAIN-003 (highest concrete value)** — implement `gain <skill>` /
   `gain <group>` and `gain list` at a trainer (`src/skills.c:74-131,174-249`).
   Currently a player **cannot learn skills/groups at a trainer** (Python returns
   "That is not a valid option."). Feature work, **gated on infra**: verify
   whether `mud/account/account_service.py:add_group` is a faithful recursive
   `gn_add` (adds component skills + sub-groups) and how the `learned` skill map
   is represented, then close both. See `docs/parity/SKILLS_C_DO_GAIN_AUDIT.md`.
2. **GAIN-004** — trainer lines use lowercase f-strings instead of ROM's
   `act("$N ...")` cap (the HEALER-005 act-cap class) + the no-arg
   `do_function(trainer, &do_say, ...)` say-to-room nuance. Small.
3. **Continue probe-then-scope on fresh subsystems** — OLC save round-trips, shop
   `do_buy` haggle/credit edges, reset edge cases, mob-program trigger dispatch,
   `do_practice`. Healer/weather/drink/do_gain are now exhausted. Use
   `/rom-divergence-sweep` for the lens.

**Recurring lesson reinforced this session:** three files marked ✅/100% audited
hid real gaps (`healer.c`, `board.c` Phase-1 table, `skills.c` `do_gain`). A
"100% audited" row covers the slice someone checked, not the whole file —
re-verify against ROM C before trusting it. The stale "FINDING-001 = open mob-HP
bug" handoff claim (actually FINDING-006, resolved 2026-05-28) was the same trap.

**Infra note:** GitNexus MCP healthy; `detect_changes` returned LOW risk on every
commit (scope confined to the touched function + its audit doc). Three surfaces
(README/SESSION_STATUS/pyproject) reconcile at **2.14.179**.
