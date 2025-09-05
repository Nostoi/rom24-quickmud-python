from __future__ import annotations
import asyncio

from mud.models.character import Character, character_registry
from mud.net.protocol import broadcast_room, broadcast_global, send_to_char


def do_say(char: Character, args: str) -> str:
    if not args:
        return "Say what?"
    message = f"{char.name} says, '{args}'"
    if char.room:
        char.room.broadcast(message, exclude=char)
        broadcast_room(char.room, message, exclude=char)
    return f"You say, '{args}'"


def do_tell(char: Character, args: str) -> str:
    if "tell" in char.banned_channels:
        return "You are banned from tell."
    if not args:
        return "Tell whom what?"
    try:
        target_name, message = args.split(None, 1)
    except ValueError:
        return "Tell whom what?"
    target = next(
        (
            c
            for c in character_registry
            if c.name and c.name.lower() == target_name.lower()
        ),
        None,
    )
    if not target:
        return "They aren't here."
    if "tell" in target.muted_channels:
        return "They aren't listening."
    text = f"{char.name} tells you, '{message}'"
    writer = getattr(target, "connection", None)
    if writer:
        asyncio.create_task(send_to_char(target, text))
    if hasattr(target, "messages"):
        target.messages.append(text)
    return f"You tell {target.name}, '{message}'"


def do_shout(char: Character, args: str) -> str:
    if "shout" in char.banned_channels:
        return "You are banned from shout."
    if not args:
        return "Shout what?"
    message = f"{char.name} shouts, '{args}'"
    broadcast_global(message, channel="shout", exclude=char)
    return f"You shout, '{args}'"
