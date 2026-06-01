"""MAGIC-007 — object-``$p`` PERS masking for spell room broadcasts.

ROM renders object-subject spell room lines through ``act("$p ...", ch, obj,
NULL, TO_ROOM)``.  ``act()`` expands ``$p`` per recipient via ``can_see_obj``
(``src/handler.c`` ``can_see_obj``), so a recipient who cannot see the object
(blind, dark room, or the object invisible without detect-invis) sees
``"something"`` instead of the object's short description.

The Python port baked ``_object_short_descr(obj)`` into the message once and
broadcast it via ``broadcast_room`` (the module-level ``_act_room`` helper),
leaking the object name to recipients who should not be able to see it.  The
fix routes each visible-object ``$p`` room line through the shared
``act_to_room`` helper (per-recipient ``act_format`` → ``_object_name`` →
``can_see_object`` masking + per-NPC TRIG_ACT dispatch).

``fireproof`` (``spell_fireproof``, ``src/magic.c:2785`` — a single
``act("$p is surrounded by a protective aura.", ch, obj, NULL, TO_ROOM)`` with
no RNG gating the message) is the cleanest deterministic exemplar of the
invariant.  The room is lit (``Sector.INSIDE``) so the visible-render guard is
not masked for the wrong reason (a dark room would mask via ``can_see_obj``
independently of the object name being baked).
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, ExtraFlag, Sector
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.skills.handlers import fireproof


def _lit_room() -> Room:
    room = Room(
        vnum=42810,
        name="Object PERS Lab",
        description="A well-lit room for object-$p PERS masking tests.",
        room_flags=0,
        sector_type=int(Sector.INSIDE),
    )
    room.people = []
    room.contents = []
    return room


def _pc(name: str, room: Room, *, level: int = 30) -> Character:
    char = Character(name=name, level=level, room=room, is_npc=False)
    room.people.append(char)
    return char


def _scroll() -> Object:
    return Object(instance_id=42, prototype=ObjIndex(vnum=2010, short_descr="ancient scroll"), extra_flags=0)


class TestObjectPERSMasking:
    """A spell's object-``$p`` room line must render per-recipient through
    ``can_see_obj`` (INV-027 object variant), not leak the baked short_descr."""

    def test_fireproof_room_line_masks_object_for_blind_witness(self) -> None:
        room = _lit_room()
        caster = _pc("Enchanter", room, level=28)
        witness = _pc("Blindman", room)
        witness.add_affect(AffectFlag.BLIND)
        obj = _scroll()

        assert fireproof(caster, obj) is True
        assert obj.extra_flags & int(ExtraFlag.BURN_PROOF)

        witness_msgs = [str(m) for m in witness.messages]
        assert any("Something is surrounded by a protective aura" in m for m in witness_msgs), (
            f"Expected can_see_obj-masked object line for blind witness, got: {witness_msgs}"
        )
        assert not any("ancient scroll" in m.lower() for m in witness_msgs), (
            f"Object short_descr leaked to a blind witness: {witness_msgs}"
        )

    def test_fireproof_room_line_shows_object_for_sighted_witness(self) -> None:
        room = _lit_room()
        caster = _pc("Enchanter", room, level=28)
        witness = _pc("Watcher", room)
        obj = _scroll()

        assert fireproof(caster, obj) is True

        witness_msgs = [str(m) for m in witness.messages]
        assert any("Ancient scroll is surrounded by a protective aura" in m for m in witness_msgs), (
            f"Expected real object short_descr for sighted witness, got: {witness_msgs}"
        )
