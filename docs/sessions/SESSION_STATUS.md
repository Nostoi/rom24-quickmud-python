# Session Status — 2026-06-19 — STEAL-015 (steal skill handler is_safe gate)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). This session closed **STEAL-015** — the `steal` *skill handler*
  (`mud/skills/handlers.py:steal`) had no `is_safe` gate, a dual-entry-point
  hazard vs the already-gated `do_steal` command (STEAL-003).
- **Last completed** (this session, 1 commit):
  - **STEAL-015 ✅ FIXED** (2.14.129, `034910eb`) — converged the steal skill
    handler onto `combat._kill_safety_message` (the faithful `is_safe` mirror,
    `src/fight.c:1018-1124`), right after the self-steal check and before the
    kill-stealing check, mirroring ROM `do_steal` L2191→L2194. A skill-path steal
    can no longer rob shopkeepers/healers/pets/safe-room mobs or bypass the PC
    clan PK ladder. The parity-test block-set was re-setup faithfully (rooms +
    clan) so each test still reaches its named ROM mechanic.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_STEAL-015_SKILL_IS_SAFE.md](SESSION_SUMMARY_2026-06-19_STEAL-015_SKILL_IS_SAFE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.129 |
| Tests | Area suites green (121 passed across steal/skills/spec/assist/cast PK suites); full suite not re-run this session |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants — STEAL-015 closed (skill-path is_safe converged onto INV-050 mirror) |

## Next Intended Task

Pick up the remaining open follow-ups (unchanged): **DELETE-002** (do_delete
wiznet self-deletion broadcast, `ACT_COMM_C_AUDIT.md`), **INV-050
bool-retirement** (still GATED on the `is_safe_spell`-vs-ROM standalone audit,
`src/fight.c:1126-1218`), `mud/entrypoint.py` dead code, and the `do_yell`
hand-rolled-XOR tidy-up. The higher-yield enumeration-independent lever per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md` is the Hypothesis state-machine →
diff_harness widening (Class 11 / Phase C).
