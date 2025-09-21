from mud import mobprog
from mud.models.character import Character
from mud.models.constants import Direction
from mud.models.room import Exit, Room
from mud.world.movement import move_character


def _build_rooms() -> tuple[Room, Room]:
    start = Room(vnum=5000, name="Start")
    target = Room(vnum=5001, name="Target")
    start.exits[Direction.NORTH.value] = Exit(to_room=target, keyword="archway")
    return start, target


def test_npc_entry_trigger_runs_before_greet(monkeypatch) -> None:
    start, target = _build_rooms()

    npc = Character(name="Watcher", is_npc=True, move=20)
    start.add_character(npc)

    calls: list[tuple[str, Character, mobprog.Trigger]] = []

    def fake_percent(
        mob: Character,
        actor: Character | None = None,
        arg1: object | None = None,
        arg2: object | None = None,
        trigger: mobprog.Trigger = mobprog.Trigger.RANDOM,
    ) -> bool:
        calls.append(("percent", mob, trigger))
        return False

    def fake_greet(ch: Character) -> None:
        calls.append(("greet", ch, mobprog.Trigger.GREET))

    monkeypatch.setattr(mobprog, "mp_percent_trigger", fake_percent)
    monkeypatch.setattr(mobprog, "mp_greet_trigger", fake_greet)

    move_character(npc, "north")

    assert npc.room is target
    assert calls == [("percent", npc, mobprog.Trigger.ENTRY)]
