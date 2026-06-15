# Session Status — 2026-06-14 — is_safe-bool convergence (FIGHT-075 / CONSIDER-002 / CAST-012 / FIGHT-076)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). The `fight.c` offensive-skill entry-gate sweep is fully closed; the
  active lever is **INV-050** — converging the silent-bool `is_safe` callers onto
  the faithful message-mirror `_kill_safety_message`.
- **Last completed**:
  - **FIGHT-075** (2.14.108) — `do_bash` position-gate message renders ROM's `$M`
    pronoun (`src/fight.c:2394`).
  - **CONSIDER-002** (2.14.109) — `do_consider` surfaces ROM is_safe's context
    line. **2nd** INV-050 caller.
  - **CAST-012** (2.14.110) — `do_cast` `TAR_CHAR_OFFENSIVE` gate surfaces the
    context line + "Not on that target." **3rd** INV-050 caller; 3 CAST-007 tests
    ROM-corrected for the block-set shift.
  - **FIGHT-076** (2.14.111) — `check_assist` PC autoassist gate converged: a
    non-clan PC group member no longer wrongly auto-assists in PvP and now sees
    the is_safe line. **4th** INV-050 caller.
  - **do_kill stale test** — ROM-corrected `test_kill_blocks_charmed_player_attacking_master`
    (a standing pre-existing red test asserting the charm gate fires before
    is_safe; ROM runs is_safe first). Separate `test(parity)` commit; code was
    already ROM-correct.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_FIGHT075_CONSIDER002_IS_SAFE_CONVERGENCE.md](SESSION_SUMMARY_2026-06-14_FIGHT075_CONSIDER002_IS_SAFE_CONVERGENCE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.111 |
| Tests | +2 net new + 4 ROM-corrected; assist/group slice 93 passed/1 skipped; combat+assist files 50 passed |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | INV-050 is_safe-bool convergence (do_bash + do_consider + do_cast + check_assist done; ~4 callers remain) |

## Next Intended Task

INV-050 is the active lever. Converge the remaining silent-bool
`mud/combat/safety.py:is_safe` callers onto `_kill_safety_message`, reading each
ROM C call-site first:

- **`spec_funs.py:1341,1382`**, **`commands/thief_skills.py:132`** — read the ROM
  call site to confirm ROM surfaces the line there.
- **`combat/engine.py:671-674`** (apply_damage re-check, FIGHT-002) — ROM
  `src/fight.c:725-733` is **intentionally silent**; confirm and likely leave as-is.

**Watch for block-set fallout** (the CAST-012 / FIGHT-076 lesson): converging to
the faithful mirror corrects *which* targets block, not just the message. Existing
tests asserting the silent bool's over/under-block will break and must be
ROM-corrected with a ROM C cite — they were asserting the divergence (the FIGHT-076
run also surfaced a *pre-existing* do_kill test of the same class). End goal:
collapse all callers onto the mirror, retire the silent bool (or make it a thin
wrapper). ⚠️ PARTIAL in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

Beyond INV-050, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open
lever remains the **Hypothesis state-machine → diff_harness widening** (Class 11 /
Phase C), enumeration-independent (guardrail 3).
