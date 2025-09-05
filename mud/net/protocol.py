from __future__ import annotations
import asyncio
from typing import Iterable, Optional

from mud.models.character import Character, character_registry
from mud.net.ansi import translate_ansi


async def send_to_char(char: Character, message: str | Iterable[str]) -> None:
    """Send message to character's connection with CRLF."""
    writer = getattr(char, "connection", None)
    if writer is None:
        return

    if isinstance(message, (list, tuple)):
        text = "\r\n".join(str(m) for m in message)
    else:
        text = str(message)
    text = translate_ansi(text)

    if not text.endswith("\r\n"):
        text += "\r\n"
    writer.write(text.encode())
    await writer.drain()


def broadcast_room(
    room,
    message: str,
    exclude: Optional[Character] = None,
) -> None:
    for char in list(getattr(room, "people", [])):
        if char is exclude:
            continue
        writer = getattr(char, "connection", None)
        if writer:
            # fire and forget
            asyncio.create_task(send_to_char(char, message))
        if hasattr(char, "messages"):
            char.messages.append(message)


def broadcast_global(
    message: str,
    channel: str,
    exclude: Optional[Character] = None,
) -> None:
    for char in list(character_registry):
        if char is exclude:
            continue
        if channel in getattr(char, "muted_channels", set()):
            continue
        writer = getattr(char, "connection", None)
        if writer:
            asyncio.create_task(send_to_char(char, message))
        if hasattr(char, "messages"):
            char.messages.append(message)
