# Message Delivery — Python vs ROM C

## ROM C Behavior

In ROM C, messages are delivered **directly to the socket** during the game tick:

```
violence_update()
  → multi_hit()
    → one_hit()
      → damage()
        → dam_message()
          → act()
            → write_to_buffer(desc, buf, 0)   // direct to descriptor output buffer
```

Key characteristics:
- Messages are written inline, synchronously, during `update_handler()`.
- The output buffer is drained later by the same `select()` loop that polls for
  player input.
- Players see combat messages at the prompt, between commands, without typing
  anything.

## Python Architecture

The Python port uses an asyncio event loop:
- `async_game_loop` runs `game_tick()` synchronously, then yields with
  `await asyncio.sleep(tick_interval)`.
- Player connections are handled by separate coroutines that block on
  `await read_command()`.

Because `game_tick()` is synchronous but socket writes must be async, we cannot
call `await send_to_char(...)` directly during the tick.  Instead, we schedule
delivery via `asyncio.create_task(send_to_char(...))` — fire-and-forget tasks
that the event loop executes after `game_tick()` yields.

## Design Decision

**We mirror ROM C's direct-to-socket pattern through fire-and-forget asyncio
tasks.** Characters with a socket connection receive messages immediately (the
coroutine runs when the event loop next yields).  Characters without a
connection (tests, disconnected NPCs) fall back to `char.messages.append()`.

This is implemented in `mud/combat/engine.py:_push_message()`:

```python
def _push_message(character, message):
    # Direct delivery — mirroring ROM C write_to_buffer(desc, buf, 0).
    # Connected PCs receive messages exclusively via the async send;
    # the mailbox is a fallback only when no connection is attached.
    writer = getattr(character, "connection", None)
    if writer is not None:
        asyncio.create_task(send_to_char(character, message))
        return
    # Queue fallback for tests and disconnected characters.
    mailbox = getattr(character, "messages", None)
    if isinstance(mailbox, list):
        mailbox.append(message)
```

**Important:** an earlier revision appended to `char.messages`
unconditionally (no `return` after the async dispatch), which combined
with the unconditional drain in `mud/net/connection.py` to deliver
every combat message TWICE to connected players — once via the async
task during the tick, once via the read-loop drain on the next
command. The duplicate "You have been KILLED!!" symptom on PC death
in WebSocket sessions traces to that bug. The contract is now: one
delivery channel per character, never both. Tests that need to
inspect the mailbox must construct the character without a
`connection` attribute (the standard test pattern).

Room broadcasts use `mud/net/protocol.py:broadcast_room()` (same pattern).

## Why Not Pure Queue?

An earlier implementation queued all combat messages into `char.messages` and
only drained them when the player typed a command (in the connection handler
loop).  This caused a gameplay-breaking bug:

1. Player types `kill kobold` — attack message sent.
2. Game loop advances combat — damage messages queued, never shown.
3. Player waits at prompt — sees nothing.
4. Eventually types a command — suddenly sees all queued combat messages at once.

This deviates from ROM C, where combat messages arrive at the prompt in
real-time, preserving the feel of the original game.

## Related Files

| File | Role |
|------|------|
| `mud/combat/engine.py` | `_push_message()` — direct delivery for combat messages |
| `mud/net/protocol.py` | `broadcast_room()` — direct delivery for room occupants |
| `mud/net/connection.py` | Connection loop — drains `char.messages` queue for command-driven messages |
| `src/fight.c` | ROM C reference — `write_to_buffer()` pattern |
