# Session Status — 2026-06-15 — Eddol bug-trio (INV-051 + DELETE-001 + TRAIN-006)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). This session closed a reported **three-bug cluster** around a
  half-created character (`Eddol`); the structural one, **INV-051**, is now
  ✅ ENFORCED.
- **Last completed**:
  - **INV-051** (2.14.114) — new characters no longer persist a bare level-0 DB
    row at the password phase. Transient in-memory account carries the password
    hash; the single `create_character` INSERT is deferred to creation end
    (mirroring ROM `nanny.c` `save_char_obj`-at-`CON_READ_MOTD`). Both login
    handlers reordered (creation-before-load); new public `mark_character_active`.
  - **DELETE-001** (committed 3ba262c6) — `do_delete` removes the canonical DB
    row (was unlinking a phantom JSON pfile); character no longer loginable
    after `delete`/`delete`.
  - **TRAIN-006** (committed 409dd5d1) — `do_train` normalizes a short/empty
    `perm_stat` to `MAX_STATS`; no more `IndexError` on a malformed row.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-15_EDDOL_BUGTRIO_INV051_DELETE001_TRAIN006.md](SESSION_SUMMARY_2026-06-15_EDDOL_BUGTRIO_INV051_DELETE001_TRAIN006.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.114 |
| Tests | 5807+ passing, 4 skipped (+2 new INV-051 tests; full re-run confirming active-marking edit) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants pass — INV-051 closed; INV-050 message-half done |

## Next Intended Task

The reported Eddol bug-trio is fully closed. Open follow-ups, in priority order:

1. **Eddol data cleanup (needs user confirmation).** INV-051 is forward-only —
   it prevents *new* abandoned rows but does not remove the existing corrupt
   `Eddol` DB row (or any `data/players/eddol.json`). Deleting it is destructive;
   surface to the user and act only on explicit confirmation.
2. **DELETE-002 🔄 OPEN** — `do_delete` lacks ROM's wiznet self-deletion
   broadcast (`src/act_comm.c`). Local divergence, low priority.
3. **STEAL-015 🔄 OPEN** — steal skill-handler `skills/handlers.py:steal` has no
   `is_safe` gate; converge onto `_kill_safety_message`.
4. **INV-050 bool-retirement** — gated on the `is_safe_spell`-vs-ROM audit
   (`safety.py:is_safe_spell` vs `src/fight.c:1126-1218`); message-half is done.
5. **`mud/entrypoint.py`** is dead code (`prompt_account_creation` /
   `prompt_login`, no callers) — candidate for removal in a hygiene pass.

Beyond these, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open
lever remains the **Hypothesis state-machine → diff_harness widening** (Class 11
/ Phase C), enumeration-independent (guardrail 3).
