# Session Status — 2026-06-02 — INV-001 WRONG-CHANNEL SWEEP COMPLETE (2.12.72; wiznet deferred)

## Current State

- **Active mode**: cross-file invariants. Ran a full INV-001 **wrong-channel
  sweep** — audited every `*.messages.append` in `mud/` for connected-PC
  double-delivery (async send + mailbox append) or late delivery (cross-character
  mailbox-only), and migrated the real ones to `push_message` (async-XOR-mailbox).
- **This session — 7 parity fix commits (local on `master`):**
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
- **Sweep status: essentially COMPLETE.** All verified double-delivery and
  cross-character-late sites migrated, EXCEPT one deliberate exception:
  - **`mud/wiznet.py:_wiznet_deliver` — OPEN (needs care):** its reconnect-
    announce callers run **synchronously outside an event loop**, so
    `push_message`'s `create_task` raises "no running event loop". Left
    mailbox-only with a code NOTE; needs a dedicated fix reconciling the sync
    callers (4 reconnect tests assert mailbox delivery). This is the next-session
    task for the sweep.
  - Actor-self appends (charm/colour_spray caster, practice, THIEF-flag, the
    `character.send_to_char` test helper) verified NOT late → excluded.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_INV001_WRONGCHANNEL_SWEEP.md](SESSION_SUMMARY_2026-06-02_INV001_WRONGCHANNEL_SWEEP.md).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.72 |
| Tests | **5354 passed, 4 skipped** (`pytest`, ~129s parallel) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 26 enforced; INV-001 wrong-channel sweep added 7 fixes to its trail (no new rows) — tracker past the ~20 soft cap, consolidation due |
| Open gaps | INV-001 `wiznet` sync-delivery (filed, needs-care) |

## Next Intended Task

1. **Close the wiznet INV-001 site** — reconcile the synchronous reconnect-
   announce callers (they run outside an event loop) so a connected immortal gets
   wiznet lines immediately without breaking the 4 mailbox-asserting reconnect
   tests. The one genuinely-tricky sweep site.
2. After that, the INV-001 wrong-channel sweep is fully closed. Then: weigh INV
   tracker **consolidation** (26 rows, past the ~20 cap), and probe the unaudited
   **mob-trigger ordering** contracts (bribe/exit/fight/kill/hpcnt).

> **Push note:** 2.12.67–2.12.72 (`a181a894`..`b36cd5f7`) + handoff-docs commits
> are on local `master`. Earlier this session 2.12.67–2.12.71 (through `17b38b72`)
> were pushed to `origin/master`; **2.12.72 (`b36cd5f7`) + this status update are
> NOT yet pushed.** CHANGELOG/version reflect 2.12.72.
