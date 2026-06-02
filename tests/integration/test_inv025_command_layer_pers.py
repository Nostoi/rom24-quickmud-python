"""INV-025 command-layer PERS sweep — baked-name `room.broadcast` in mud/commands/.

The INV-025 PERS-masking passes converted `_act_room` sites and `handlers.py`
manual loops, but the command layer still emitted ROM `act("$n …", TO_ROOM)`
lines as `room.broadcast(f"{char.name} …")` — no `$n` PERS masking, so an
invisible actor leaked its name to unaided witnesses.

This converts the confirmed command-layer sites to `act_to_room`:
  * `do_practice` (`act_info.c:2779/2787`), `do_train` durability/power/`$T`
    stat (`act_move.c:1760/1777/1798`)  — advancement.py
  * `do_recall` pray/disappear/appear (`act_move.c:1575/1618/1621`) — session.py
  * note start/finish (`board.c:503/1181`, `{G..{x` colour, finish `$s`) — notes.py

Representative masking coverage below: an invisible actor renders "Someone" to a
sighted witness (do_recall pray, do_train durability).
"""

from __future__ import annotations

from mud.commands.advancement import do_train
from mud.commands.session import do_recall
from mud.models.character import Character, PCData
from mud.models.constants import ActFlag, AffectFlag, Position, Sector
from mud.models.room import Room


def _room(vnum: int, sector: int = int(Sector.CITY)) -> Room:
    room = Room(vnum=vnum, name="Hall", sector_type=sector)
    room.people = []
    return room


def test_recall_pray_masks_invisible_actor() -> None:
    room = _room(9301)
    ch = Character(name="Prayer", level=20, is_npc=False, room=room, position=Position.STANDING)
    witness = Character(name="Witness", level=18, is_npc=False, room=room)
    room.people.extend([ch, witness])
    ch.add_affect(AffectFlag.INVISIBLE)
    witness.messages.clear()

    do_recall(ch, "")

    # ROM act("$n prays for transportation!", ...) — invisible actor → "Someone".
    assert any(m == "Someone prays for transportation!" for m in witness.messages), witness.messages


def test_recall_pray_shows_name_to_sighted_witness() -> None:
    room = _room(9302)
    ch = Character(name="Prayer", level=20, is_npc=False, room=room, position=Position.STANDING)
    witness = Character(name="Witness", level=18, is_npc=False, room=room)
    room.people.extend([ch, witness])
    witness.messages.clear()

    do_recall(ch, "")

    assert any(m == "Prayer prays for transportation!" for m in witness.messages), witness.messages


def test_train_durability_masks_invisible_actor() -> None:
    from mud.registry import room_registry

    room = _room(9303)
    room_registry[9303] = room
    try:
        ch = Character(
            name="Trainee", level=10, is_npc=False, room=room,
            hit=100, max_hit=100, position=Position.STANDING,
        )
        ch.pcdata = PCData()
        ch.train = 5
        witness = Character(name="Witness", level=18, is_npc=False, room=room)
        # ROM do_train requires an ACT_TRAIN mob in the room (TRAIN-003).
        trainer = Character(name="adept", short_descr="an adept", is_npc=True, act=int(ActFlag.TRAIN), room=room)
        room.people.extend([ch, witness, trainer])
        ch.add_affect(AffectFlag.INVISIBLE)
        witness.messages.clear()

        do_train(ch, "hp")

        # ROM act("$n's durability increases!", ...) — invisible actor → "Someone's".
        assert any(m == "Someone's durability increases!" for m in witness.messages), witness.messages
    finally:
        room_registry.pop(9303, None)
