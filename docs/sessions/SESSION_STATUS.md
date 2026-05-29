# Session Status — 2026-05-29 — spell_combat differential built; FINDING-012/013/014 resolved

## Current State

- **Active mode**: differential-harness-driven parity verification. A new
  `spell_combat` scenario joins `combat_melee_rounds` and `movement_get_drop`; **all
  three converge end-to-end** and `KNOWN_DIVERGENCES` is empty again (zero known
  divergences).
- **Last completed** (this session):
  - **`SHOP-PET-001`** ❌ N/A (master 2.11.17, `8003d33f`) — premise was factually
    wrong (the clone reads the `from_prototype`-resolved instance `dam_type`, not the
    proto's 0). Regression guard added; **`SHOP-PET-002`** filed for the real
    `create_mobile`-vs-clone re-roll divergence.
  - **`FINDING-012`** ✅ (master 2.11.18, `2a3ac8fd`) — `MobInstance.saving_throw`
    added; casting a `saves_spell` spell at an NPC no longer crashes.
  - **`FINDING-013`** ✅ (master 2.11.19, `f1134681`) — `do_cast` returns `""` on
    success (ROM is silent; the spell handler delivers the message).
  - **`FINDING-014`** ✅ resolved as an **architectural divergence** (diff-harness
    `fb7adb7b`) — wait-state is a sync-pulse-loop-vs-async divergence, not a bug; the
    replay now drives commands below the wait gate (mirroring the C shim), and
    `spell_combat` converges.
  - **`spell_combat` scenario + `__learn` harness primitive** built (diff-harness
    `3feb9942`); C diffshim rebuilt, golden committed.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_SPELL_COMBAT_DIFFERENTIAL_FINDINGS_012-014.md](SESSION_SUMMARY_2026-05-29_SPELL_COMBAT_DIFFERENTIAL_FINDINGS_012-014.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.19 |
| Tests | 4954 passed, 4 skipped (full suite, parallel, ~99s) |
| Differential | 9 passed, 0 xfail — 3 scenarios converge end-to-end |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | differential scenarios — zero known divergences |

## Next Intended Task

The differential harness is back at zero known divergences across three scenarios.
The `__learn` primitive makes spell scenarios cheap, so the highest-value next move is
**a new differential scenario** exercising an un-probed path (defensive/affect spells
like `bless`/`armor`/`chill touch`, a multi-mob room, or a group fight) to surface the
next divergence. Alternatively:

1. **`SHOP-PET-002`** (`docs/parity/FIGHT_C_AUDIT.md`) — pet purchase should
   `create_mobile(pIndexData)` (fresh re-roll), not clone the kennel template. A
   concrete RNG-parity gap (breaks existing pet-shop gold assertions — needs care).
2. **`ACT-CAP-001`** — non-combat act() capitalization (wide re-baseline surface).
3. **Optional async project** (`FINDINGS.md` FINDING-014) — enforce wait-state at the
   Python input loop like ROM `comm.c`, removing the handler-level checks.

Also pending (test-infra, not a parity gap): seed RNG in the `test_combat_death.py`
unit death tests to kill the xdist ordering flake.
