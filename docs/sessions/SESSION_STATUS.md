# Session Status — 2026-06-14 — do_bash / do_dirt entry-gate ordering + `$E` render (FIGHT-068 / FIGHT-072 / FIGHT-073)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). Closing the residual `fight.c` offensive-skill **entry-gate**
  ordering/message follow-ups left from the FIGHT-067/069/070/071/074 closures.
- **Last completed**:
  - **FIGHT-068** (2.14.105) — `do_bash` now checks `position < POS_FIGHTING`
    **before** the `victim == ch` self-target check, matching ROM
    `src/fight.c:2392-2403` (was reversed; self-bash-while-sitting emitted the
    brains-out line instead of the position line).
  - **FIGHT-072** (2.14.106) — `do_dirt` now checks `AFF_BLIND` **before** the
    `victim == ch` self-target check, matching ROM `src/fight.c:2522-2532` (was
    reversed; self-dirt-while-blind emitted "Very funny." instead of the blind
    line). Sibling of FIGHT-068.
  - **FIGHT-073** (2.14.107) — `do_dirt`'s already-blind message now renders ROM's
    `$E` pronoun + wording via `act_format` ("He's already been blinded." for a
    male victim), `src/fight.c:2524` (was the literal "They're already blinded.").
  - Spin-off **FIGHT-075** filed 🔄 OPEN: do_bash's position-gate message still
    uses literal "them" where ROM renders `$M` (`src/fight.c:2394`).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_FIGHT068_072_073_ENTRY_GATE_ORDER.md](SESSION_SUMMARY_2026-06-14_FIGHT068_072_073_ENTRY_GATE_ORDER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.107 |
| Tests | +3 (FIGHT-068/072/073); `bash or dirt or trip or fight or kill or combat` integration: 352 passed / 2 skipped |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | fight.c offensive-skill entry-gate sweep — ordering/message follow-ups closed (FIGHT-068/072/073); FIGHT-075 + INV-050 convergence remain |

## Next Intended Task

The fight.c entry-gate ordering/message follow-ups are exhausted. Open rows:

- **FIGHT-075** — do_bash position-gate message `$M` render (1-line `act_format`
  fix + test; act()-render class, sibling of FIGHT-073).
- **INV-050** — converge the remaining ~8 silent-bool `mud/combat/safety.py:is_safe`
  callers onto the faithful message-mirror `_kill_safety_message` (or retire the
  bool): `spec_funs.py:1341,1382`, `combat/assist.py:84`, `combat/engine.py:671-674`
  (apply_damage re-check — FIGHT-002, *intentionally* silent; confirm against
  `src/fight.c:725-733` before converting), `commands/consider.py:43`,
  `commands/thief_skills.py:132`, `combat.py:do_cast` (~1003). ⚠️ PARTIAL in
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.
- Beyond fight.c, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield
  open lever remains the **Hypothesis state-machine → diff_harness widening**
  (Class 11 / Phase C), enumeration-independent (guardrail 3).
