"""ORDER-001 — do_order TO_VICT routed through act()-equivalent visibility gating.

ROM C: ``src/act_comm.c:1752-1754``
    sprintf(buf, "$n orders you to '%s'.", argument);
    act(buf, ch, NULL, och, TO_VICT);

ROM ``act()`` substitutes ``$n`` via ``pers(ch, vict)`` which returns
``"someone"`` when the recipient can't see the actor (wiz-invis, dark room,
etc.). Pre-fix Python formatted ``f"{char.name} orders you..."`` manually,
revealing wiz-invis orderers regardless of recipient trust.
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


def _charmed_follower(name: str, room: Room, master: Character) -> Character:
    follower = Character(name=name, is_npc=True, level=1, room=room, hit=100, max_hit=100)
    follower.act = int(ActFlag.IS_NPC)
    follower.affected_by = int(AffectFlag.CHARM)
    follower.master = master
    follower.trust = 0
    follower.level = 1
    follower.messages = []
    room.people.append(follower)
    character_registry.append(follower)
    return follower


def test_do_order_wiz_invis_orderer_renders_as_someone(monkeypatch):
    # mirrors ROM src/act_comm.c:1752-1754 — act() pers() returns "someone" when
    # viewer can't see actor (wiz-invis above viewer trust)
    from mud.commands import group_commands as gc

    room = _room(50800)
    orderer = create_test_character("Bigwiz", room.vnum)
    orderer.is_npc = False
    orderer.level = 60
    orderer.trust = 60
    orderer.invis_level = 60  # wiz-invis to anyone below trust 60
    orderer.messages = []

    _charmed_follower("fido", room, orderer)
    # follower.trust = 0 — cannot see orderer

    delivered: list[tuple[str, str]] = []

    def fake_send(char, message):
        delivered.append((getattr(char, "name", "?"), message))

    monkeypatch.setattr(gc, "_send_to_char_sync", fake_send, raising=False)

    # Stub out process_command to avoid executing the order down the real dispatcher
    import mud.commands.dispatcher as _disp

    monkeypatch.setattr(_disp, "process_command", lambda *a, **k: None)

    gc.do_order(orderer, "fido smile")

    follower_msgs = [m for n, m in delivered if n == "fido"]
    assert follower_msgs, f"follower received nothing: {delivered!r}"
    msg = follower_msgs[0]
    # Visibility-gated rendering: orderer hidden → "Someone orders you to 'smile'."
    assert "Bigwiz" not in msg, f"wiz-invis orderer name leaked to low-trust follower: {msg!r}"
    assert "someone" in msg.lower() and "orders you to 'smile'" in msg, f"expected someone-rendered order; got {msg!r}"


def test_do_order_visible_orderer_renders_with_name(monkeypatch):
    # Visible orderer (no invis_level) should still render with name
    from mud.commands import group_commands as gc

    room = _room(50900)
    orderer = create_test_character("Master", room.vnum)
    orderer.is_npc = False
    orderer.level = 30
    orderer.trust = 30
    orderer.messages = []

    _charmed_follower("rex", room, orderer)

    delivered: list[tuple[str, str]] = []

    def fake_send(char, message):
        delivered.append((getattr(char, "name", "?"), message))

    monkeypatch.setattr(gc, "_send_to_char_sync", fake_send, raising=False)
    monkeypatch.setattr(gc, "process_command", lambda *a, **k: None, raising=False)

    gc.do_order(orderer, "rex sit")

    follower_msgs = [m for n, m in delivered if n == "rex"]
    assert follower_msgs, f"follower received nothing: {delivered!r}"
    assert any("Master orders you to 'sit'" in m for m in follower_msgs), (
        f"expected visible orderer name; got {follower_msgs!r}"
    )
