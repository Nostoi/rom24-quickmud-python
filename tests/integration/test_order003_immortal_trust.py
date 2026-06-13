"""ORDER-003 — do_order single-target gate includes ROM's immortal-trust clause.

ROM ``do_order`` (``src/act_comm.c``) refuses a single-target order when::

    if (!IS_AFFECTED(victim, AFF_CHARM)
        || victim->master != ch
        || (IS_IMMORTAL(victim) && victim->trust >= ch->trust))
    {
        send_to_char("Do it yourself!\n\r", ch);
        return;
    }

``IS_IMMORTAL`` is ``get_trust(ch) >= LEVEL_IMMORTAL`` (= 52, ``src/merc.h:149``).
The Python `do_order` checked only the first two clauses, so a charmed immortal
follower whose trust ≥ the orderer's could be ordered where ROM refuses. A normal
charmed mob (`is_immortal()` False) is unaffected and can still be ordered.
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import Character, character_registry
from mud.models.constants import ActFlag, AffectFlag
from mud.models.room import Room
from mud.registry import room_registry
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clean_state():
    rooms = set(room_registry)
    char_ids = {id(c) for c in character_registry}
    yield
    for vnum in list(room_registry):
        if vnum not in rooms:
            room_registry.pop(vnum, None)
    character_registry[:] = [c for c in character_registry if id(c) in char_ids]
    if hasattr(global_registry, "descriptor_list"):
        delattr(global_registry, "descriptor_list")


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="")
    room_registry[vnum] = room
    return room


def _orderer(name: str, room: Room, *, trust: int = 30) -> Character:
    char = create_test_character(name, room.vnum)
    char.is_npc = False
    char.level = trust
    char.trust = trust
    char.wait = 0
    char.messages = []
    return char


def _charmed_follower(name: str, room: Room, master: Character, *, trust: int) -> Character:
    follower = Character(name=name, is_npc=True, level=1, room=room, hit=100, max_hit=100)
    follower.act = int(ActFlag.IS_NPC)
    follower.affected_by = int(AffectFlag.CHARM)
    follower.master = master
    follower.trust = trust
    follower.messages = []
    room.people.append(follower)
    character_registry.append(follower)
    return follower


def test_order_refuses_charmed_immortal_with_trust_ge_orderer(monkeypatch):
    """ROM src/act_comm.c — IS_IMMORTAL(victim) && victim->trust >= ch->trust => 'Do it yourself!'."""
    from mud.commands import group_commands as gc

    room = _room(51100)
    orderer = _orderer("Master", room, trust=30)
    # victim is immortal (trust 52 >= LEVEL_IMMORTAL) and trust >= orderer's 30
    victim = _charmed_follower("angel", room, orderer, trust=52)
    assert victim.is_immortal()

    monkeypatch.setattr(gc, "_send_to_char_sync", lambda *a, **k: None, raising=False)
    import mud.commands.dispatcher as _disp

    monkeypatch.setattr(_disp, "process_command", lambda *a, **k: None)

    result = gc.do_order(orderer, "angel sit")

    assert result == "Do it yourself!", result
    assert orderer.wait == 0, "refused order must not apply WAIT_STATE"


def test_order_allows_normal_charmed_mob(monkeypatch):
    """A normal (non-immortal) charmed follower is still orderable — clause must not over-refuse."""
    from mud.commands import group_commands as gc

    room = _room(51101)
    orderer = _orderer("Master", room, trust=30)
    victim = _charmed_follower("fido", room, orderer, trust=0)
    assert not victim.is_immortal()

    monkeypatch.setattr(gc, "_send_to_char_sync", lambda *a, **k: None, raising=False)
    import mud.commands.dispatcher as _disp

    monkeypatch.setattr(_disp, "process_command", lambda *a, **k: None)

    result = gc.do_order(orderer, "fido sit")

    assert result == "Ok.", result
