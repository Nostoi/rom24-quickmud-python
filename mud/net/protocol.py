from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from mud.models.character import Character, character_registry
from mud.net.ansi import render_ansi
from mud.net.session import Session

if TYPE_CHECKING:
    from mud.net.connection import TelnetStream


def _line_count(text: str) -> int:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized:
        return 0
    return normalized.count("\n") + (0 if normalized.endswith("\n") else 1)


async def send_to_char(char: Character, message: str | Iterable[str]) -> None:
    """Send message to character's connection with CRLF."""
    writer = getattr(char, "connection", None)
    if writer is None:
        return

    if isinstance(message, (list, tuple)):
        text = "\r\n".join(str(m) for m in message)
    elif isinstance(message, Iterable) and not isinstance(message, (str, bytes)):
        text = "\r\n".join(str(m) for m in message)
    else:
        text = str(message)

    session = getattr(char, "desc", None)
    lines_pref = int(getattr(char, "lines", 0) or 0)
    if (
        isinstance(session, Session)
        and hasattr(writer, "send_text")
        and lines_pref > 0
        and _line_count(text) > lines_pref
    ):
        await session.start_paging(text, lines_pref)
        return

    if hasattr(writer, "send_line"):
        telnet: TelnetStream = writer
        await telnet.send_line(text)
        return

    text = render_ansi(text, getattr(char, "ansi_enabled", True))
    if not text.endswith("\r\n"):
        text += "\r\n"
    writer.write(text.encode())
    await writer.drain()


def broadcast_room(
    room,
    message: str,
    exclude: Character | None = None,
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
    exclude: Character | None = None,
    should_send: Callable[[Character], bool] | None = None,
) -> None:
    for char in list(character_registry):
        if char is exclude:
            continue
        if should_send is not None and not should_send(char):
            continue
        if channel in getattr(char, "muted_channels", set()):
            continue
        writer = getattr(char, "connection", None)
        if writer:
            asyncio.create_task(send_to_char(char, message))
        if hasattr(char, "messages"):
            char.messages.append(message)
