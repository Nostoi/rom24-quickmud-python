# Death-on-WS-Disconnect Bug — Triage Notes (2026-05-02)

## Symptom (reported)

When a connected PC dies in WebSocket combat, the player gets disconnected
from the MUD and must log back in.

## ROM expected behavior

`src/handler.c:2103-2187` — `extract_char(ch, FALSE)` for a PC:

- leaves the descriptor open
- sets `position = POS_RESTING`
- clamps `hit / mana / move` to `max(1, current)`
- moves the PC to clan hall (or `ROOM_VNUM_ALTAR = 3054`)
- does **not** call `close_socket`

Python equivalent lives in `mud/combat/death.py::raw_kill` (lines 550-589) and
`_move_player_to_death_room` (line 541).

## What the test proved

`tests/integration/test_pc_death_keeps_connection.py` runs the whole death
path under a real `asyncio.run` loop (production-equivalent — `async_game_loop`
schedules `game_tick` from a running loop, so `asyncio.create_task` inside
`_push_message` works). It exercises:

- `apply_damage(attacker, pc, 500, show=True)` — full message dispatch
- yields the loop several times to drain `create_task` continuations
- asserts the post-death state matches ROM

**All assertions pass:**

| Assertion | Result |
|---|---|
| `pc in character_registry` | PASS |
| `pc.room is not None` (altar) | PASS |
| `pc.position == Position.RESTING` | PASS |
| `pc.hit / mana / move >= 1` | PASS |
| `pc.connection is conn` (not nulled) | PASS |
| `pc.desc is conn` (not nulled) | PASS |
| `conn.close` not called | PASS |
| `bust_a_prompt(pc)` does not raise | PASS |
| `await conn.send_prompt(rendered)` does not raise | PASS |

**Conclusion: the bug is not in `raw_kill`, `_move_player_to_death_room`,
`bust_a_prompt`, or any state mutation in the death path.** The connection
object survives, the prompt renders, the registry is intact, the room is
correctly set to the altar (3054).

## Hypotheses ruled out

- (a) `bust_a_prompt(char)` raises after death — **ruled out**, renders fine.
- (b) `_move_player_to_death_room` doesn't set `victim.room` —
  **ruled out**, `Room.add_character` (`mud/models/room.py:138-153`) does
  `char.room = self` on every call.
- (c) Death path closes / nulls `char.connection` or `char.desc` —
  **ruled out**, no such mutation in `raw_kill` or any callee. The only
  places that null `connection` / `desc` are link-takeover, manual logout
  hooks (`imm_punish`, `imm_admin`), and the connection-loop `finally` block
  (`mud/net/connection.py:1786-1808`) — none of which are reached by the
  death path.
- (e) `Position.RESTING` rejected by `process_command` — irrelevant; the
  read loop calls `bust_a_prompt` and `_read_player_command` *before*
  `process_command`, and `process_command` never breaks the loop on
  position-rejected commands (it only sends a "you can't do that" string).

## Test-environment artifact (not the production bug)

When the test was first run as a sync `def test_...`, it hit
`RuntimeError: no running event loop` in
`mud/combat/engine.py:222` — `asyncio.create_task(_send(character, message))`
inside `_push_message`. **This is a test-only artifact.** Production runs
`game_tick()` from inside `async_game_loop`, where a loop is always running.
The test was rewritten to use `asyncio.run(...)` and now exercises the
production code path correctly.

If anyone ever invokes `apply_damage` from a non-async path (e.g. a sync
admin command, REPL, batch script) and the victim has a `connection`,
`_push_message` would raise — but that's a separate latent bug, not the
reported WS-death-disconnect.

## What to investigate next

The disconnect must originate **outside** `raw_kill`. Candidates, in
descending suspicion:

1. **The WS read loop's outer `except Exception` (line 1766-1768)** is
   catching some unrelated exception during the *iteration after death*. A
   targeted reproducer would:
   - boot the actual `telnet_server` / `ssh_server` against an in-process
     fake WS client
   - drive a real combat death through one game-tick
   - assert the read loop's `while True` loop iterates at least once after
     death without breaking
2. **`_read_player_command` returning `None`** because the WS client
   closed the socket on its end after seeing the death message. If the
   browser frontend (`../quickmud-web-client`) interprets the death
   message as a "session ended" signal and closes the socket, the server
   sees `readline() -> None` and breaks. Worth grepping the frontend for
   any close-on-death logic.
3. **Game-tick exception unrelated to death** that fires *after* the death
   processes. e.g. the corpse spawn, gore object creation, or the wiznet
   broadcast. Run `pytest tests/test_combat_death.py -v` and tail the
   server log during a real death to look for stack traces.
4. **`save_character` in the connection-loop `finally` block** — if the
   loop *does* break for an unrelated reason, the finally calls
   `save_character(char)` which saves the post-death state. This is a
   symptom amplifier, not the cause, but worth confirming the saved
   character file shows altar room + RESTING (which would prove death
   completed cleanly before the disconnect).

## Files inspected

- `mud/combat/death.py` — `raw_kill`, `_move_player_to_death_room`,
  `_clear_spell_effects`, `_restore_race_affects`, `_reset_player_armor`,
  `make_corpse`, `death_cry`
- `mud/combat/engine.py:205-222` — `_push_message` (the create_task call)
- `mud/combat/engine.py:491-617` — `apply_damage` (death dispatch)
- `mud/combat/engine.py:1087-1102` — `_handle_death`
- `mud/models/room.py:138-171` — `add_character` / `remove_character`
  (confirmed both set `char.room` correctly)
- `mud/utils/prompt.py:150-254` — `bust_a_prompt` (no death-relevant raises)
- `mud/net/connection.py:1730-1808` — main game-loop and finally block
- `mud/net/protocol.py:22-91` — `send_to_char`, `broadcast_room` (silent
  on disconnected chars)

## Test added

`tests/integration/test_pc_death_keeps_connection.py` — passes today,
serves as a regression guard if anyone refactors `raw_kill` or
`_move_player_to_death_room` in a way that breaks ROM parity.

## Proposed fix

**No fix to apply yet — the symptom does not reproduce in isolation.**

The next session should add a connection-loop-level integration test that
boots the WS server with a fake client and drives a real death tick, to
catch the actual disconnect site. If that reproduces, the fix will likely
land in `mud/net/connection.py` (extra logging in the outer
`except Exception` branch on line 1766 to surface the actual exception
type, plus a narrower except so non-IO exceptions don't sever the
descriptor).
