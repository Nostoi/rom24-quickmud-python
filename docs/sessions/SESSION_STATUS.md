# Session Status — 2026-06-19 — do_yell → push_message chokepoint refactor

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). This session closed **DELETE-002** then collapsed **`do_yell`**'s
  hand-rolled async-delivery XOR onto the canonical `push_message` chokepoint.
- **Last completed** (this session, 2 parity/refactor commits + handoff docs):
  - **do_yell → push_message** (2.14.131, `8460a368`) — behavior-preserving:
    the per-listener loop's hand-rolled `if writer: create_task(send_to_char)
    else _queue_personal_message` collapsed onto `push_message` (loop-aware
    socket-XOR-mailbox). Removes the last hand-rolled async-delivery loop that
    `DIVERGENCE_CLASS_ROSTER.md` Class 4 cited as a Layer-A static-guard blocker.
    Characterization test added (socket once, mailbox empty); dead `asyncio` /
    `send_to_char` imports dropped.
  - **DELETE-002 ✅ FIXED** (2.14.130, `d6fc8c53`) — `do_delete` now emits ROM's
    two staff `wiznet` lines (request + confirm pass), via the `mud.wiznet.wiznet`
    chokepoint.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_DO_YELL_PUSH_MESSAGE_REFACTOR.md](SESSION_SUMMARY_2026-06-19_DO_YELL_PUSH_MESSAGE_REFACTOR.md)
  (DELETE-002 record:
  [SESSION_SUMMARY_2026-06-19_DELETE-002_WIZNET_BROADCASTS.md](SESSION_SUMMARY_2026-06-19_DELETE-002_WIZNET_BROADCASTS.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.131 |
| Tests | Comm/delivery area suites green (47 + 44 passed this turn); full suite last green at 5834 passed / 4 skipped (DELETE-002 commit) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep |

## Next Intended Task

Remaining open follow-ups: **INV-050 bool-retirement** (GATED on the
`is_safe_spell`-vs-ROM standalone audit, `src/fight.c:1126-1218`) and
`mud/entrypoint.py` dead code. The higher-yield enumeration-independent lever per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md` is the Hypothesis state-machine →
diff_harness widening (Class 11 / Phase C).
