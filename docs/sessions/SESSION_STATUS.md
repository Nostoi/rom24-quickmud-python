# Session Status — 2026-06-19 — INV-001 debt burndown COMPLETE

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). **INV-001 SINGLE-DELIVERY debt burndown is now COMPLETE** —
  `_INV001_DEBT` in `tests/test_message_delivery_convention.py` is **empty**.
  The Layer-A delivery scanner now forbids any new unsanctioned
  `*.messages.append` in `mud/` outright (genuine chokepoints allowlisted).
- **Last completed** (this session — final 3 frozen sites, 3 commits):
  - **snoop-forward ✅ CLOSED** (2.14.126, `b85d4864`) — `dispatcher.py`
    `process_command` forwarded the snooped char's logline to the snooper's
    mailbox; a snooper is a connected PC, so it was late. → `push_message`. ROM
    `src/interp.c:491-496`.
  - **"still recovering" registry line ✅ CLOSED** (2.14.127, `5074d7ac`) —
    `registry.py:SkillRegistry.use` wait-state line was mailbox-only (test-only
    path, no double). Migrated to `push_message` for consistency; supersedes the
    INV-001 (d) "deliberately excluded" note.
  - **`_queue_personal_message` ✅ RESOLVED AS LEGITIMATE** (2.14.128,
    `f4bfa17a`) — NOT a bug: it is ROM's deferred tell-buffer
    `add_buf(victim->pcdata->buffer)` analog (linkdead/AFK/note-writing,
    `src/act_comm.c:50/83/93`), intentionally mailbox-only. Reclassified
    `_INV001_DEBT` → `_LEGITIMATE` with a why-comment.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_INV001_DEBT_BURNDOWN_COMPLETE.md](SESSION_SUMMARY_2026-06-19_INV001_DEBT_BURNDOWN_COMPLETE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.128 |
| Tests | 5831 passed, 4 skipped (full suite, 244s) — incl. 2 new connected-socket delivery tests |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants — INV-001 debt burndown COMPLETE (`_INV001_DEBT` empty) |

## Next Intended Task

INV-001 debt burndown is done. Pick up the open follow-ups (unchanged):
**DELETE-002** (do_delete wiznet self-deletion broadcast), **STEAL-015** (steal
skill-handler has no is_safe gate), **INV-050** bool-retirement,
`mud/entrypoint.py` dead code, and the `do_yell` hand-rolled-XOR tidy-up noted in
the INV-001 tracker row (collapse to a single `push_message`). The higher-yield
enumeration-independent lever per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` is the
Hypothesis state-machine → diff_harness widening (Class 11 / Phase C).
