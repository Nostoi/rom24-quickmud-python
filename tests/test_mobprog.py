from mud.mobprog import Trigger
import mud.mobprog as mobprog
from mud.models.character import Character
from mud.models.constants import AffectFlag, Position
from mud.models.mob import MobProgram
from mud.models.room import Room


def _make_room() -> tuple[Room, Character]:
    room = Room(vnum=4000, name="MobProg Test Chamber")
    mob = Character(name="Watcher", is_npc=True)
    mob.position = Position.STANDING
    mob.default_pos = Position.STANDING
    room.add_character(mob)
    return room, mob


def test_random_trigger_picks_visible_pc(monkeypatch) -> None:
    room, mob = _make_room()

    alpha = Character(name="Alpha", is_npc=False)
    bravo = Character(name="Bravo", is_npc=False)
    sneaky = Character(name="Sneaky", is_npc=False)
    sneaky.affected_by |= int(AffectFlag.INVISIBLE)
    bystander = Character(name="Helper", is_npc=True)

    for ch in (alpha, bravo, sneaky, bystander):
        room.add_character(ch)

    rolls = iter([30, 80])
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: next(rolls))

    assert mobprog._get_random_char(mob) is bravo


def test_invisible_player_does_not_trigger_greet(monkeypatch) -> None:
    room, mob = _make_room()
    program = MobProgram(
        trig_type=int(Trigger.GREET),
        trig_phrase="100",
        vnum=2000,
        code="mob echo Greetings mortal.",
    )
    mob.mob_programs = [program]

    visible = Character(name="Visible", is_npc=False)
    invisible = Character(name="Hidden", is_npc=False)
    invisible.affected_by |= int(AffectFlag.INVISIBLE)

    for ch in (visible, invisible):
        room.add_character(ch)

    fired: list[Character] = []

    def fake_percent(
        mob_arg: Character,
        actor: Character | None,
        arg1=None,
        arg2=None,
        trigger: Trigger = Trigger.RANDOM,
    ) -> bool:
        fired.append(actor)
        return True

    monkeypatch.setattr(mobprog, "mp_percent_trigger", fake_percent)

    assert mobprog._count_people_room(mob, 1) == 1

    mobprog.mp_greet_trigger(invisible)
    assert fired == []

    mobprog.mp_greet_trigger(visible)
    assert fired == [visible]

    invisible.affected_by &= ~int(AffectFlag.INVISIBLE)
    mobprog.mp_greet_trigger(invisible)
    assert fired[-1] is invisible
    assert mobprog._count_people_room(mob, 1) == 2
