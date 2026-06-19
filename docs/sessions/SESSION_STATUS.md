# Session Status — 2026-06-18 — INV-001 debt burndown (THIEF promotion line)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). This session began **INV-001 debt burndown** (prior status's Next
  Intended Task #1): migrating the frozen `_INV001_DEBT` mailbox-bypass sites in
  `tests/test_message_delivery_convention.py` onto the `push_message`
  single-delivery chokepoint, one ROM-confirmed TDD fix per site.
- **Last completed** (this session, commit 8ef44cda, v2.14.120):
  - **INV-001 debt — THIEF promotion line ✅ CLOSED.** The
    "*** You are now a THIEF!! ***" line in
    `mud/commands/thief_skills.py:_steal_failure` (PC caught stealing from a PC)
    was appended straight to `char.messages`, which the connection read loop only
    drains after the player's *next* command — a connected thief saw it late
    (INV-001 SINGLE-DELIVERY wrong-channel class, SPEC-017 shape). Routed through
    the file's existing `_send_to_char_sync` → `push_message` chokepoint,
    mirroring ROM `src/act_obj.c:2259` `send_to_char`. First of 13 frozen
    `_INV001_DEBT` sites burned down (13 → 12); allowlist line deleted (orphan
    check enforces it). Test: `tests/integration/test_steal_thief_flag_delivery.py`
    (connected-socket-once + mailbox-empty; disconnected mailbox fallback).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-18_INV001_DEBT_THIEF_PROMOTION.md](SESSION_SUMMARY_2026-06-18_INV001_DEBT_THIEF_PROMOTION.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.120 |
| Tests | 5812 passed (v2.14.115 baseline) + new `test_steal_thief_flag_delivery.py` (2) + message-delivery guard green |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants — INV-001 debt burndown (12 frozen sites left) |

## Next Intended Task

Continue **INV-001 debt burndown** — 12 frozen `_INV001_DEBT` sites remain in
`tests/test_message_delivery_convention.py`. One clean ROM-confirmed TDD fix per
site, routing through `push_message` + deleting its allowlist line. Candidates,
roughly easiest-first:

1. `mud/net/connection.py:766`/`787` — login enter-game broadcast (ROM
   `src/nanny.c:804`/`810-815` `act` TO_ROOM).
2. `mud/commands/dispatcher.py:1201` — snoop forward (ROM `src/comm.c:1393-1398`
   `write_to_buffer(d->snoop_by)`).
3. `mud/commands/communication.py:29` — `_queue_personal_message`.
4. `mud/commands/magic_items.py:319` — wand TO_VICT.
5. `mud/skills/handlers.py` (4 sites) + `mud/skills/registry.py` cluster — the
   `_deliver_message`+`messages.append` dual-channel (`_deliver_message` is a
   third local copy of the chokepoint; likely closes several at once via refactor).

Other open follow-ups (unchanged): DELETE-002 (do_delete wiznet self-deletion
broadcast), STEAL-015 (steal skill-handler has no is_safe gate), INV-050
bool-retirement (gated on `is_safe_spell`-vs-ROM audit), `mud/entrypoint.py` dead
code. Higher-yield enumeration-independent lever per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md`: the Hypothesis state-machine →
diff_harness widening (Class 11 / Phase C).
