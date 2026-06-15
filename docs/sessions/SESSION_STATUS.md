# Session Status — 2026-06-14 — is_safe-bool convergence (FIGHT-075 / CONSIDER-002 / CAST-012 / FIGHT-076 / STEAL-003 / spec-funs)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). **INV-050's player-facing message-surfacing divergence is now FULLY
  CLOSED** — every offensive verb that calls is_safe surfaces ROM's context line.
  The remaining INV-050 work (full block-set unification / retiring the silent
  bool) is **gated on an `is_safe_spell`-vs-ROM audit**.
- **Last completed**:
  - **FIGHT-075** (2.14.108) — `do_bash` position message renders ROM's `$M` pronoun.
  - **CONSIDER-002** (2.14.109) — `do_consider` surfaces is_safe context line.
  - **CAST-012** (2.14.110) — `do_cast` `TAR_CHAR_OFFENSIVE` surfaces line + override; 3 tests ROM-corrected.
  - **FIGHT-076** (2.14.111) — `check_assist`: non-clan PC no longer wrongly auto-assists in PvP.
  - **STEAL-003** (2.14.112) — `do_steal` surfaces is_safe line (was ""); 4 tests ROM-corrected.
  - **spec_troll_member/spec_ogre_member** (2.14.113) — converged onto `_is_safe_mirror`
    (corrects ActFlag.GAIN over-block; predicate refactor, message moot — NPC recipient).
  - **do_kill stale test** — ROM-corrected (pre-existing red test; separate `test(parity)` commit).
  - **STEAL-015 🔄 OPEN** filed — the steal *skill-handler* `skills/handlers.py:steal` has no is_safe at all.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_FIGHT075_CONSIDER002_IS_SAFE_CONVERGENCE.md](SESSION_SUMMARY_2026-06-14_FIGHT075_CONSIDER002_IS_SAFE_CONVERGENCE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.113 |
| Tests | +4 net new + 7 ROM-corrected; steal 40 / assist+group 93 / spec-funs 52 — all green |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | INV-050: message-half DONE (6 callers converged); bool-retirement gated on is_safe_spell audit |

## Next Intended Task

INV-050's player-facing half is complete. Two follow-on tasks remain:

1. **`is_safe_spell`-vs-ROM audit (bool-retirement blocker).** `safety.py:is_safe_spell`
   delegates to `is_safe` (line 113), but ROM `is_safe_spell` (`src/fight.c:1126-1218`)
   is a standalone function with extra checks (area handling + the
   `victim->fighting != NULL && !is_same_group` legal-kill clause). Audit it against
   ROM, fix any divergence, THEN the silent bool `safety.py:is_safe` can be retired
   or made a thin wrapper over `_kill_safety_message` — unifying the block-set across
   the last callers (apply_damage re-check stays silent by reading only the bool).
2. **STEAL-015 🔄 OPEN** — converge the steal skill-handler `skills/handlers.py:steal`
   (~7762, no is_safe at all, reachable via the skill system) onto `_kill_safety_message`.

**Watch for block-set fallout** (the CAST-012 / FIGHT-076 / STEAL-003 lesson):
converging corrects *which* targets block, not just the message. Tests asserting the
silent bool's over/under-block must be ROM-corrected with a ROM C cite.

Beyond INV-050, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open
lever remains the **Hypothesis state-machine → diff_harness widening** (Class 11 /
Phase C), enumeration-independent (guardrail 3).
