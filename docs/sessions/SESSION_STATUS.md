# Session Status — 2026-06-18 — INV-001 debt burndown (skills handlers/registry)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). **INV-001 debt burndown** — migrating frozen `_INV001_DEBT`
  mailbox-bypass sites in `tests/test_message_delivery_convention.py` onto the
  `push_message` single-delivery chokepoint, one ROM-confirmed TDD fix per site.
- **Last completed** (this session — 7 sites, 10 → 3 frozen, across 3 commits):
  - **`registry.py` `_deliver_message` consolidation ✅ CLOSED** (2.14.123,
    `ab42f9fa`) — `SkillRegistry.use` failure line + `_check_improve`
    become-better/learn-from-mistakes lines: dual delivery (local socket-only
    helper + `caster.messages.append`) → `push_message`; divergent
    `_deliver_message` helper deleted. ROM `src/magic.c:551`,
    `src/skills.c:951-967`.
  - **`charm_person` caster lines ✅ CLOSED** (2.14.124, `a8a01f75`) — self-charm
    / ROOM_LAW / adoring-eyes (TO_CHAR), all mailbox-only → `_send_to_char`. ROM
    `src/magic.c:1358`/`1371`/`1390`.
  - **`colour_spray` caster line ✅ CLOSED** (2.14.125, `71168a91`) — caster spray
    flavor mailbox-only → `_send_to_char`, matching its already-migrated
    target/room legs. ROM `src/magic.c:1437`.
  - Each fix has a connected-socket integration test (live event loop +
    `_RecordingConn`) that fail-firsts on the bypass; each closed debt allowlist
    line deleted (orphan check enforces).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-18_INV001_DEBT_SKILLS_HANDLERS.md](SESSION_SUMMARY_2026-06-18_INV001_DEBT_SKILLS_HANDLERS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.125 |
| Tests | 5829 passed, 4 skipped (full suite, 444s) — incl. 6 new connected-socket delivery tests |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants — INV-001 debt burndown (3 frozen sites left) |

## Next Intended Task

Continue **INV-001 debt burndown** — **3 frozen `_INV001_DEBT` sites remain**,
the trickier ones (verify before migrating, not mechanical):

1. `mud/commands/dispatcher.py:1201` — snoop-forward. ROM `src/comm.c:1393-1398`
   `write_to_buffer(d->snoop_by)` targets the **snooper's** descriptor, not the
   snooped char — confirm the recipient before migrating.
2. `mud/commands/communication.py:29` — `_queue_personal_message`. Confirm it
   isn't *intentionally* mailbox-only (deferred personal-message/note path)
   before changing.
3. `mud/skills/registry.py:161` — "You are still recovering." getattr+append.
   Deliberately excluded per INV-001 (d): appends then `raise`s (no return
   channel), no production callers, `tests/test_skills.py` asserts the mailbox
   delivery. Likely stays frozen — re-confirm before touching.

Other open follow-ups (unchanged): DELETE-002 (do_delete wiznet self-deletion
broadcast), STEAL-015 (steal skill-handler has no is_safe gate), INV-050
bool-retirement, `mud/entrypoint.py` dead code. Higher-yield
enumeration-independent lever per `docs/parity/DIVERGENCE_CLASS_ROSTER.md`:
Hypothesis state-machine → diff_harness widening (Class 11 / Phase C).
