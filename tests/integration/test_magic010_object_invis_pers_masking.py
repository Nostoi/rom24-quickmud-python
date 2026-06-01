"""MAGIC-010 — object-invisibility ``$p`` masks the caster too, not just the room.

ROM ``spell_invisibility`` object branch (``src/magic.c:3620-3641``) sets
``ITEM_INVIS`` via ``affect_to_obj`` (``:3638``) **before** the broadcast
``act("$p fades out of sight.", ch, obj, NULL, TO_ALL)`` (``:3640``).  ``TO_ALL``
includes the caster, and because the object is already invisible at render
time, ``can_see_obj`` (``src/handler.c``) returns FALSE for any char without
detect-invis/holylight — so the **caster** AND every witness see
``"Something fades out of sight."``, not the object's short description.

This is the load-bearing difference from MAGIC-007: at the visible-object sites
the caster always sees a visible target, so a baked caster leg is harmless.
Here the object is genuinely invisible, so *both* legs must render ``$p``
per-recipient through ``can_see_obj``.

The "already invisible" early-out (``src/magic.c:3627`` —
``act("$p is already invisible.", ch, obj, NULL, TO_CHAR)``) lives inside the
same ``IS_OBJ_STAT(obj, ITEM_INVIS)`` branch, so it masks identically: a caster
without detect-invis sees ``"Something is already invisible."``
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, ExtraFlag, Sector
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.skills.handlers import invis


def _lit_room() -> Room:
    room = Room(
        vnum=42820,
        name="Object Invis Lab",
        description="A well-lit room for object-invis PERS masking tests.",
        room_flags=0,
        sector_type=int(Sector.INSIDE),
    )
    room.people = []
    room.contents = []
    return room


def _pc(name: str, room: Room, *, level: int = 30) -> Character:
    char = Character(name=name, level=level, room=room, is_npc=False)
    room.people.append(char)
    char.messages = []
    return char


def _gem() -> Object:
    return Object(instance_id=42, prototype=ObjIndex(vnum=2011, short_descr="mysterious gem"), extra_flags=0)


class TestObjectInvisPERSMasking:
    """The object-invis room+caster line must render per-recipient through
    ``can_see_obj`` — the object is ITEM_INVIS at render time (MAGIC-010)."""

    def test_invis_masks_object_for_caster_and_witness(self) -> None:
        # ROM src/magic.c:3638-3640 — affect_to_obj sets ITEM_INVIS before the
        # TO_ALL act, so neither the caster nor a witness (no detect-invis) can
        # see the object name.
        room = _lit_room()
        caster = _pc("Enchanter", room, level=28)
        witness = _pc("Watcher", room)
        obj = _gem()

        assert invis(caster, obj) is True
        assert obj.extra_flags & int(ExtraFlag.INVIS)

        # Load-bearing: the CASTER leg masks too (distinguishes MAGIC-010 from
        # MAGIC-007, where the baked caster leg is harmless).
        caster_msgs = [str(m) for m in caster.messages]
        assert caster_msgs[-1] == "Something fades out of sight.", (
            f"Object short_descr leaked to the caster (no detect-invis): {caster_msgs}"
        )

        witness_msgs = [str(m) for m in witness.messages]
        assert witness_msgs[-1] == "Something fades out of sight.", (
            f"Object short_descr leaked to a witness (no detect-invis): {witness_msgs}"
        )
        assert not any("mysterious gem" in m.lower() for m in caster_msgs + witness_msgs), (
            f"Object short_descr leaked: caster={caster_msgs} witness={witness_msgs}"
        )

    def test_invis_shows_object_for_detect_invis_witness(self) -> None:
        # A witness WITH detect-invis sees the real short_descr (can_see_obj
        # returns TRUE — src/handler.c can_see_obj / vision.py:291).
        room = _lit_room()
        caster = _pc("Enchanter", room, level=28)
        seer = _pc("Seer", room)
        seer.add_affect(AffectFlag.DETECT_INVIS)
        obj = _gem()

        assert invis(caster, obj) is True

        seer_msgs = [str(m) for m in seer.messages]
        assert seer_msgs[-1] == "Mysterious gem fades out of sight.", (
            f"Expected real short_descr for a detect-invis witness, got: {seer_msgs}"
        )

    def test_already_invisible_masks_object_for_caster(self) -> None:
        # ROM src/magic.c:3627 — act("$p is already invisible.", ch, obj, NULL,
        # TO_CHAR) inside the ITEM_INVIS branch: a caster without detect-invis
        # sees "Something is already invisible."
        room = _lit_room()
        caster = _pc("Enchanter", room, level=28)
        obj = _gem()

        assert invis(caster, obj) is True
        caster.messages.clear()

        assert invis(caster, obj) is False
        caster_msgs = [str(m) for m in caster.messages]
        assert caster_msgs[-1] == "Something is already invisible.", (
            f"Object short_descr leaked on the already-invisible early-out: {caster_msgs}"
        )
