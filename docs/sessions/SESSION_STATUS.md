# Session Status — 2026-06-10 — INV-015 Affect-Tick Sub-Contract Enforcement (2.13.61)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **INV-015 AFFECT-EXPIRY-LIFECYCLE sub-contracts locked (2.13.61)** — probe of
    `src/update.c:762-786` confirmed `tick_spell_effects` is faithful. Two
    previously unguarded sub-contracts are now enforcement-tested:
    - **GL-026 RNG guard**: `number_range(0,4)` is consumed unconditionally per
      `duration>0` affect before `level>0` check — locked by
      `test_rng_slot_consumed_per_duration_positive_affect`.
    - **Dedup guard**: `src/update.c:774-775` — only the last consecutive same-type
      expiry emits `msg_off` — locked by
      `test_msg_off_dedup_suppresses_all_but_last_same_type_affect`.
  - **INV-041 SHOPKEEPER-PSOP-COHERENCE** (prior session, v2.13.60): `is_safe`
    now checks `victim.prototype.pShop`; both loaders write `MobIndex.pShop`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_INV015_AFFECT_TICK_SUBCONTRACTS.md](SESSION_SUMMARY_2026-06-10_INV015_AFFECT_TICK_SUBCONTRACTS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.61 |
| Tests | 5500 passed, 5 skipped (full suite — 2.13.61) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced |
| Diff-harness scenarios | 22 scenarios (Class 11 complete) |

## Next Intended Task

Cross-file invariants remains the active pass. Two concrete candidates:

1. **Affect-join contract** — the most actionable open gap: ROM `src/handler.c:affect_join`
   is used for plague-spread (`src/update.c:828-840`), averaging levels and summing
   durations+modifiers when the victim already has plague before calling
   `affect_to_char`. Python calls `affect_to_char` directly, so re-infection stacks
   a second plague entry instead of merging. Filed as ⚠️ Partial in
   `docs/parity/HANDLER_C_AUDIT.md:affect_join`. This is a concrete single-function
   gap — appropriate for `/rom-gap-closer` once a gap ID is assigned.

2. **Position-transition affect-application** — ROM `src/update.c:update_pos`
   (also `src/handler.c:update_pos`) strips `AFF_SLEEP` and handles position-gated
   affects. INV-016 covers the broadcast side; the affect-application side (e.g.
   sanctuary dropping below a position threshold) has no INV row yet. A
   probe-then-scope pass on `update_pos` would determine if a gap exists.
