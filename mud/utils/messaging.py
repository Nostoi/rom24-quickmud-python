"""Canonical single-delivery message push, mirroring ROM ``write_to_buffer``.

ROM C ``src/comm.c:write_to_buffer`` writes one message to the descriptor's
output buffer — a single delivery channel.  Python cannot do synchronous
socket writes inside the synchronous game tick, so connected characters
receive messages via ``asyncio.create_task(send_to_char(...))``.  The
``char.messages`` mailbox is a fallback for tests and disconnected
characters only.

Appending to BOTH the async send and the mailbox causes duplicate
delivery: the connection read loop in ``mud/net/connection.py`` drains
``char.messages`` after every command, so any combat/magic message would
replay on the next prompt for connected PCs.

See ``docs/divergences/MESSAGE_DELIVERY.md`` for the full design rationale
and ``docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`` (DUPL-002) for the
audit row that consolidated the divergent copies into this module.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


def push_message(character: Character | None, message: str) -> None:
    """Deliver a message to a character, mirroring ROM C write_to_buffer.

    Connected PCs receive via the async socket send exclusively.  Tests and
    disconnected characters fall back to the ``messages`` mailbox.  Never
    both — see module docstring.
    """
    if character is None:
        return
    writer = getattr(character, "connection", None)
    if writer is not None:
        # mirroring ROM src/comm.c:write_to_buffer — single delivery channel.
        # ``asyncio.create_task`` requires a running event loop. Connected
        # recipients are normally serviced under the live server loop (combat
        # ticks, command read loop, async nanny login/reconnect). A few callers
        # run synchronously outside any loop (the sync reconnect-announce path,
        # tests); there is no socket to write to, so fall back to the mailbox
        # rather than raising — keeping the single-delivery contract intact.
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            from mud.net.protocol import send_to_char as _send

            asyncio.create_task(_send(character, str(message)))
            return
    mailbox = getattr(character, "messages", None)
    if isinstance(mailbox, list):
        mailbox.append(str(message))


def send_to_char_buffered(character: Character | None, message: str) -> None:
    """Buffered ROM send_to_char — async send for connected PCs, mailbox fallback.

    Used by code paths (gain_condition, immortal commands, etc.) that in ROM
    call ``send_to_char(buf, ch)`` to write to the descriptor.  Same
    single-delivery contract as ``push_message`` — a connected PC receives
    via the async send only, never also via ``char.messages`` (the
    connection read loop would replay the message).

    The DUPL-001 audit row consolidates the 13 divergent local
    ``_send_to_char`` copies onto this canonical entry point — see
    ``docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md``.
    """
    push_message(character, message)
