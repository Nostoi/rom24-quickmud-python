# Session Status — 2026-05-30 — do_cast Object-Targeting Parity

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **CAST-004/005/006 — do_cast object-targeting legs ✅ DONE (2.11.52)** —
    ROM `TAR_OBJ_INV`, `TAR_OBJ_CHAR_OFF` object fallback, `TAR_OBJ_CHAR_DEF`
    object fallback all routed through `do_cast`. Object-only spells (`identify`,
    `enchant armor`, `enchant weapon`, `fireproof`, `create water`,
    `detect poison`, `recharge`) now resolve via `get_obj_carry`. Offensive
    dual-target spells (`curse`, `poison`) fall back to `get_obj_here` after
    character search fails. Defensive dual-target spells (`bless`,
    `invisibility`, `remove curse`) fall back to `get_obj_carry` after
    character search fails. Error messages match ROM byte-for-byte.
  - **Before that**: group-command lint cleanup (2.11.51), INV-025 (2.11.50),
    INV-001 shop haggle cousin (2.11.49), FIGHT-032/033/034, VISION-002,
    ACT-CAP-001/002/003/004.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-30_DO_CAST_OBJECT_TARGETING.md](SESSION_SUMMARY_2026-05-30_DO_CAST_OBJECT_TARGETING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.52 |
| Tests | 10 new integration tests (all green); full suite passes |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants — continue probe/close cycle |

## Next Intended Task

Continue cross-file invariants as the primary pass. Pick the next candidate area
not yet covered by an INV row, or address a carried-open maintenance item with
appropriate impact analysis.

Carried-open items: known xdist flakes (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); `Character.pet` stale type annotation
(GitNexus reports HIGH risk on the field, so handle deliberately).

## Commit / push state

- Working tree: clean (all changes included in the 2.11.52 commit).