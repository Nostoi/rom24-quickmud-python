# Session Status — 2026-06-14 — is_safe-bool convergence (FIGHT-075 / CONSIDER-002 / CAST-012)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). The `fight.c` offensive-skill entry-gate sweep is fully closed; the
  active lever is **INV-050** — converging the silent-bool `is_safe` callers onto
  the faithful message-mirror `_kill_safety_message`.
- **Last completed**:
  - **FIGHT-075** (2.14.108) — `do_bash` position-gate message renders ROM's `$M`
    pronoun via `act_format` (`src/fight.c:2394`). Last fight.c entry-gate spin-off.
  - **CONSIDER-002** (2.14.109, INV-050) — `do_consider` surfaces ROM is_safe's
    context line ("...Mota would approve." + "Don't even think about it.").
    **Second** INV-050 caller converged.
  - **CAST-012** (2.14.110, INV-050) — `do_cast`'s `TAR_CHAR_OFFENSIVE` gate
    surfaces ROM is_safe's context line + "Not on that target." (`src/magic.c:398`).
    **Third** INV-050 caller converged. The `is_safe_spell`/`TAR_OBJ_CHAR_OFF`
    branch is silent in ROM, left as-is. Block-set correction fallout: 3 CAST-007
    tests ROM-corrected (clan victim / NPC ROOM_SAFE victim) per AGENTS.md.
    Removed the now-unused bare `is_safe` import from combat.py.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_FIGHT075_CONSIDER002_IS_SAFE_CONVERGENCE.md](SESSION_SUMMARY_2026-06-14_FIGHT075_CONSIDER002_IS_SAFE_CONVERGENCE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.110 |
| Tests | +1 net new test + 3 ROM-corrected; cast/spell/magic/safe/pk integration: 454 passed |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | INV-050 is_safe-bool convergence (do_bash + do_consider + do_cast done; ~5 callers remain) |

## Next Intended Task

INV-050 is the active lever. Converge the remaining silent-bool
`mud/combat/safety.py:is_safe` callers onto `_kill_safety_message`, reading each
ROM C call-site first:

- **`combat/assist.py:84`** — next cleanest; ROM auto-assist / `do_assist`
  surfaces the is_safe line. Good next conversion.
- **`spec_funs.py:1341,1382`**, **`commands/thief_skills.py:132`** — read the ROM
  call site first to confirm ROM surfaces the line there.
- **`combat/engine.py:671-674`** (apply_damage re-check, FIGHT-002) — ROM
  `src/fight.c:725-733` is **intentionally silent**; confirm and likely leave as-is.

**Watch for block-set fallout** (the CAST-012 lesson): converging to the faithful
mirror corrects *which* targets block, not just the message. Existing tests
asserting the silent bool's over/under-block (e.g. KILLER-flag on a non-clan PC
victim) will break and must be ROM-corrected with a ROM C cite — they were
asserting the divergence. End goal: collapse all callers onto the mirror, retire
the silent bool (or make it a thin wrapper). ⚠️ PARTIAL in
`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

Beyond INV-050, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open
lever remains the **Hypothesis state-machine → diff_harness widening** (Class 11 /
Phase C), enumeration-independent (guardrail 3).
