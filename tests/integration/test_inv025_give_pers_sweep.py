"""INV-025 give PERS sweep — `do_give` object + coins branches.

ROM `do_give` (`src/act_obj.c:659-855`) has two branches with DIFFERENT TRIG_ACT
contracts:

* **object branch** (`:830-846`) wraps its `act()` trio in
  `MOBtrigger = FALSE; … MOBtrigger = TRUE;` (`:832/:836`), so the room line does
  NOT fire TRIG_ACT — the dedicated `mp_give_trigger` (`:846`) covers the give
  event instead.
* **coins branch** (`:726`) is NOT MOBtrigger-suppressed, so `act("$n gives $N
  some coins.", …, TO_NOTVICT)` DOES dispatch TRIG_ACT (`src/comm.c:2384`).

Both branches baked the giver name via `act_format(recipient=None)` and shipped it
through `_broadcast_to_room_observers` (one baked string, no PERS masking); the
coins branch additionally never dispatched TRIG_ACT. Converted both to
`act_to_room` (per-recipient PERS; object branch wrapped in `disable_mobtrigger()`
to keep TRIG_ACT suppressed, coins branch plain so TRIG_ACT fires).
"""

from __future__ import annotations

import pytest

from mud.commands.give import do_give
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, ItemType, Position, WearFlag
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(9600, None)


class _FakeProg:
    def __init__(self, trig_type: int, trig_phrase: str, code: str, vnum: int):
        self.trig_type = trig_type
        self.trig_phrase = trig_phrase
        self.code = code
        self.vnum = vnum


def _room() -> Room:
    room = Room(vnum=9600, name="Plaza", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9600] = room
    return room


def _giver(room: Room, *, invisible: bool) -> Character:
    ch = Character(
        name="Glark",
        is_npc=False,
        level=20,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    ch.messages = []
    ch.inventory = []
    ch.silver = 1000
    room.people.append(ch)
    character_registry.append(ch)
    if invisible:
        ch.add_affect(AffectFlag.INVISIBLE)
    return ch


def _victim(room: Room) -> Character:
    v = Character(
        name="Victim",
        is_npc=False,
        level=20,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    v.messages = []
    v.inventory = []
    room.people.append(v)
    character_registry.append(v)
    return v


def _witness(room: Room) -> Character:
    w = Character(name="Witness", is_npc=False, level=18, room=room, position=int(Position.STANDING))
    w.messages = []
    room.people.append(w)
    character_registry.append(w)
    return w


def _listener(room: Room, phrase: str, vnum: int = 9601) -> Character:
    from mud.mobprog import Trigger

    listener = Character(
        name=f"watcher_{vnum}",
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=vnum, short_descr="a watcher", level=10)
    proto.mprogs = [_FakeProg(trig_type=int(Trigger.ACT), trig_phrase=phrase, code='mob echo "X"\n', vnum=vnum)]
    listener.prototype = proto
    room.people.append(listener)
    character_registry.append(listener)
    return listener


def _sword(holder: Character) -> Object:
    proto = ObjIndex(vnum=9602, name="sword", short_descr="a long sword", item_type=int(ItemType.WEAPON))
    proto.weight = 1
    proto.wear_flags = int(WearFlag.TAKE) | int(WearFlag.WIELD)
    proto.value = [0, 0, 0, 0, 0]
    obj = Object(instance_id=None, prototype=proto)
    obj.wear_flags = int(WearFlag.TAKE) | int(WearFlag.WIELD)
    obj.wear_loc = -1
    obj.weight = 1
    holder.add_object(obj)
    obj.carried_by = holder
    return obj


def _record_act_triggers(call):
    import mud.mobprog as mobprog

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *args, **kwargs):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *args, **kwargs)

    mobprog.mp_act_trigger = _probe
    try:
        call()
    finally:
        mobprog.mp_act_trigger = original
    return fired


def _line(c: Character) -> str:
    return "\n".join(c.messages)


def test_give_object_masks_invisible_giver():
    room = _room()
    ch = _giver(room, invisible=True)
    _victim(room)
    w = _witness(room)
    _sword(ch)
    w.messages.clear()

    do_give(ch, "sword Victim")

    # ROM act_obj.c:834 "$n gives $p to $N." TO_NOTVICT — invisible giver → "Someone".
    assert "Someone gives a long sword to Victim." in _line(w), w.messages


def test_give_object_suppresses_trig_act_on_bystander():
    room = _room()
    ch = _giver(room, invisible=False)
    _victim(room)
    _listener(room, "gives")  # NPC bystander (not the victim)
    _sword(ch)

    fired = _record_act_triggers(lambda: do_give(ch, "sword Victim"))

    # ROM act_obj.c:832 MOBtrigger=FALSE — the give room line must NOT fire TRIG_ACT.
    assert not any(name.startswith("watcher_") for name, _ in fired), fired


def test_give_coins_masks_invisible_giver():
    room = _room()
    ch = _giver(room, invisible=True)
    _victim(room)
    w = _witness(room)
    w.messages.clear()

    do_give(ch, "100 silver Victim")

    # ROM act_obj.c:726 "$n gives $N some coins." TO_NOTVICT — invisible giver → "Someone".
    assert "Someone gives Victim some coins." in _line(w), w.messages


def test_give_coins_fires_trig_act_on_bystander():
    room = _room()
    ch = _giver(room, invisible=False)
    _victim(room)
    _listener(room, "gives")  # NPC bystander (not the victim)

    fired = _record_act_triggers(lambda: do_give(ch, "100 silver Victim"))

    # ROM act_obj.c:726 is NOT MOBtrigger-suppressed — the room line fires TRIG_ACT.
    assert any(name.startswith("watcher_") and "gives" in arg for name, arg in fired), fired
