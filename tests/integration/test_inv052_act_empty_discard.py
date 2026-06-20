"""INV-052 — ACT-EMPTY-DISCARD.

ROM ``act_new`` (``src/comm.c:2240-2244``) discards NULL **and** zero-length
format strings as its *first* action, before the per-recipient loop::

    /* Discard null and zero-length messages. */
    if (format == NULL || format[0] == '\\0')
        return;

Because the guard precedes the loop, it suppresses **both** the delivery and the
per-NPC ``mp_act_trigger`` (``TRIG_ACT``) dispatch (``src/comm.c:2384-2385``).

The Python port stores ROM-NULL social fields as ``""`` (``data/socials.json``
uses ``""`` everywhere ``area/social.are`` has the ROM ``$`` NULL sentinel — 384
fields across 244 socials, verified by a full ROM↔JSON join). Without the guard,
``act_to_room``/``socials._act_to_char`` render ``act_format("")`` → ``""`` and
``push_message(recipient, "")`` delivers a spurious blank line — and
``act_to_room`` additionally fires ``TRIG_ACT`` on the empty message.

Enforcement points: top of ``mud/utils/act.py:act_to_room`` and top of
``mud/commands/socials.py:_act_to_char`` — both before the loop / push / trigger,
mirroring ``act_new``'s ordering.
"""

from __future__ import annotations

import mud.mobprog as mobprog
from mud.commands.socials import _act_to_char, perform_social
from mud.loaders.social_loader import load_socials
from mud.models.character import Character
from mud.models.room import Room
from mud.models.social import find_social, social_registry
from mud.utils.act import act_to_room


def _room_with(*chars: Character) -> Room:
    room = Room(vnum=4242)
    for c in chars:
        c.room = room
        room.people.append(c)
        c.messages = []
    return room


def test_act_to_room_empty_format_delivers_nothing():
    actor = Character(name="Actor", is_npc=False)
    bystander = Character(name="Bystander", is_npc=False)
    _room_with(actor, bystander)

    act_to_room(bystander.room, "", actor)

    # ROM act_new returns before the loop — no blank line.
    assert bystander.messages == []


def test_act_to_room_empty_format_suppresses_trig_act(monkeypatch):
    actor = Character(name="Actor", is_npc=False)
    npc = Character(name="mob", is_npc=True)
    _room_with(actor, npc)

    fired: list[str] = []
    monkeypatch.setattr(
        mobprog,
        "mp_act_trigger",
        lambda message, *args, **kwargs: fired.append(message),
    )

    act_to_room(npc.room, "", actor)

    # act_new's empty-guard precedes the per-recipient TRIG_ACT dispatch.
    assert fired == []


def test_socials_act_to_char_empty_format_delivers_nothing():
    recipient = Character(name="Recipient", is_npc=False)
    actor = Character(name="Actor", is_npc=False)
    recipient.messages = []

    _act_to_char(recipient, "", actor)

    assert recipient.messages == []


def test_kiss_no_arg_no_blank_line_to_room():
    """End-to-end repro: ``kiss`` with no arg has a ROM-NULL ``others_no_arg``."""
    social_registry.clear()
    load_socials("data/socials.json")
    kiss = find_social("kiss")
    assert kiss is not None
    assert kiss.others_no_arg == ""  # ROM $ NULL → JSON ""

    actor = Character(name="Alice", is_npc=False)
    bystander = Character(name="Bob", is_npc=False)
    _room_with(actor, bystander)

    perform_social(actor, "kiss", "")

    # ROM: act(char_no_arg, TO_CHAR) to Alice; act(NULL, TO_ROOM) → nothing.
    assert actor.messages == ["Isn't there someone you want to kiss?"]
    assert bystander.messages == []
