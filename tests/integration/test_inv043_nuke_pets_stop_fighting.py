"""INV-043 — NUKE-PETS-STOP-FIGHTING.

ROM ``src/act_comm.c:1640-1655 nuke_pets`` calls ``extract_char(pet, TRUE)``
(``src/handler.c:2103``), which calls ``stop_fighting(pet, TRUE)``
(``src/handler.c:2121``).  That call clears the ``fighting`` pointer on every
character that was fighting the (now-extracted) pet — so no ghost fighting
pointers survive the extraction.

Python ``mud/combat/death.py:_nuke_pets`` performs a manual extraction:
it calls ``stop_follower(pet)`` (clears charm/master/leader), then removes
the pet from the room and ``character_registry``.  Without
``stop_fighting(pet, both=True)`` inside that manual path, any character who
was fighting the pet retains a dangling ``fighting`` pointer to an object no
longer in the registry or any room — a ghost pointer that could cause
``violence_update`` to attack an extracted mob.

Cross-file contract:
  ``mud/combat/death.py:_nuke_pets`` must call ``stop_fighting(pet, TRUE)``
  BEFORE removing the pet from ``character_registry``, mirroring the
  ``stop_fighting`` inside ROM's ``extract_char``.

Both tests are mutation-verified: removing the ``stop_fighting`` call from
``_nuke_pets`` causes the ghost-pointer assertion to fail (RED).
"""

from __future__ import annotations

import pytest

from mud.combat.death import _nuke_pets
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _isolated_registry():
    char_snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(char_snapshot)
    room_registry.pop(9451, None)


def _make_room(vnum: int = 9451) -> Room:
    room = Room(vnum=vnum, name="Test Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _make_pc(name: str, room: Room) -> Character:
    ch = Character(name=name, is_npc=False, level=10, room=room, position=int(Position.STANDING))
    ch.hit = 100
    ch.max_hit = 100
    character_registry.append(ch)
    room.add_character(ch)
    return ch


def _make_npc(name: str, room: Room) -> Character:
    mob = Character(name=name, is_npc=True, level=5, room=room, position=int(Position.STANDING))
    mob.hit = 50
    mob.max_hit = 50
    character_registry.append(mob)
    room.add_character(mob)
    return mob


def test_nuke_pets_clears_ghost_fighting_pointer() -> None:
    """Characters fighting a charmed pet have fighting cleared when pet is nuked.

    ROM: nuke_pets → extract_char(pet, TRUE) → stop_fighting(pet, TRUE)
         clears pet from every other character's fighting pointer.
    Python gap: _nuke_pets manual extraction skipped stop_fighting — any
    character fighting the pet retained a dangling pointer.
    """
    room = _make_room()
    owner = _make_pc("Owner", room)
    pet = _make_npc("Fido", room)
    enemy = _make_pc("Enemy", room)

    # wire up pet → owner
    pet.master = owner
    owner.pet = pet

    # enemy is fighting the pet when the owner dies
    enemy.fighting = pet
    pet.fighting = enemy

    _nuke_pets(owner, room=room)

    # ghost pointer must be cleared — mirroring ROM extract_char's stop_fighting
    assert enemy.fighting is None, (
        "INV-043: enemy.fighting must be None after pet is nuked "
        "(ROM: nuke_pets → extract_char → stop_fighting clears all fighters)"
    )


def test_nuke_pets_clears_pet_fighting_pointer() -> None:
    """The pet's own fighting pointer is also cleared after extraction.

    ROM: stop_fighting(pet, TRUE) with ``fch == ch`` branch clears
    pet's own fighting pointer before extraction.
    """
    room = _make_room()
    owner = _make_pc("Owner", room)
    pet = _make_npc("Fido", room)
    enemy = _make_pc("Enemy", room)

    pet.master = owner
    owner.pet = pet
    pet.fighting = enemy
    enemy.fighting = pet

    _nuke_pets(owner, room=room)

    # pet object still exists in memory; its fighting field should be cleared too
    assert pet.fighting is None, (
        "INV-043: pet.fighting must be None after extraction "
        "(ROM: stop_fighting clears the extracted char's own pointer)"
    )
