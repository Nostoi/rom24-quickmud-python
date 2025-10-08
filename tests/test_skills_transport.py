from mud.models.character import Character
from mud.models.constants import RoomFlag
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _make_room(vnum: int, name: str, description: str = "") -> Room:
    return Room(vnum=vnum, name=name, description=description)


def test_gate_moves_caster_and_pet_with_room_checks() -> None:
    origin = _make_room(1000, "Circle of Warding")
    destination = _make_room(1001, "Hall of Mirrors", "Polished stone reflects endless images.")

    caster = Character(name="Sorcerer", level=45, is_npc=False)
    pet = Character(name="Wolf", level=30, is_npc=True)
    pet.master = caster
    caster.pet = pet

    target = Character(name="Ally", level=40, is_npc=False)
    observer = Character(name="Witness", level=20, is_npc=False)

    origin.add_character(caster)
    origin.add_character(pet)
    origin.add_character(observer)
    destination.add_character(target)

    caster.messages.clear()
    pet.messages.clear()
    observer.messages.clear()
    target.messages.clear()

    result = skill_handlers.gate(caster, target)

    assert result is True
    assert caster.room is destination
    assert pet.room is destination

    assert caster.messages[0] == "You step through a gate and vanish."
    assert caster.messages[1] == "Hall of Mirrors\nPolished stone reflects endless images."

    assert pet.messages[0] == "You step through a gate and vanish."
    assert pet.messages[1] == "Hall of Mirrors\nPolished stone reflects endless images."

    assert observer.messages[-2:] == [
        "Sorcerer steps through a gate and vanishes.",
        "Wolf steps through a gate and vanishes.",
    ]
    assert target.messages[-2:] == [
        "Sorcerer has arrived through a gate.",
        "Wolf has arrived through a gate.",
    ]


def test_gate_rejects_safe_room_or_clan_mismatch() -> None:
    origin = _make_room(2000, "Arcane Junction")
    safe_destination = _make_room(2001, "Sanctum", "A serene, warded chamber.")
    safe_destination.room_flags = int(RoomFlag.ROOM_SAFE)

    caster = Character(name="Invoker", level=35, clan=1, is_npc=False)
    target = Character(name="Rival", level=33, clan=2, is_npc=False)

    origin.add_character(caster)
    safe_destination.add_character(target)

    caster.messages.clear()

    result = skill_handlers.gate(caster, target)

    assert result is False
    assert caster.room is origin
    assert caster.messages[-1] == "You failed."
