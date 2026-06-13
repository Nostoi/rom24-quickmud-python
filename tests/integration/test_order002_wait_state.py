"""ORDER-002 — do_order applies WAIT_STATE(ch, PULSE_VIOLENCE) when an order lands.

ROM ``do_order`` (``src/act_comm.c``) ends with::

    if (found)
    {
        WAIT_STATE (ch, PULSE_VIOLENCE);
        send_to_char ("Ok.\n\r", ch);
    }
    else
        send_to_char ("You have no followers here.\n\r", ch);

``PULSE_VIOLENCE`` is ``3 * PULSE_PER_SECOND`` = 12 (``src/merc.h:155-156``). Both
the single-target and ``order all`` paths share that one trailing WAIT_STATE. The
Python ``mud/commands/group_commands.py:do_order`` carried a
``# Note: WAIT_STATE not implemented yet`` stub and returned ``"Ok."`` without any
wait — the orderer could spam orders with no lag. (The audit doc's "✅ WAIT_STATE
(12 ticks)" rows were a stale false-✅.)
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.config import get_pulse_violence
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


def _charmed_follower(name: str, room: Room, master: Character) -> Character:
    follower = Character(name=name, is_npc=True, level=1, room=room, hit=100, max_hit=100)
    follower.act = int(ActFlag.IS_NPC)
    follower.affected_by = int(AffectFlag.CHARM)
    follower.master = master
    follower.trust = 0
    follower.messages = []
    room.people.append(follower)
    character_registry.append(follower)
    return follower


def _orderer(name: str, room: Room) -> Character:
    char = create_test_character(name, room.vnum)
    char.is_npc = False
    char.level = 30
    char.trust = 30
    char.wait = 0
    char.messages = []
    return char


def test_do_order_single_target_applies_wait_state(monkeypatch):
    """ROM src/act_comm.c — WAIT_STATE(ch, PULSE_VIOLENCE) after a landed single-target order."""
    from mud.commands import group_commands as gc

    room = _room(51000)
    orderer = _orderer("Master", room)
    _charmed_follower("rex", room, orderer)

    monkeypatch.setattr(gc, "_send_to_char_sync", lambda *a, **k: None, raising=False)
    import mud.commands.dispatcher as _disp

    monkeypatch.setattr(_disp, "process_command", lambda *a, **k: None)

    result = gc.do_order(orderer, "rex sit")

    assert result == "Ok.", result
    assert orderer.wait == get_pulse_violence() == 12, f"expected wait 12, got {orderer.wait}"


def test_do_order_all_applies_wait_state(monkeypatch):
    """ROM src/act_comm.c — the shared if(found) WAIT_STATE also fires for `order all`."""
    from mud.commands import group_commands as gc

    room = _room(51001)
    orderer = _orderer("Master", room)
    _charmed_follower("rex", room, orderer)
    _charmed_follower("fido", room, orderer)

    monkeypatch.setattr(gc, "_send_to_char_sync", lambda *a, **k: None, raising=False)
    import mud.commands.dispatcher as _disp

    monkeypatch.setattr(_disp, "process_command", lambda *a, **k: None)

    result = gc.do_order(orderer, "all sit")

    assert result == "Ok.", result
    assert orderer.wait == get_pulse_violence() == 12, f"expected wait 12, got {orderer.wait}"


def test_do_order_no_followers_does_not_apply_wait_state(monkeypatch):
    """ROM only applies WAIT_STATE inside `if (found)` — a no-follower order costs no lag."""
    from mud.commands import group_commands as gc

    room = _room(51002)
    orderer = _orderer("Master", room)
    # No charmed followers in the room.
    other = create_test_character("Stranger", room.vnum)
    other.is_npc = True
    other.affected_by = 0

    monkeypatch.setattr(gc, "_send_to_char_sync", lambda *a, **k: None, raising=False)
    import mud.commands.dispatcher as _disp

    monkeypatch.setattr(_disp, "process_command", lambda *a, **k: None)

    result = gc.do_order(orderer, "all sit")

    assert "no followers" in result.lower(), result
    assert orderer.wait == 0, f"no-follower order must not apply wait, got {orderer.wait}"
