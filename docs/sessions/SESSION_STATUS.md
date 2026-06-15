# Session Status — 2026-06-14 — fight.c do_bash is_safe message-surfacing (FIGHT-070, INV-050)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). Following the "category-error / borrowed-gate / split-helper" lead
  in the `fight.c` offensive-skill **entry gates** — where the *first failing gate
  selects the player-facing message* (SHOUT-005, TELL-009, GIVE-003, RECITE-006,
  FIGHT-067/069/071/074 shape).
- **Last completed**:
  - **FIGHT-070** — `do_bash`'s entry gate now routes through the faithful ROM
    `is_safe()` mirror (`_kill_safety_message`) instead of the **silent** bool
    `mud/combat/safety.py:is_safe`, so it surfaces ROM's context line ("Not in
    this room.", shopkeeper, pet, clan ladder, …) — `src/fight.c:1018-1124` +
    `:2405`. The silent bool's bidirectional divergence (over-blocks `is_ghost`/
    `ActFlag.GAIN`; under-blocks immortal/fighting-back bypass + PC-vs-PC clan
    ladder) and its ~8 remaining callers are filed as **INV-050** (⚠️ PARTIAL).
    One pre-existing test (`test_bash_pc_dodge_penalty_applied`) repaired (gave
    both PCs `clan=1` to clear ROM's PK gate). (v2.14.104)
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_FIGHT070_BASH_IS_SAFE_MESSAGE.md](SESSION_SUMMARY_2026-06-14_FIGHT070_BASH_IS_SAFE_MESSAGE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.104 |
| Tests | +1 FIGHT-070 (`pytest -k bash`: 34 passed; area suite `bash or fight or dirt or trip or kill`: 295 passed / 1 skipped) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | fight.c offensive-skill entry-gate sweep (FIGHT-067/069/071/074/070 closed); INV-050 convergence + cross-file / divergence-class pass continue |

## Next Intended Task

Continue the fight.c offensive-skill entry-gate sweep and the INV-050 convergence.
Open rows in `docs/parity/FIGHT_C_AUDIT.md` and `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`:

- **INV-050** — converge the remaining ~8 silent-bool `is_safe` callers onto the
  faithful message-mirror (`spec_funs.py:1341,1382`, `combat/assist.py:84`,
  `combat/engine.py:671-674` apply_damage re-check, `commands/consider.py:43`,
  `commands/thief_skills.py:132`, `combat.py:do_cast` ~1003), or retire the bool.
  **Caution:** the apply_damage re-check (engine.py:671-674) is the FIGHT-002
  silent-suppression port and is *meant* to be silent mid-combat (ROM
  `damage()`/is_safe at `src/fight.c:725-733` re-checks silently) — confirm against
  ROM C before converting it.
- **FIGHT-068** — do_bash `victim==ch`/position order swap (Python checks
  `victim==ch` before position; ROM checks position first, `src/fight.c:2392` vs
  `:2399`). MINOR ordering.
- **FIGHT-072 / FIGHT-073** — do_dirt `victim==ch`-before-BLIND order swap + BLIND
  `$E` pronoun message. MINOR, act()-render class.

Beyond this verb family, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the
higher-yield open lever remains the **Hypothesis state-machine → diff_harness
widening** (Class 11 / Phase C), enumeration-independent (guardrail 3), where most
recent FINDING-0xx originated.
