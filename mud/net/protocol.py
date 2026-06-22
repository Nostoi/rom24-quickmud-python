from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from mud.models.character import Character, character_registry
from mud.net.ansi import render_ansi
from mud.net.session import Session
from mud.utils.act import capitalize_act_line
from mud.utils.messaging import note_tick_delivery

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

    if isinstance(message, list | tuple):
        text = "\r\n".join(str(m) for m in message)
    elif isinstance(message, Iterable) and not isinstance(message, str | bytes):
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
    # ROM delivers room broadcasts via act(..., TO_ROOM); act_new caps the first
    # visible char of every such line (src/comm.c:2376-2379, ACT-CAP-001 / INV-029).
    # broadcast_room is the terminal act(TO_ROOM) delivery boundary — its argument
    # IS the delivered line (one baked string for all recipients, not a
    # per-recipient PERS render) — so cap once here. Idempotent on an
    # already-capital / already-capped line.
    message = capitalize_act_line(message)
    for char in list(getattr(room, "people", [])):
        if char is exclude:
            continue
        writer = getattr(char, "connection", None)
        if writer is not None:
            # INV-001 SINGLE-DELIVERY: a connected PC receives via the async send
            # ONLY. The connection read loop (mud/net/connection.py) drains
            # char.messages after the next command, so anything also queued there
            # replays on the next prompt (duplicate delivery). Mirrors
            # mud/utils/messaging.py:push_message — async XOR mailbox, never both.
            asyncio.create_task(send_to_char(char, message))
            note_tick_delivery(char)  # INV-053: arm tick-prompt (no-op off-tick)
        elif hasattr(char, "messages"):
            char.messages.append(message)


def broadcast_global(
    message: str | None,
    channel: str,
    exclude: Character | None = None,
    should_send: Callable[[Character], bool] | None = None,
    render: Callable[[Character], str] | None = None,
) -> None:
    """Deliver a channel message to every eligible character.

    GOSSIP-001: ROM channel commands render `$n` PER RECIPIENT via
    `act_new(..., d->character, TO_VICT)` — an invisible sender masks to
    "someone" for listeners who can't see them. Pass ``render`` (a
    ``recipient -> str`` callable) to compute each listener's copy with
    per-recipient PERS masking; ``message`` is used only when ``render`` is None
    (legacy callers with no actor to mask).
    """
    for char in list(character_registry):
        if char is exclude:
            continue
        if should_send is not None and not should_send(char):
            continue
        if channel in getattr(char, "muted_channels", set()):
            continue
        per_message = render(char) if render is not None else message
        if per_message is None:
            continue
        writer = getattr(char, "connection", None)
        if writer is not None:
            # INV-001 SINGLE-DELIVERY — async send XOR mailbox (see broadcast_room).
            asyncio.create_task(send_to_char(char, per_message))
            note_tick_delivery(char)  # INV-053: arm tick-prompt (no-op off-tick)
        elif hasattr(char, "messages"):
            char.messages.append(per_message)
