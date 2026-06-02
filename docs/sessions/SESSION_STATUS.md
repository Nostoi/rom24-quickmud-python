# Session Status — 2026-06-02 — INV-001 WRONG-CHANNEL SWEEP (2.12.71, sweep in progress)

## Current State

- **Active mode**: cross-file invariants. This day ran an INV-001 **wrong-channel
  sweep** — auditing every `*.messages.append` in `mud/` for connected-PC
  double-delivery (async send + mailbox append) or late delivery (cross-character
  mailbox-only). ROM delivers via `act()`/`send_to_char` immediately; the
  canonical primitive is `push_message` (async-XOR-mailbox).
- **This session — 5 parity fix commits (local on `master`, NOT yet pushed):**
  - **2.12.71 — INV-001 delivery-helper migration** (`c3bb1854`): 5 hand-rolled
    both-channels helpers → `push_message` (`group_commands._send_to_char_sync`
    + do_split/do_follow legs, `thief_skills._send_to_char_sync` + steal-yell,
    `mob_cmds._append_message`, `handlers._to_vict_send`/`_notvict_broadcast`).
  - **2.12.70 — ROOM-BCAST-001** (`5a5bc77c`): `Room.broadcast` double-delivery
    (mob speech/reconnect/zap/AI) → `push_message`.
  - **2.12.69 — SAY-005/SHOUT-004/TELL-007/EMOTE-004** (`85271aec`):
    say/shout/tell/emote per-listener loops (a double-delivery regression of
    SAY-004 from the INV-025 PERS rewrites) → `push_message`.
  - **2.12.68 — GIVE-001** (`a6fb9c03`): `do_give` recipient TO_VICT → `push_message`.
  - **2.12.67 — ACT_COMM-003** (`a181a894`): `stop_follower` → `push_message`.
- **Sweep status**: bulk fixed (comm cluster, Room.broadcast, GIVE-001, 5
  delivery helpers). **Remaining OPEN sweep sites are filed with exact line
  numbers** in the INV-001 trail + the latest summary's "Outstanding" section:
  `combat/engine.py` (pos-change + split doubles), `position.py` wake, `liquids.py`
  pour, `say_spell.py`, `wiznet.py`, `give.py` changer, `handlers.py` inline
  spell loops, and `music/_push_music_message` (needs care). Actor-self appends
  (charm/practice/THIEF-flag/test-helper) verified NOT late → excluded.

- **Open gaps**: none per-file; the INV-001 sweep remainder above is the active work.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_INV001_WRONGCHANNEL_SWEEP.md](SESSION_SUMMARY_2026-06-02_INV001_WRONGCHANNEL_SWEEP.md)
  (earlier this day: [MOB_TRIGGER_PROBE_GIVE001](SESSION_SUMMARY_2026-06-02_MOB_TRIGGER_PROBE_GIVE001.md),
  [ACT_COMM003_STOP_FOLLOWER_CHANNEL](SESSION_SUMMARY_2026-06-02_ACT_COMM003_STOP_FOLLOWER_CHANNEL.md)).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.71 |
| Tests | **5351 passed, 4 skipped** (`pytest`, ~128s parallel) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 26 enforced; INV-001 wrong-channel sweep added 5 fixes to its trail (no new rows) — tracker past the ~20 soft cap, consolidation due |
| Open gaps | INV-001 sweep remainder (filed with line numbers) |

## Next Intended Task

**Continue the INV-001 wrong-channel sweep** from the "Outstanding" list in the
latest summary — start with the `combat/engine.py` position-change + split
doubles (highest severity), then position/liquids/say_spell/wiznet/give-changer/
handlers-loops (simple `append`→`push_message` swaps), then `music` (needs care
for its connection-juggling `writer` fallback). One gap = one connected-PC test
(`messages == []`) = one commit. After the sweep: weigh INV tracker consolidation
(26 rows, past the ~20 cap) and the unprobed mob-trigger ordering contracts
(bribe/exit/fight/kill/hpcnt).

> **Push note:** 2.12.67–2.12.71 (`a181a894`..`c3bb1854`) + handoff-docs commits
> are on local `master`, **NOT yet pushed** to `origin/master` (at `64f0dc1d` /
> 2.12.66). Push when ready; CHANGELOG/version reflect 2.12.71.
