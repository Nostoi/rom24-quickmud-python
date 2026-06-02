# Session Status — 2026-06-02 — INV-001 WRONG-CHANNEL SWEEP FULLY COMPLETE (2.12.73)

## Current State

- **Active mode**: cross-file invariants. The INV-001 **wrong-channel sweep** —
  auditing every `*.messages.append` in `mud/` for connected-PC double-delivery
  (async send + mailbox append) or late delivery (cross-character mailbox-only)
  and migrating the real ones to `push_message` (async-XOR-mailbox) — is now
  **100% closed**. The final, deferred wiznet site landed this session (2.12.73).
- **Latest commit — 2.12.73 — INV-001 wiznet** (`611381de`): `_wiznet_deliver`
  routed through a now **loop-aware** `push_message` (`mud/utils/messaging.py`
  probes `asyncio.get_running_loop()` and falls back to the mailbox when no loop
  runs, instead of raising). A connected immortal under the live server loop now
  gets wiznet lines on the immediate async channel (ROM `src/act_wiz.c:184-189`
  `send_to_char`); the sync reconnect-announce callers + tests fall back to the
  mailbox exactly as before. Test
  `tests/integration/test_inv001_wiznet_delivery_channel.py`. **This closes the
  one deferred sweep site — INV-001 wrong-channel sweep is fully done.**
- **Earlier this session — 7 parity fix commits:**
  - **2.12.72 — INV-001 inline migration** (`b36cd5f7`): combat pos-change +
    group-split, `do_wake`, `pour`, `say_spell`, gold-changer line, `music`
    (XOR), 7 inline `handlers.py` spell loops.
  - **2.12.71 — INV-001 delivery-helper migration** (`c3bb1854`): 5 hand-rolled
    helpers (`group_commands`/`thief_skills` `_send_to_char_sync`,
    `mob_cmds._append_message`, `handlers._to_vict_send`/`_notvict_broadcast`).
  - **2.12.70 — ROOM-BCAST-001** (`5a5bc77c`): `Room.broadcast` double-delivery.
  - **2.12.69 — SAY-005/SHOUT-004/TELL-007/EMOTE-004** (`85271aec`):
    say/shout/tell/emote per-listener double-delivery (regression of SAY-004).
  - **2.12.68 — GIVE-001** (`a6fb9c03`): `do_give` recipient TO_VICT.
  - **2.12.67 — ACT_COMM-003** (`a181a894`): `stop_follower`.
- **Sweep status: FULLY COMPLETE.** Every verified double-delivery and
  cross-character-late site is migrated, including the last deliberate exception:
  - **`mud/wiznet.py:_wiznet_deliver` — ✅ CLOSED (2.12.73):** its reconnect-
    announce callers run **synchronously outside an event loop**, so a naive
    `push_message`'s `create_task` raised "no running event loop". Resolved by
    making `push_message` loop-aware (probe `get_running_loop`, fall back to
    mailbox when absent) and routing `_wiznet_deliver` through it. The 4
    mailbox-asserting reconnect tests stay green (they run sync → fallback).
  - Actor-self appends (charm/colour_spray caster, practice, THIEF-flag, the
    `character.send_to_char` test helper) verified NOT late → excluded.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_INV001_WRONGCHANNEL_SWEEP.md](SESSION_SUMMARY_2026-06-02_INV001_WRONGCHANNEL_SWEEP.md).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.73 |
| Tests | **5355 passed, 4 skipped** (`pytest`, ~166s parallel) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 26 enforced; INV-001 wrong-channel sweep added 8 fixes to its trail (no new rows) — tracker past the ~20 soft cap, consolidation due |
| Open gaps | none from the INV-001 sweep (fully closed) |

## Next Intended Task

1. **INV-001 wrong-channel sweep is fully closed** (wiznet landed 2.12.73). No
   remaining sweep work.
2. Weigh INV tracker **consolidation** (26 rows, past the ~20 cap), and probe the
   unaudited **mob-trigger ordering** contracts (bribe/exit/fight/kill/hpcnt) as
   the next cross-file-invariants candidate.

> **Push note:** 2.12.67–2.12.73 (`a181a894`..`611381de`) are on local `master`.
> Earlier this session 2.12.67–2.12.71 (through `17b38b72`) were pushed to
> `origin/master`; **2.12.72 (`b36cd5f7`), 2.12.73 (`611381de`) + this status
> update are NOT yet pushed.** CHANGELOG/version reflect 2.12.73.
