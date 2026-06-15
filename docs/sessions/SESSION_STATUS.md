# Session Status — 2026-06-14 — do_bash `$M` render + `consider` is_safe convergence (FIGHT-075 / CONSIDER-002)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). The `fight.c` offensive-skill entry-gate sweep is now fully closed;
  the active lever is **INV-050** — converging the silent-bool `is_safe` callers
  onto the faithful message-mirror `_kill_safety_message`.
- **Last completed**:
  - **FIGHT-075** (2.14.108) — `do_bash`'s position-gate message now renders ROM's
    `$M` pronoun via `act_format` ("...let **him** get back up first." for a male
    victim), `src/fight.c:2394` (was the literal "...let **them**..."). Last
    spin-off from the FIGHT-068 order swap; act()-render class.
  - **CONSIDER-002** (2.14.109, INV-050) — `do_consider` now surfaces ROM's
    is_safe context line. ROM runs `is_safe` (which writes its own rejection line
    before returning TRUE) then sends "Don't even think about it." — two lines;
    Python's silent-bool route dropped the first. Converged onto
    `combat._kill_safety_message` (do_bash's FIGHT-070 pattern). **Second INV-050
    caller converged** (do_bash was first).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_FIGHT075_CONSIDER002_IS_SAFE_CONVERGENCE.md](SESSION_SUMMARY_2026-06-14_FIGHT075_CONSIDER002_IS_SAFE_CONVERGENCE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.109 |
| Tests | +2 (FIGHT-075 / CONSIDER-002); consider/safe/kill/murder integration: 152 passed / 1 skipped |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | INV-050 is_safe-bool convergence (do_bash + do_consider done; ~7 callers remain) |

## Next Intended Task

INV-050 is the active lever. Converge the remaining silent-bool
`mud/combat/safety.py:is_safe` callers onto `_kill_safety_message`, reading each
ROM C call-site to decide whether ROM surfaces the is_safe line there:

- **`combat.py:do_cast` (~1003)** and **`combat/assist.py:84`** — ROM surfaces
  the is_safe line (good next conversions, sibling pattern to do_consider).
- **`commands/thief_skills.py:132`**, **`spec_funs.py:1341,1382`** — read the ROM
  call site first.
- **`combat/engine.py:671-674`** (apply_damage re-check, FIGHT-002) — ROM
  `src/fight.c:725-733` is **intentionally silent**; confirm and likely leave as-is.
- End goal: collapse all callers onto the mirror, retire the silent bool (or make
  it a thin wrapper) to eliminate its bidirectional over/under-block. ⚠️ PARTIAL
  in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

Beyond INV-050, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open
lever remains the **Hypothesis state-machine → diff_harness widening** (Class 11 /
Phase C), enumeration-independent (guardrail 3).
