"""INV-027 — ACT-PERS-NAME-MASKING enforcement.

ROM ``PERS(ch, looker)`` (``src/merc.h:2145``) renders an ``act()`` ``$n``/``$N``
substitution as ``"someone"`` when ``can_see(looker, ch)`` is false, while the
line itself is still delivered — ``act_new`` (``src/comm.c:2230-2244``) delivers
to *every* eligible recipient, so visibility is per-recipient **name-masking**,
not line-suppression. The combat path is faithful (``mud/combat/*`` uses
``mud/world/vision.py:pers``), but ``mud/utils/act.py:act_format`` had a local
``_pers`` that returned the name unconditionally, leaking an invisible/unseen
actor's identity to recipients who cannot see them.

This test locks the **per-recipient** half of the contract: when ``act_format``
is given a concrete ``recipient`` (a real viewer), ``$n``/``$N`` honor
``can_see_character``. The **broadcast-once** half (``recipient=None`` fed to
``broadcast_room``) cannot reproduce ROM's per-recipient PERS — that is the
documented MESSAGE_DELIVERY.md architectural divergence — so the gate is
deliberately scoped to ``recipient is not None`` and the second test pins that
boundary.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, Sector
from mud.models.room import Room
from mud.utils.act import act_format


def _lit_room() -> Room:
    # sector INSIDE is never dark (mud/world/vision.py:room_is_dark), so the
    # only visibility variable is the invisible/detect-invis pairing.
    room = Room(vnum=42700, name="Lit Hall", description="A well-lit hall.", room_flags=0, sector_type=int(Sector.INSIDE))
    room.people = []
    room.contents = []
    return room


def _char(name: str, room: Room) -> Character:
    char = Character(name=name, level=50, room=room, is_npc=False)
    room.people.append(char)
    return char


def test_act_pers_masks_invisible_actor_name_for_nonseeing_recipient() -> None:
    # ROM PERS (src/merc.h:2145) → can_see(looker, ch) ? name : "someone".
    room = _lit_room()
    wraith = _char("Wraith", room)
    wraith.add_affect(AffectFlag.INVISIBLE)

    seer = _char("Seer", room)
    seer.add_affect(AffectFlag.DETECT_INVIS)  # can_see → real name
    blindspot = _char("Blindspot", room)  # no detect-invis → "someone"

    seen = act_format("$n grins slyly.", recipient=seer, actor=wraith)
    masked = act_format("$n grins slyly.", recipient=blindspot, actor=wraith)

    assert seen == "Wraith grins slyly."
    # The line is still delivered to the non-seeing witness — only the name is
    # masked (ROM masks, it does not suppress). INV-029: ROM act_new then caps
    # the first letter, so the masked "someone" renders "Someone".
    assert masked == "Someone grins slyly."


def test_act_pers_does_not_mask_broadcast_once_recipient_none() -> None:
    # Boundary guard: with recipient=None there is no concrete viewer to run
    # can_see against (the broadcast-once path fed to broadcast_room — the
    # MESSAGE_DELIVERY.md divergence). The gate must NOT mask here, or every
    # room broadcast would render "someone". ROM reproduces per-recipient PERS
    # only because it formats inside the recipient loop; Python pre-formats once.
    room = _lit_room()
    wraith = _char("Wraith", room)
    wraith.add_affect(AffectFlag.INVISIBLE)

    broadcast = act_format("$n grins slyly.", recipient=None, actor=wraith)

    assert broadcast == "Wraith grins slyly."
