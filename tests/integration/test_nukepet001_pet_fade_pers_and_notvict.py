"""NUKEPET-001 — nuke_pets' "$N slowly fades away." obeys TO_NOTVICT + PERS + TRIG_ACT.

ROM ``nuke_pets`` (``src/act_comm.c:1641-1655``) dismisses a charmed pet with
``act("$N slowly fades away.", ch, NULL, pet, TO_NOTVICT)``. Three consequences:

  1. ``$N`` renders through ``PERS(pet, to)`` per recipient — an invisible pet
     masks to "someone" for a witness without detect-invis (INV-027).
  2. ``TO_NOTVICT`` excludes BOTH ``ch`` (the owner) and ``pet`` — the owner
     does NOT see the fade line.
  3. No ``MOBtrigger = FALSE`` wrap → NPC recipients with a matching
     ``TRIG_ACT`` mprog receive ``mp_act_trigger`` (INV-025).

The Python ``_nuke_pets`` (``mud/combat/death.py``) baked ``$N``=pet name via
``expand_placeholders`` and delivered with ``pet_room.broadcast(message,
exclude=pet)`` — leaking an invisible pet's name, wrongly showing the owner the
line, and never dispatching TRIG_ACT. ``_nuke_pets`` is the shared chokepoint
for every PC-extract / quit / death pet dismissal, so the fix covers all paths.
"""

from __future__ import annotations

import pytest

import mud.mobprog as mobprog
from mud.combat.death import _nuke_pets
from mud.mobprog import Trigger
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, Position, Sector
from mud.models.mob import MobIndex
from mud.models.room import Room


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name="Kennel", sector_type=int(Sector.CITY))
    room.people = []
    room.contents = []
    return room


def _pet(room: Room, owner: Character, name: str = "Fido") -> Character:
    pet = Character(name=name, is_npc=True, level=5, room=room, position=int(Position.STANDING))
    pet.short_descr = name
    pet.inventory = []
    pet.equipment = {}
    pet.master = owner
    pet.leader = owner
    owner.pet = pet
    room.people.append(pet)
    character_registry.append(pet)
    return pet


def test_invisible_pet_masks_to_someone_for_witness() -> None:
    room = _room(9420)
    owner = Character(name="Owner", level=10, is_npc=False, room=room)
    witness = Character(name="Witness", level=10, is_npc=False, room=room)
    room.people.extend([owner, witness])
    character_registry.extend([owner, witness])
    pet = _pet(room, owner)
    pet.add_affect(AffectFlag.INVISIBLE)
    witness.messages.clear()

    _nuke_pets(owner, room=room)

    # ROM act("$N slowly fades away.", ch, NULL, pet, TO_NOTVICT) → PERS masks.
    assert any(m == "Someone slowly fades away." for m in witness.messages), witness.messages
    assert not any("Fido" in m for m in witness.messages), witness.messages


def test_owner_does_not_see_fade_line() -> None:
    room = _room(9421)
    owner = Character(name="Owner", level=10, is_npc=False, room=room)
    witness = Character(name="Witness", level=10, is_npc=False, room=room)
    room.people.extend([owner, witness])
    character_registry.extend([owner, witness])
    _pet(room, owner)
    owner.messages.clear()
    witness.messages.clear()

    _nuke_pets(owner, room=room)

    # TO_NOTVICT excludes ch (owner): owner must NOT receive the fade line;
    # a sighted bystander sees the pet's name.
    assert not any("fades away" in m for m in owner.messages), owner.messages
    assert any("Fido slowly fades away." == m for m in witness.messages), witness.messages


def test_pet_fade_fires_act_trigger_on_listening_npc(monkeypatch: pytest.MonkeyPatch) -> None:
    room = _room(9422)
    owner = Character(name="Owner", level=10, is_npc=False, room=room)
    room.people.append(owner)
    character_registry.append(owner)
    _pet(room, owner)

    watcher = Character(name="watcher", is_npc=True, level=5, room=room, position=int(Position.STANDING))
    watcher.messages = []
    proto = MobIndex(vnum=9423, short_descr="a watcher", level=5)
    proto.mprogs = [
        type(
            "_P", (), {"trig_type": int(Trigger.ACT), "trig_phrase": "fades", "code": 'mob echo "X"\n', "vnum": 9423}
        )()
    ]
    watcher.prototype = proto
    room.people.append(watcher)
    character_registry.append(watcher)

    fired: list[str] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append(str(argument))
        return original(argument, mob, ch, *args, **kwargs)

    monkeypatch.setattr(mobprog, "mp_act_trigger", _probe)

    _nuke_pets(owner, room=room)

    # ROM act(TO_NOTVICT) with no MOBtrigger wrap → mp_act_trigger fires.
    assert fired, "pet-fade must dispatch mp_act_trigger (ROM act_comm.c:1648, no MOBtrigger wrap)"
    assert any("fades away" in msg for msg in fired), fired
