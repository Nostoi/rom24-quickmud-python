# Session Status — 2026-06-08 — Diff-Harness spell rules: detect_evil / fly / bless (2.13.24)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Diff-harness spell rules (2.13.24).** Three new Hypothesis rules added to
    `DeterministicNoRngDiffMachine` (`learn_and_cast_detect_evil`, `learn_and_cast_fly`,
    `learn_and_cast_bless`). All four spell-casting rules (including the existing
    `learn_and_cast_armor`) now guard on `self.current_position == Position.STANDING` —
    `do_cast` requires `POS_FIGHTING` minimum in ROM C. Position guard prevents Hypothesis
    from generating divergent cast-from-rest sequences. `test_generated_no_rng_sequences_match_live_c` passes.
  - **FINDING-030 filed**: `bless` at `char_level ≤ 7` emits 1 Python `AffectData` vs 2 in C
    (falsy guards in `sync_spell_effect_to_affected` skip zero-modifier entries). Fix outlined
    in `FINDINGS.md`; not yet applied — needs its own gap-closer commit.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_DIFF_HARNESS_SPELL_RULES.md](SESSION_SUMMARY_2026-06-08_DIFF_HARNESS_SPELL_RULES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.24 |
| Tests | 5438 passed, 4 skipped, 0 failed |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Diff-harness scenarios | 9 static + 16 generated-oracle tests |
| Diff-harness position rules | sit/rest/sleep/stand/wake — full ROM graph |
| Diff-harness affect rules | learn_and_cast_armor + detect_evil + fly + bless + char_update_tick (up to 8/run) |
| Diff-harness shop rules | load_weaponsmith + sell_sword + stock_keeper_sword + buy_sword |
| Diff-harness mobprog rules | mob_speech_trigger (SPEECH keyword match) |
| Open findings | FINDING-030 (bless RNG divergence at low levels) |

## Next Intended Task

**Close FINDING-030** — bless RNG divergence. Write a failing test first: a scenario that casts bless
at `char_level=5`, calls `__char_update`, then executes something RNG-dependent; the 2-vs-1 AffectData
count causes per-tick drift. Fix: change `SpellEffect.hitroll_mod` / `saving_throw_mod` defaults from
`0` to `None` (`int | None`); update `sync_spell_effect_to_affected` guards from falsy to `is not None`.
Run `gitnexus_impact` on `sync_spell_effect_to_affected` before editing (shared by `Character` +
`MobInstance` paths). After FINDING-030: shop transaction atomicity error-exit paths in `do_buy`/`do_sell`.
