"""VISION-001 — ``can_see_character`` roomless-target policy (INV-027 prerequisite).

ROM ``can_see`` (``src/handler.c:2618-2664``) only ever dereferences the
**looker's** room (``room_is_dark(ch->in_room)`` and the incog comparison
``ch->in_room != victim->in_room``). It **never** NULL-checks nor dereferences
``victim->in_room``. A roomless *subject* (the new-player passed to
``wiznet("Newbie alert! $N sighted.", ...)`` at ``src/nanny.c:547`` — whose
``in_room`` is NULL at ``CON_GET_NEW_CLASS``) is therefore still visible to a
seeing recipient, and ``$N`` renders the real name.

Python's ``can_see_character`` carried a non-ROM ``target_room is None → False``
bail (``mud/world/vision.py``) that over-masked exactly this case, blocking
INV-027 (ACT-PERS-NAME-MASKING) enforcement. This locks the reconciled policy:
a roomless target is visible per the ROM rules (trust/invis/incog/blind/dark/
invisible/sneak/hide), with the **observer's** room still required (the dark
gate needs it, and ROM's looker always has a room).

The observer is placed in a LIT room (``Sector.INSIDE`` is never dark per
``room_is_dark``) so the only visibility variable under test is the
roomless-target reconciliation — not the dark gate, whose same-room divergence
is tracked separately (VISION-002).
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, Sector
from mud.models.room import Room
from mud.world.vision import can_see_character


def _lit_room() -> Room:
    room = Room(
        vnum=42710,
        name="Lit Hall",
        description="A well-lit hall.",
        room_flags=0,
        sector_type=int(Sector.INSIDE),
    )
    room.people = []
    room.contents = []
    return room


def test_roomed_observer_sees_roomless_visible_target() -> None:
    # ROM can_see (handler.c:2618) never checks victim->in_room — a roomless,
    # non-invisible subject is visible to a seeing looker. This is the newbie
    # alert / wiznet case (nanny.c:547 passes the roomless new player).
    observer = Character(name="Watcher", level=50, room=_lit_room(), is_npc=False)
    roomless = Character(name="Newbie", level=1, room=None, is_npc=False)

    assert can_see_character(observer, roomless) is True


def test_roomed_observer_masks_invisible_roomless_target() -> None:
    # The reconciliation removes only the roomless bail — the rest of ROM
    # can_see still applies. An invisible roomless target stays masked when the
    # observer lacks detect-invis (handler.c:2641-2643).
    observer = Character(name="Watcher", level=50, room=_lit_room(), is_npc=False)
    roomless = Character(name="Phantom", level=50, room=None, is_npc=False)
    roomless.add_affect(AffectFlag.INVISIBLE)

    assert can_see_character(observer, roomless) is False


def test_roomless_observer_still_cannot_see() -> None:
    # ROM's looker always has a room; the dark check dereferences ch->in_room.
    # We keep observer_room is None → False as a defensive Python guard.
    observer = Character(name="Ghost", level=50, room=None, is_npc=False)
    target = Character(name="Target", level=50, room=_lit_room(), is_npc=False)

    assert can_see_character(observer, target) is False
