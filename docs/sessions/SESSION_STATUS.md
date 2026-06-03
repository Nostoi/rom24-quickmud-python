# Session Status — 2026-06-02 — Flag-hex Layer-A guard (2.12.76)

## Current State

- **Active mode**: cross-file invariants under the **divergence-class
  completeness lens**. This session ran a `/rom-divergence-sweep` on **class 5
  (flag-hex)** and locked it as a committed Layer-A bypass-guard.
- **Flag-hex (class 5) → ✅ Layer-A guarded** (`tests/test_flag_hex_convention.py`,
  the 4th static guard alongside RNG / equipment-key / attribute-naming). A tight
  prefix-anchored grep had exactly one legitimate hit (`mud/wiznet.py`'s
  `WiznetFlag` enum body — allowlisted), so the class proved Layer-A **feasible**
  (opposite outcome to async-delivery, which reclassified A→C). Recall validated
  against the past PARALLEL-005 / ACT_TRAIN instances. Limit: catches hex
  re-definitions, **not** decimal-literal bypasses.
- **Four offenders resolved to make the guard green** (no live behavior change):
  - **Deleted** two dead+wrong-bit `handler.py` duplicates — `is_friend`
    (HANDLER-DEAD-001: assist bits 0–4 vs canonical `OffFlag` 15–20) and
    `check_immune` (HANDLER-DEAD-002: IMM bits 0–1 vs `DefenseBit` 2–3). Both had
    no callers; live paths are `combat/assist.py` and `affects/saves.py`.
  - **Migrated** live `PLR_*` (`player_config.py`) and `COMM_DEAF`
    (`remaining_rom.py`) to derive from `PlayerFlag`/`CommFlag` (values already
    correct → byte-identical behavior).
- **Latest commits — 2.12.76**: `568639b7` (offender fixes), `6ce23769` (guard +
  docs).

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_FLAG_HEX_LAYER_A_GUARD.md](SESSION_SUMMARY_2026-06-02_FLAG_HEX_LAYER_A_GUARD.md).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.76 |
| Tests | **5356 passed, 4 skipped** (201.91s; +1 vs 2.12.75 baseline = the new guard test; zero regressions) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 26 enforced (no new rows this session) |
| Divergence-class lens | **Layer A 4/5 guarded** (RNG, equipment-key, attribute-naming, flag-hex); class 6 pointer-identity to-do |
| Lint | `ruff check .` 1762 pre-existing errors (none introduced — edited lines clean) |

## Next Intended Task

1. **Last Layer-A to-do (via `/rom-divergence-sweep`):** class 6
   (pointer-identity). Scope a pattern for `==`/`!=` between two `Character`
   references — high false-positive risk, so it may reclassify to Layer B/C (like
   async-delivery) or prove feasible (like flag-hex). Either way yields a durable
   result. Roster Layer-A would then be 5/5 (modulo reclassifications).
2. **Highest-ceiling (deliberate multi-day project):** `diff_harness` Hypothesis
   widening (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences. Phase A (live-C oracle)
   is the cost center.
3. **Standing cross-INV candidate:** mob-trigger ordering (bribe/exit/fight/kill/
   hpcnt); INV tracker consolidation (26 rows, past the ~20 soft cap).

> **Push note:** 2.12.76 (`568639b7`, `6ce23769`) + this handoff are on local
> `master`, **not pushed** — on top of the unpushed 2.12.72–2.12.75 from prior
> sessions. CHANGELOG/version reflect 2.12.76.
