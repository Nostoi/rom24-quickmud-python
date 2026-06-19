# Session Status — 2026-06-18 — INV-001 debt burndown (3 sites)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). **INV-001 debt burndown** — migrating the frozen `_INV001_DEBT`
  mailbox-bypass sites in `tests/test_message_delivery_convention.py` onto the
  `push_message` single-delivery chokepoint, one ROM-confirmed TDD fix per site.
- **Last completed** (this session — three sites, 13 → 10 frozen):
  - **THIEF promotion line ✅ CLOSED** (2.14.120, commit 8ef44cda) —
    `thief_skills.py:_steal_failure` "*** You are now a THIEF!! ***" →
    `_send_to_char_sync`→`push_message` (ROM `src/act_obj.c:2259`).
  - **Login enter-game broadcast ✅ CLOSED** (2.14.121, commit 22865df8) —
    `connection.py:broadcast_entry_to_room` "$n has entered the game." (char +
    pet) → `push_message`, per-recipient loop kept (ROM `src/nanny.c:804`/`813-814`
    `act(..., TO_ROOM)` masks `$n` via `can_see`).
  - **Wand zap TO_VICT ✅ CLOSED** (2.14.122, commit 53226411) —
    `magic_items.py:do_zap` "$n zaps you with $p." → `push_message` (ROM
    `src/act_obj.c:2125` `act(..., TO_VICT)`); fires before the success roll, so
    deterministic.
  - Each fix has a connected-socket integration test (live event loop +
    `_RecordingConn`) that fail-firsts on the mailbox bypass; each debt allowlist
    line deleted (orphan check enforces).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-18_INV001_DEBT_BURNDOWN.md](SESSION_SUMMARY_2026-06-18_INV001_DEBT_BURNDOWN.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.122 |
| Tests | 5812 passed (v2.14.115 baseline) + 4 new connected-socket delivery tests + message-delivery guard green |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants — INV-001 debt burndown (10 frozen sites left) |

## Next Intended Task

Continue **INV-001 debt burndown** — 10 frozen `_INV001_DEBT` sites remain in
`tests/test_message_delivery_convention.py`. One clean ROM-confirmed TDD fix per
site, routing through `push_message` + deleting its allowlist line. Candidates,
roughly easiest-first:

1. `mud/commands/dispatcher.py:1201` — snoop forward (ROM `src/comm.c:1393-1398`
   `write_to_buffer(d->snoop_by)`). Targets the **snooper's** descriptor, not the
   snooped char — verify the recipient before migrating.
2. `mud/commands/communication.py:29` — `_queue_personal_message` (a deferred
   mailbox path — confirm it isn't intentionally mailbox-only before changing).
3. **Highest-yield**: `mud/skills/handlers.py` (4 sites) + `mud/skills/registry.py`
   (4 sites) — the `_deliver_message`+`messages.append` dual-channel.
   `_deliver_message` is a third local copy of the chokepoint (DUPL-style);
   migrating it likely closes several sites in one refactor.

Other open follow-ups (unchanged): DELETE-002 (do_delete wiznet self-deletion
broadcast), STEAL-015 (steal skill-handler has no is_safe gate), INV-050
bool-retirement (gated on `is_safe_spell`-vs-ROM audit), `mud/entrypoint.py` dead
code. Higher-yield enumeration-independent lever per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md`: Hypothesis state-machine → diff_harness
widening (Class 11 / Phase C).
