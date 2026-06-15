# Session Status — 2026-06-14 — is_safe-bool convergence (FIGHT-075 / CONSIDER-002 / CAST-012 / FIGHT-076 / STEAL-003)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). The `fight.c` offensive-skill entry-gate sweep is fully closed; the
  active lever is **INV-050** — converging the silent-bool `is_safe` callers onto
  the faithful message-mirror `_kill_safety_message`. **5 of 7 callers converged;
  ~2 remain.**
- **Last completed**:
  - **FIGHT-075** (2.14.108) — `do_bash` position-gate message renders ROM's `$M` pronoun.
  - **CONSIDER-002** (2.14.109) — `do_consider` surfaces is_safe context line. 2nd caller.
  - **CAST-012** (2.14.110) — `do_cast` `TAR_CHAR_OFFENSIVE` gate surfaces line + override. 3rd caller; 3 tests ROM-corrected.
  - **FIGHT-076** (2.14.111) — `check_assist`: non-clan PC no longer wrongly auto-assists in PvP; surfaces line. 4th caller.
  - **STEAL-003** (2.14.112) — `do_steal` surfaces is_safe line (silent bool returned ""). 5th caller; 4 tests ROM-corrected.
  - **do_kill stale test** — ROM-corrected (pre-existing red test; separate `test(parity)` commit).
  - **STEAL-015 🔄 OPEN** filed — the steal *skill-handler* `skills/handlers.py:steal` has no is_safe at all.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_FIGHT075_CONSIDER002_IS_SAFE_CONVERGENCE.md](SESSION_SUMMARY_2026-06-14_FIGHT075_CONSIDER002_IS_SAFE_CONVERGENCE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.112 |
| Tests | +3 net new + 7 ROM-corrected; steal slice 40 passed; assist/group 93 passed/1 skipped |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | INV-050 is_safe-bool convergence (5/7 callers done: bash/consider/cast/assist/steal; ~2 remain) |

## Next Intended Task

INV-050 is nearly complete — **2 silent-bool callers remain**:

- **`spec_funs.py:1341,1382`** — read the ROM spec-fun call sites first to decide
  whether ROM surfaces the is_safe line there (likely yes for the aggressive
  spec-funs that call is_safe before attacking).
- **`combat/engine.py:671-674`** (apply_damage re-check, FIGHT-002) — ROM
  `src/fight.c:725-733` is **intentionally silent**; confirm and likely leave as-is.

After those, the silent bool `combat.safety.is_safe` can likely be **retired or
made a thin wrapper** over `_kill_safety_message` — eliminating its bidirectional
over/under-block entirely (the INV-050 end goal). Also open: **STEAL-015** (the
steal skill-handler has no is_safe — converge it too).

**Watch for block-set fallout** (the CAST-012 / FIGHT-076 / STEAL-003 lesson):
converging corrects *which* targets block, not just the message. Tests asserting
the silent bool's over/under-block will break and must be ROM-corrected with a ROM
C cite — they were asserting the divergence. ⚠️ PARTIAL in
`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`.

Beyond INV-050, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open
lever remains the **Hypothesis state-machine → diff_harness widening** (Class 11 /
Phase C), enumeration-independent (guardrail 3).
