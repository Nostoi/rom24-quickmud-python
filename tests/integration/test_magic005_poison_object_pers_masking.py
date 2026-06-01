"""MAGIC-005 — poison-object room broadcasts mask the object via ``can_see_obj``.

ROM ``spell_poison`` object branch emits the weapon/food poison lines as
``act("$p is coated with deadly venom.", ch, obj, NULL, TO_ALL)``
(``src/magic.c:3981``) and
``act("$p is infused with poisonous vapors.", ch, obj, NULL, TO_ALL)``
(``:3946``).  ``act()`` expands ``$p`` per recipient via ``can_see_obj``
(``src/handler.c``), so a recipient who cannot see the object (blind, dark room,
or the object invisible without detect-invis) sees ``"something"`` instead of
the short description.

Unlike object-invisibility (MAGIC-010), poison does **not** make the object
invisible, so the caster (who targeted a visible object) still sees the real
name — only the per-recipient room leg needs masking.  The Python port baked
``_object_short_descr(obj)`` into the room broadcast via the module-level
``_act_room`` helper (no visibility check), leaking the name; the fix routes
each room leg through the shared ``act_to_room("$p ...", ch, arg1=obj)`` helper.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, ItemType, Sector, WeaponType
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _lit_room() -> Room:
    room = Room(
        vnum=42830,
        name="Poison PERS Lab",
        description="A well-lit room for poison-object $p masking tests.",
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


def _weapon() -> Object:
    proto = ObjIndex(
        vnum=3300,
        short_descr="serrated dagger",
        item_type=int(ItemType.WEAPON),
        value=[int(WeaponType.SWORD), 2, 4, 0, 0],
        new_format=True,
    )
    return Object(instance_id=3300, prototype=proto, value=list(proto.value), extra_flags=0)


def _food() -> Object:
    proto = ObjIndex(
        vnum=4400,
        short_descr="loaf of bread",
        item_type=int(ItemType.FOOD),
        value=[0, 0, 0, 0, 0],
    )
    return Object(instance_id=4400, prototype=proto, value=list(proto.value), extra_flags=0)


class TestPoisonObjectPERSMasking:
    """The poison-object room line must render per-recipient through
    ``can_see_obj`` (INV-027 object variant), not leak the baked short_descr."""

    def test_weapon_room_line_masks_object_for_blind_witness(self) -> None:
        room = _lit_room()
        caster = _pc("Assassin", room, level=32)
        witness = _pc("Blindman", room)
        witness.add_affect(AffectFlag.BLIND)
        weapon = _weapon()

        assert skill_handlers.poison(caster, weapon) is True

        witness_msgs = [str(m) for m in witness.messages]
        assert witness_msgs[-1] == "Something is coated with deadly venom.", (
            f"Object short_descr leaked to a blind witness: {witness_msgs}"
        )
        # The caster targeted a visible object — still sees the real name.
        assert caster.messages[-1] == "Serrated dagger is coated with deadly venom."

    def test_weapon_room_line_shows_object_for_sighted_witness(self) -> None:
        room = _lit_room()
        caster = _pc("Assassin", room, level=32)
        witness = _pc("Watcher", room)
        weapon = _weapon()

        assert skill_handlers.poison(caster, weapon) is True
        assert witness.messages[-1] == "Serrated dagger is coated with deadly venom."

    def test_food_room_line_masks_object_for_blind_witness(self) -> None:
        room = _lit_room()
        caster = _pc("Herbalist", room, level=28)
        witness = _pc("Blindman", room)
        witness.add_affect(AffectFlag.BLIND)
        food = _food()

        assert skill_handlers.poison(caster, food) is True

        witness_msgs = [str(m) for m in witness.messages]
        assert witness_msgs[-1] == "Something is infused with poisonous vapors.", (
            f"Object short_descr leaked to a blind witness: {witness_msgs}"
        )
        assert caster.messages[-1] == "loaf of bread is infused with poisonous vapors."
