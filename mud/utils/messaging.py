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


# --- INV-053 PROMPT-AFTER-TICK-OUTPUT ----------------------------------------
# ROM `game_loop_unix` runs one output phase per pulse, AFTER `update_handler()`:
# every descriptor with buffered output (`d->outtop > 0`) gets `process_output`,
# which appends a fresh `bust_a_prompt` (src/comm.c:868-883, 1376-1377). So a
# tick-generated message (combat, a spell from a mob/mobprog, a poison affect)
# is followed by a refreshed prompt within the same pulse. The Python port pushes
# the message but rendered no trailing prompt — the HP/mana line stayed frozen
# until the player's next command. We mirror ROM by marking every PC that
# receives output *during the synchronous tick* and emitting one prompt per
# marked descriptor afterwards (`mud.net.connection.schedule_tick_prompts`).
#
# Gated to tick context: because `game_tick()` is synchronous and the event loop
# is single-threaded, anything delivered while `_in_tick` is True is exactly the
# pulse's output — command-context deliveries (socials, command responses) leave
# `_in_tick` False and never arm a prompt, so they don't double-prompt against
# the per-connection loop's own top-of-loop prompt (ROM's `fcommand` case).
_in_tick: bool = False
_prompt_dirty: list[Character] = []


def begin_tick_output() -> None:
    """Mark the start of a synchronous game-tick output window (INV-053)."""
    global _in_tick
    _in_tick = True


def end_tick_output() -> None:
    """Mark the end of the game-tick output window (INV-053)."""
    global _in_tick
    _in_tick = False


def note_tick_delivery(character: Character | None) -> None:
    """Record a connected PC that received output during the current pulse.

    No-op outside tick context (``_in_tick`` False) or for disconnected
    characters. Identity-deduped (a PC hit by several combat lines this pulse
    still gets exactly one prompt, mirroring ROM's single ``process_output``).
    """
    if not _in_tick or character is None:
        return
    if getattr(character, "connection", None) is None:
        return
    for existing in _prompt_dirty:
        if existing is character:
            return
    _prompt_dirty.append(character)


def drain_prompt_dirty() -> list[Character]:
    """Return and clear the PCs marked for a fresh prompt this pulse (INV-053)."""
    global _prompt_dirty
    drained = _prompt_dirty
    _prompt_dirty = []
    return drained


def reset_prompt_dirty() -> None:
    """Reset tick-output prompt state — test hygiene (global mutable singleton)."""
    global _in_tick, _prompt_dirty
    _in_tick = False
    _prompt_dirty = []


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
            # INV-053: arm a fresh prompt for tick-context output (no-op outside).
            note_tick_delivery(character)
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
