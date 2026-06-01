# Session Status — 2026-06-01 — PERS-masking sweep (MAGIC-010/005/006 + FIGHT-036) (2.12.35)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted) —
  INV-025 / INV-027 PERS-masking sweep.
- **Last completed (this session, 2.12.32 → 2.12.35)** — four single-gap
  TDD commits, each a baked-name → `act_to_room`/`act_format` conversion:
  - **MAGIC-010** (`f50ce63f`, 2.12.32) — object-invis `$p` masks the caster
    too (object is `ITEM_INVIS` at render time per `src/magic.c:3638-3640`);
    folded in the same-branch "already invisible" early-out (`:3627`).
  - **MAGIC-005** (`d70ce1e0`, 2.12.33) — poison-object room legs (weapon
    `:3981` + food/drink `:3946`) mask via `can_see_obj`; caster leg stays
    baked (object stays visible — MAGIC-007 precedent).
  - **MAGIC-006** (`2ed4924c`, 2.12.34) — plague room line `$s skin` gendered
    possessive + `$n` PERS (`src/magic.c:3921`).
  - **FIGHT-036** (`b6a3ad8a`, 2.12.35) — dirt-kick blind room line `$s eyes`
    + `$n` PERS + `{5..{x` colour (`src/fight.c:2614`).
  - **Filed (not fixed):** **FIGHT-037** — dirt-kick TO_VICT/victim-self legs
    drop `{5..{x` colour; Python invents a caster "You kick dirt…" line ROM
    never emits. **MAGIC-011** — poison food/drink caster leg uncapped (missed
    site under the CLOSED ACT-CAP-002 invariant; weapon leg above it *is*
    capped).
  - **Tests**: 4 new integration files (12 tests). Full suite: 5225 passed,
    4 skipped.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_PERS_MASKING_SWEEP_MAGIC010_005_006_FIGHT036.md](SESSION_SUMMARY_2026-06-01_PERS_MASKING_SWEEP_MAGIC010_005_006_FIGHT036.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.35 |
| Tests | full suite: 5225 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | MAGIC-004 + FIGHT-035 (structural); FIGHT-037 + MAGIC-011 (new); MAGIC-009 + CAST-009 + TRAIN-005 remain (MAGIC-005/006/007/008/010 closed) |

## Next Intended Task

Continue the INV-025 / INV-027 PERS-masking pass. Only the **structural** gaps
remain (TO_VICT/TO_NOTVICT splits to rebuild, not token swaps):

1. **MAGIC-004** — `chain_lightning` TO_NOTVICT/TO_VICT split.
2. **FIGHT-035** — `disarm` fail-line double-broadcast + TO_CHAR/TO_VICT/
   TO_NOTVICT structure + `{5..{x` colour.
3. **FIGHT-037** — dirt-kick TO_VICT/victim-self colour + drop the invented
   caster line (smaller; same `handlers.py:dirt_kicking` just touched).

`CAST-009` (failed-cast skill improvement) also remains 🔄 OPEN in
`MAGIC_C_AUDIT.md`.
