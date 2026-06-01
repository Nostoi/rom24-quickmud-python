# Session Status — 2026-06-01 — INV-025/INV-027 structural queue drain (MAGIC-004/011 + FIGHT-035/037/038) (2.12.40)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted) —
  INV-025 / INV-027 PERS-masking sweep. **The structural queue is now drained.**
- **Last completed (this session, 2.12.35 → 2.12.40)** — five single-gap TDD
  commits:
  - **MAGIC-011** (`f7f177df`, 2.12.36) — poison food/drink caster line
    capitalized (`act(TO_ALL)` caps every recipient; missed ACT-CAP-002 leg).
  - **FIGHT-037** (`63e58ab4`, 2.12.37) — dirt-kick victim legs colour/`$n` PERS;
    invented caster "You kick dirt…" line removed. Completes the `do_dirt` surface.
  - **FIGHT-035** (`6eb93eda`, 2.12.38) — disarm TO_CHAR/TO_VICT/TO_NOTVICT split
    + colour + `$n`/`$N`/`$S` PERS; fixed the TO_NOTVICT double-broadcast.
  - **FIGHT-038** (`01fa68ea`, 2.12.39) — NOREMOVE disarm credits skill
    improvement TRUE (ROM `do_disarm:3206`); surfaced + filed closing FIGHT-035.
  - **MAGIC-004** (`04f118e8`, 2.12.40) — chain_lightning `$n`/`$N` per-recipient
    PERS masking (lowercase mid-sentence "someone").
  - **15 new integration tests across 5 files.** Full suite: 5240 passed, 4 skipped.
  - **3 of 5 audit rows had wrong ROM refs/scope** — all corrected (see summary).

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_PERS_STRUCTURAL_QUEUE_MAGIC004_011_FIGHT035_037_038.md](SESSION_SUMMARY_2026-06-01_PERS_STRUCTURAL_QUEUE_MAGIC004_011_FIGHT035_037_038.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.40 |
| Tests | full suite: 5240 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | CAST-009 + TRAIN-005 remain (all INV-025/027 structural gaps now CLOSED) |

## Next Intended Task

The INV-025 / INV-027 PERS-masking structural queue is drained. Next:

1. **CAST-009** — failed-cast skill improvement (🔄 OPEN in `MAGIC_C_AUDIT.md`).
2. **TRAIN-005** — remains open per prior status.
3. Open a fresh cross-file-invariants candidate area (affect ticks, position
   transitions, mob script triggers, group/follower chain) per the AGENTS.md
   probe-then-scope method.

> **Distrust remaining audit-row ROM refs:** 3 of 5 rows closed this session had
> materially wrong ROM line numbers / over-stated scope, caught only by reading
> `src/`. Re-verify any ⚠️/❌ row against the C source before relying on it.

> **Before pushing:** commits `f7f177df..04f118e8` are local on `master`, not
> pushed. Refresh `README.md` Version/badge/test-count (→ 2.12.40 / 5240) and
> confirm README + AGENTS + this file agree, per AGENTS.md Repo Hygiene.
