# Message Delivery Audit — Real-Time vs Queue

**Created**: 2026-04-30  
**Status**: 🔄 In Progress  
**Related**: `docs/divergences/MESSAGE_DELIVERY.md`

ROM C delivers messages directly to the socket descriptor via `write_to_buffer()`
during the game tick. The Python port queues messages in `char.messages` and
only drains them when the player types a command — a deviation that freezes
combat output.

## Fix Strategy

| # | Change | Leverage | Status |
|---|--------|----------|--------|
| 1 | `mud/combat/engine.py` — `_push_message` | P0 | ✅ **FIXED** |
| 2 | `mud/models/room.py` — `Room.broadcast()` | P0 (fixes ~12 sites) | ✅ **FIXED** |
| 3 | `mud/game_loop.py` — `_send_to_char`, `_message_room` | P0 | ✅ **FIXED** |
| 4 | `mud/combat/assist.py` — `_send_to_char` | P0 | ✅ **FIXED** |
| 5 | `mud/skills/handlers.py` — `_send_to_char`, `messages.append`, `room.broadcast` | P1 | ✅ **FIXED** |
| 6 | `mud/mob_cmds.py` — `messages.append`, `room.broadcast` | P1 | ✅ **FIXED** |
| 7 | `mud/magic/effects.py` — `_send_effect_message`, `messages.append` | P1 | ✅ **FIXED** |
| 8 | `mud/skills/registry.py` — `messages.append` | P2 | ✅ **FIXED** |

## Auto-Fixed by Room.broadcast() Fix

Once `Room.broadcast()` is updated, these call sites are fixed automatically:

| File | Line(s) | Type |
|------|---------|------|
| `mud/combat/death.py` | 229, 325, 513 | `room.broadcast()` |
| `mud/ai/__init__.py` | 243 | `room.broadcast()` |
| `mud/game_loop.py:_message_room` | 344–355 | `room.broadcast()` |
| `mud/groups/xp.py` | 82 | `room.broadcast()` |
| `mud/spec_funs.py` | 832, 1413, 1431 | `room.broadcast()` |

## Remaining Direct `.messages.append()` Sites

These bypass `Room.broadcast()` and append directly to `char.messages`. Each
needs a parallel `asyncio.create_task(send_to_char(...))` path.

| File | Function | Line(s) |
|------|----------|---------|
| `mud/game_loop.py` | `_send_to_char` | 338–341 |
| `mud/combat/assist.py` | `_send_to_char` | 196–205 |
| `mud/skills/handlers.py` | `_send_to_char` | 461–471 |
| `mud/mob_cmds.py` | various | 336, 412, 893 |
| `mud/magic/effects.py` | `_send_effect_message` | 137–147 |
| `mud/skills/registry.py` | skill improvement | 198, 340, 347 |
