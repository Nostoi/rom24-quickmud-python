# Session Status — 2026-06-08 — FINDING-030: bless zero-modifier AffectData count (2.13.25)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **FINDING-030 closed (2.13.25).** `SpellEffect.hitroll_mod` / `saving_throw_mod` defaults
    changed from `0` to `None` (`int | None`); `sync_spell_effect_to_affected` guards updated
    from falsy to `is not None`. Bless at `char_level ≤ 7` now emits 2 AffectData entries
    (APPLY_HITROLL + APPLY_SAVES, both modifier=0) matching ROM C — no more RNG drift from a
    bless+tick combination. `_add_opt` helper added for None-safe merge arithmetic;
    `PetSpellEffectSave` updated for correct serialization. 3 integration tests added.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_FINDING_030_BLESS_AFFECT_COUNT.md](SESSION_SUMMARY_2026-06-08_FINDING_030_BLESS_AFFECT_COUNT.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.25 |
| Tests | 5441 passed, 4 skipped, 0 failed |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 9 static + 16 generated-oracle tests |
| Diff-harness position rules | sit/rest/sleep/stand/wake — full ROM graph |
| Diff-harness affect rules | learn_and_cast_armor + detect_evil + fly + bless + char_update_tick (up to 8/run) |
| Diff-harness shop rules | load_weaponsmith + sell_sword + stock_keeper_sword + buy_sword |
| Diff-harness mobprog rules | mob_speech_trigger (SPEECH keyword match) |
| Open findings | (none — FINDING-030 resolved) |

## Next Intended Task

**Shop transaction atomicity** — probe error-exit paths in `do_buy` / `do_sell`:
insufficient funds, item-not-for-sale, keeper-can't-afford scenarios. A scenario
with a player holding exactly 0 silver trying to buy a 300-silver item isolates
the error path. These paths may be candidates for INV entries (cross-file contracts:
wealth deduction should be atomic with inventory transfer, matching ROM C
`src/act_comm.c:do_buy` / `do_sell`). After that: cross-INV affect-tick ordering
(`char_update` affect list traversal order vs ROM C `src/update.c:char_update`).
