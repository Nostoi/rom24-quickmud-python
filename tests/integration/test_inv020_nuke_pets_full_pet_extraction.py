"""INV-020 (pet leg) — nuke_pets must run the FULL pet extraction cleanup.

ROM ``src/act_comm.c:1640-1654 nuke_pets`` dismisses the charmed pet via::

    stop_follower(pet);
    act("$N slowly fades away.", ...);
    extract_char(pet, TRUE);          // <-- the FULL extract chain

``extract_char(pet, TRUE)`` (``src/handler.c:2103-2180``) is not just a
room/registry unlink — with ``fPull=TRUE`` it runs the same cleanup chain as
any other pull-extract, including:

- ``die_follower(pet)`` (``src/act_comm.c:1658-1680``) — walks ``char_list`` and
  ``stop_follower``s every ``fch->master == pet`` and self-leads every
  ``fch->leader == pet``; and
- the ``reply``/``mprog_target`` dangling-pointer sweep
  (``src/handler.c:2151-2157`` — the INV-047 contract) clearing any
  ``wch->reply == pet``.

The Python port split ``extract_char`` across call sites, and
``mud/combat/death.py:_nuke_pets`` inlined a *partial* pet-extraction
(``stop_follower`` + fade + object drain + ``stop_fighting`` + registry
removal) that OMITS ``die_follower(pet)`` and ``clear_extract_target_refs(pet)``.
So when a pet's owner is extracted, any character following the pet
(``master == pet``) — or holding a ``reply`` pointer at it — is left with a
dangling reference at the now-extracted pet corpse.

Both are ROM-reachable: a third character can be following the pet
(``X.master = pet``), and a character can have ``tell``'d the pet
(``Y.reply = pet``). This pins that the owner-extract path runs the full
``extract_char(pet, TRUE)`` cleanup on the pet leg.
"""

from __future__ import annotations

import pytest

from mud.combat.death import raw_kill
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
    room_registry.pop(9431, None)


def _make_room(vnum: int = 9431) -> Room:
    room = Room(vnum=vnum, name="Death Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _make_npc(name: str, room: Room) -> Character:
    ch = Character(
        name=name,
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
    )
    ch.messages = []
    ch.hit = 100
    ch.max_hit = 100
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def test_nuke_pets_runs_die_follower_on_pet():
    """ROM nuke_pets → extract_char(pet, TRUE) → die_follower(pet).

    A third character following the pet must be detached when the pet is
    dismissed on owner extraction — otherwise its ``master`` dangles at the
    extracted pet corpse.
    """
    room = _make_room()
    owner = _make_npc("owner", room)
    pet = _make_npc("pet", room)
    follower = _make_npc("follower", room)

    pet.master = owner
    owner.pet = pet
    # A charmed mob ordered to be followed / following the pet (ROM-reachable).
    follower.master = pet

    raw_kill(owner)

    assert pet not in character_registry, "nuke_pets must extract the dismissed pet"
    assert follower.master is None, (
        "a character following the pet must be detached when the pet is "
        "dismissed (ROM nuke_pets → extract_char(pet, TRUE) → die_follower(pet) "
        "→ stop_follower(follower)); got a dangling master pointer at the "
        f"extracted pet: {follower.master!r}"
    )


def test_nuke_pets_clears_reply_pointer_at_pet():
    """ROM nuke_pets → extract_char(pet, TRUE) → reply/mprog_target sweep.

    A character whose ``reply`` points at the pet must have it nulled when the
    pet is dismissed (INV-047 contract, un-run on the pet leg).
    """
    room = _make_room()
    owner = _make_npc("owner", room)
    pet = _make_npc("pet", room)
    teller = _make_npc("teller", room)

    pet.master = owner
    owner.pet = pet
    teller.reply = pet

    raw_kill(owner)

    assert pet not in character_registry, "nuke_pets must extract the dismissed pet"
    assert teller.reply is None, (
        "a reply pointer at the pet must be cleared when the pet is dismissed "
        "(ROM extract_char(pet, TRUE) → char_list reply sweep, src/handler.c:"
        f"2151-2157); got a dangling reply at the extracted pet: {teller.reply!r}"
    )
