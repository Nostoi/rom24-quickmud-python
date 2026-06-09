# Session Status — 2026-06-09 — TABLES-004 MEdit mobprog flags (2.13.42)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **`TABLES-004` resolved.** OLC MEdit `addmprog` now uses ROM-correct
    `mprog_flags` values from `mud.mobprog.Trigger`, matching
    `src/tables.c:298-314` and `src/merc.h:1971-1986`. Builder-created
    `entry`, `speech`, `greet`, and related mobprogs now set the same bits the
    runtime `HAS_TRIGGER` checks.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_TABLES004_MEDIT_MPROG_FLAGS.md](SESSION_SUMMARY_2026-06-09_TABLES004_MEDIT_MPROG_FLAGS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.42 |
| Tests | 5466 passed, 5 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 18 generated-oracle tests |
| Class 11 dynamic widening | TABLES-004 MEdit mobprog trigger-value probe resolved |

## Next Intended Task

Continue Class 11 / dynamic differential widening on another deterministic
command/watch-set surface. Good candidates are a generated/source-read probe that
follows OLC-created mobprogs into runtime trigger dispatch now that the builder
sets ROM-correct bits, or another non-combat lifecycle probe anchored in primary
ROM source. Avoid duplicating `nuke_pets` unless the ROM/Python read exposes a
specific missing contract.
