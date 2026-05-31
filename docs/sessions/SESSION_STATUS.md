# Session Status — 2026-05-30 — INV-030 Bless Object Branch

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **INV-030 BLESS-OBJECT-BRANCH (2.11.55)** — `bless()` now handles Object
    targets per ROM `src/magic.c:788-834`: already-blessed check, evil-dispel
    branch (affect_remove_obj + REMOVE_BIT), clean-object affect via
    affect_to_obj (TO_OBJECT/APPLY_SAVES/-1/ITEM_BLESS), saving_throw -= 1
    for worn objects. All five dual-target spells now handle Object branches.
  - Probed NPC shop PCHAR flag integrity — no gap (Python matches ROM).
  - Probed `Character.pet` type annotation — deferred (type hygiene, not parity).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-30_INV030_BLESS_OBJECT_BRANCH.md](SESSION_SUMMARY_2026-05-30_INV030_BLESS_OBJECT_BRANCH.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.55 |
| Tests | 5087 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 30 enforced (INV-001..030) |
| Active focus | Cross-file invariants — continue probe/close cycle |

## Next Intended Task

Continue cross-file invariants as the primary pass. Candidate areas for probing:
- Affect-tick interaction across modules (e.g., plague spread during
  char_update and its interaction with SINGLE-DELIVERY)
- Group/follower chain contracts beyond INV-020
- Per-spell handler type annotation hygiene pass (curse missing Object in sig,
  Character.pet typed as Character instead of MobInstance)

Carried-open items: `Character.pet` type annotation hygiene;
`curse` handler type annotation hygiene (missing `Object` in signature).

## Commit / push state

- Working tree: clean (all changes included in the 2.11.55 commit).