# Session Status — 2026-06-09 — Entry trigger guard (2.13.41)

## Current State

- **Active mode**: divergence Class 11 / dynamic differential widening
  (per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **`MOVE-007` / `ENTER-020` resolved.** NPC directional and portal movement
    now dispatch `TRIG_ENTRY` only when `HAS_TRIGGER(ch, TRIG_ENTRY)` is true
    (`char.mprog_flags & Trigger.ENTRY`), matching ROM `act_move.c:240` and
    `act_enter.c:219`. NPCs without the bit stay silent; PCs still run the
    separate greet path.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-09_ENTRY_TRIGGER_GUARD.md](SESSION_SUMMARY_2026-06-09_ENTRY_TRIGGER_GUARD.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.41 |
| Tests | 5465 passed, 5 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced |
| Diff-harness scenarios | 10 static + 18 generated-oracle tests |
| Class 11 dynamic widening | MOVE-007 / ENTER-020 entry-trigger guard probe resolved |

## Next Intended Task

Continue Class 11 / Phase C dynamic differential widening on another
deterministic command/watch-set surface. Prefer mob entry/greet ordering with
real `mprog_flags` and a concrete observable, or another source-read lifecycle
probe; `nuke_pets` already has substantial INV-020/INV-025 coverage, so avoid
duplicating it unless the ROM/Python read exposes a specific missing contract.
