# Session Summary — 2026-06-02 — INV-001 WRONG-CHANNEL SWEEP

## Scope

Cross-file invariants pass. After closing ACT_COMM-003 (`stop_follower`) and
GIVE-001 (`do_give` recipient) — both INV-001 wrong-channel cousins — the
recurring shape (a connected PC receiving a line late or twice because code
appended to the `char.messages` mailbox instead of / in addition to the async
`send_to_char`) justified a **repo-wide sweep** of every `*.messages.append`
site in `mud/`. The user authorized "verify all, fix the real ones."

## Method & the false-green trap

ROM delivers via `act()`/`send_to_char` (immediate, single channel). The
canonical Python primitive is `push_message` (async send for a connected PC,
mailbox fallback only for disconnected chars). Two bug shapes:

- **Double-delivery**: `if writer: create_task(send_to_char(...))` **and** an
  unconditional `*.messages.append(...)` → connected PC gets it twice (async now
  + mailbox drain on next prompt, `mud/net/connection.py:2002-2005`).
- **Wrong-channel (late)**: a cross-character `*.messages.append` with no async
  → connected recipient gets it on their next prompt instead of immediately.

**Key discriminators** (a triage subagent over-flagged 31; verified down):
- **Actor-self appends are NOT late** — the actor's own mailbox is drained right
  after their command, so a self-line via mailbox is effectively immediate.
  Excluded: charm "You like yourself even better!", `advancement` practice,
  steal THIEF-flag, `character.send_to_char` (test helper).
- **XOR fallbacks are correct** — `if writer: async … else/continue: append`
  (e.g. `do_yell`, `broadcast_room`/`broadcast_global`). Not bugs.
- Tests using **disconnected** chars false-green against both bug shapes
  (mailbox-only → count 1). Every regression test here uses a **connected** PC
  and asserts the line once on the async channel with `messages == []`.

## Outcomes — 5 fix commits

| Commit | Ver | What |
|--------|-----|------|
| `a181a894` | 2.12.67 | **ACT_COMM-003** — `stop_follower` (follow.py) → `push_message` |
| `a6fb9c03` | 2.12.68 | **GIVE-001** — `do_give` recipient TO_VICT (object + coins) → `push_message` |
| `85271aec` | 2.12.69 | **SAY-005/SHOUT-004/TELL-007/EMOTE-004** — say/shout/tell/emote per-listener loops (double-delivery regression of SAY-004 from the INV-025 PERS rewrites) → `push_message` |
| `5a5bc77c` | 2.12.70 | **ROOM-BCAST-001** — `Room.broadcast` (mob speech/reconnect/link-loss/zap/AI/mob-cmds) double-delivery → `push_message` |
| `c3bb1854` | 2.12.71 | **INV-001 delivery-helper migration** — `group_commands._send_to_char_sync` (+ do_split redundant append + do_follow add/stop_follower legs), `thief_skills._send_to_char_sync` (+ steal-yell loop), `mob_cmds._append_message`, `handlers._to_vict_send` + `_notvict_broadcast` → `push_message` |

All five filed in the INV-001 "Touched by" trail in
`CROSS_FILE_INVARIANTS_TRACKER.md` (no new INV row — wrong-channel cousins of an
existing contract; tracker is at 26, past the ~20 soft cap). ACT_COMM-003 / GIVE-001 / SAY-005-family rows also in their per-file audit docs.

## Tests added

- `test_act_comm003_stop_follower_delivery_channel.py`
- `test_give001_victim_delivery_channel.py`
- `test_inv001_comm_delivery_channel.py` (say/tell/shout/emote)
- `test_inv001_room_broadcast_channel.py`
- `test_inv001_delivery_helpers_channel.py` (5 helpers, parametrized)

Full suite after the last commit: **5351 passed, 4 skipped** (~128s). Each
fix's full-suite run was green with zero fallout, including the high-fan-out
`Room.broadcast` and the core comm commands.

## Update — sweep completed this session (2.12.72)

The "Outstanding" list below was **closed** in two further commits after the
delivery-helper batch:

- **`c3bb1854` (2.12.71)** — delivery-helper migration (group_commands /
  thief_skills `_send_to_char_sync`, `mob_cmds._append_message`,
  `handlers._to_vict_send`/`_notvict_broadcast`).
- **`b36cd5f7` (2.12.72)** — inline migration: `combat/engine._broadcast_pos_change`
  + group-split, `position.do_wake`, `liquids` pour, `say_spell.broadcast_spell_words`,
  `give._append_message` (gold-changer), `music._push_music_message` (XOR), and
  7 inline `handlers.py` spell loops.

**Only `mud/wiznet.py:_wiznet_deliver` remains OPEN** — its reconnect-announce
callers run synchronously outside an event loop, so `push_message`'s
`create_task` raises "no running event loop". Left mailbox-only with a code NOTE;
needs a dedicated fix reconciling the sync callers (4 reconnect tests in
`test_account_auth.py`/`test_wiznet.py` assert mailbox delivery). This is the one
genuinely-tricky site and the right next-session task for the sweep.

Tests added this session: `test_inv001_comm_delivery_channel.py`,
`test_inv001_room_broadcast_channel.py`, `test_inv001_delivery_helpers_channel.py`,
`test_inv001_inline_delivery_channel.py`. Full suite: **5354 passed, 4 skipped**.

---

## Outstanding (ORIGINAL, now closed except wiznet — see Update above)

These were confirmed wrong-channel/double sites; all closed in 2.12.71–2.12.72
except `wiznet` (see Update). Exact locations were:

- `mud/combat/engine.py` ~868-872 (`_broadcast_pos_change` per-listener) and
  ~1218-1222 (combat split coins) — **both-channels doubles**. Note: the
  position-change loop has a `writer is None`-gated TRIG_ACT block right after
  (like `do_say`) — keep `writer` for that, only swap the delivery.
- `mud/commands/position.py` ~453-461 (`do_wake` victim) — both-channels double.
- `mud/commands/liquids.py` ~223 (`do_pour` target_char) — cross-char late.
- `mud/skills/say_spell.py` ~153 (spell incantation room occupants) — cross-char late.
- `mud/wiznet.py` ~254 (wiznet recipient `ch`) — cross-char late.
- `mud/commands/give.py` ~235 (`_append_message`, changer-exchange "tells you")
  — cross-char late (a GIVE-001 cousin the 2.12.68 commit missed).
- `mud/skills/handlers.py` inline spell loops ~2298 (target), ~2387 (chill_touch
  occupants), ~2478/2486 (colour_spray target/occupants), ~2725 (cure_blind),
  ~2836 (cure_disease), ~8026 (trip) — cross-char late. (The shared
  `_to_vict_send`/`_notvict_broadcast` helpers are already fixed; these are the
  spells that hand-roll instead of using them.)
- `mud/music/__init__.py:_push_music_message` ~162-167 — both-channels, but
  **needs care**: it takes an explicit `writer` fallback param and temporarily
  swaps `recipient.connection` (`_send_music_line`), so a naive `push_message`
  swap could break delivery when `connection` is None but a `writer` was passed.
  Check callers before migrating.

Each is one gap = one connected-PC test (`messages == []`) = one commit. Method
proven this session; continue from the top of this list.

## Next Steps

Finish the OPEN sweep sites above (start with the combat/engine doubles — highest
severity). After the sweep, cross-file invariants is still the active pass; the
tracker at 26 rows is past the ~20 soft cap and a consolidation pass (INV-014/015
precedent) is due. Unprobed mob-trigger ordering contracts (bribe/exit/fight/
kill/hpcnt) also remain.

> **Push note:** five fix commits (2.12.67–2.12.71) + handoff-docs commits are on
> local `master`, **NOT yet pushed** to `origin/master` (at `64f0dc1d` / 2.12.66).
> CHANGELOG/version reflect 2.12.71.
