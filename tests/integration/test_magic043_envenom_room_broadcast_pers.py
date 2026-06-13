"""MAGIC-043 — envenom's "coats $p with deadly venom" room broadcast uses $n/$p PERS.

ROM `do_envenom` (`src/act_obj.c:946`): `act("$n coats $p with deadly venom.", ch,
obj, NULL, TO_ROOM)` — `$n` = PERS(caster), `$p` = the object. The Python passed a
pre-baked `f"{_character_name(caster)} coats {short_descr} …"` string to
`_act_room`, so it never did per-recipient PERS. An NPC caster distinguishes the
two: `_character_name` returns the keyword, ROM `$n` renders the short_descr.
"""

from __future__ import annotations

from types import SimpleNamespace

from mud.models.character import Character
from mud.models.constants import ItemType, Position
from mud.models.object import Object
from mud.models.room import Room
from mud.skills.handlers import envenom
from mud.utils import rng_mm


def test_magic043_envenom_weapon_room_broadcast_uses_pers(monkeypatch):
    room = Room(vnum=99217, name="Alchemy Lab")
    proto = SimpleNamespace(name="serrated dagger", short_descr=None, item_type=None, extra_flags=0)
    weapon = Object(instance_id=None, prototype=proto)
    weapon.short_descr = "a serrated dagger"
    weapon.item_type = int(ItemType.WEAPON)
    weapon.value = [0, 0, 0, 0]
    weapon.affected = []

    caster = Character(
        name="alchemist", is_npc=True, short_descr="a wandering alchemist", level=30, position=int(Position.STANDING)
    )
    caster.skills = {"envenom": 90}
    caster.inventory = [weapon]
    room.add_character(caster)
    caster.messages = []

    witness = Character(name="Bystander", is_npc=False, position=int(Position.STANDING))
    room.add_character(witness)
    witness.messages = []

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)  # success roll

    result = envenom(caster, item_name="dagger")
    assert result["success"] is True, result
    # ROM $n = PERS(caster) = NPC short_descr (cap); $p = the weapon.
    assert any("A wandering alchemist coats a serrated dagger with deadly venom." in m for m in witness.messages), (
        witness.messages
    )
