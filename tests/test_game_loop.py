import mud.game_loop as gl
from mud.ai import mobile_update
from mud.config import get_pulse_tick
from mud.game_loop import (
    SkyState,
    char_update,
    events,
    game_tick,
    obj_update,
    schedule_event,
    weather,
    weather_tick,
)
from mud.models.area import Area
from mud.models.character import Character, PCData, SpellEffect, character_registry
from mud.models.constants import ActFlag, Condition, ItemType, Position, Size, WearFlag, WearLocation, ROOM_VNUM_LIMBO
from mud.models.obj import ObjIndex, ObjectData, object_registry
from mud.models.room import Room
from mud.models.room import room_registry
from mud.utils import rng_mm
from mud.time import time_info
import mud.mobprog as mobprog


def setup_function(_):
    character_registry.clear()
    events.clear()
    weather.sky = SkyState.CLOUDLESS
    weather.mmhg = 1016
    weather.change = 0
    gl._pulse_counter = 0
    gl._point_counter = 0
    gl._violence_counter = 0
    gl._area_counter = 0
    object_registry.clear()
    room_registry.clear()


def test_regen_tick_increases_resources():
    area = Area(name="Inn")
    room = Room(vnum=10, area=area)
    room_registry[room.vnum] = room

    ch = Character(
        name="Bob",
        hit=5,
        max_hit=10,
        mana=3,
        max_mana=10,
        move=4,
        max_move=10,
        ch_class=3,
        is_npc=False,
        position=int(Position.STANDING),
        pcdata=PCData(condition=[48, 48, 48, 48]),
        perm_stat=[13, 13, 13, 13, 13],
    )
    room.add_character(ch)
    character_registry.append(ch)
    pulses = get_pulse_tick()
    game_tick()
    assert ch.hit == 8 and ch.mana == 4 and ch.move == 10
    for _ in range(max(0, pulses - 1)):
        game_tick()
    assert ch.hit == 8 and ch.mana == 4 and ch.move == 10
    game_tick()
    assert ch.hit == 10 and ch.mana == 5 and ch.move == 10


def test_weather_pressure_and_sky_transitions(monkeypatch):
    dice_rolls = iter([4, 2, 12] * 5)
    bit_rolls = iter([0, 0, 0, 0, 0])

    monkeypatch.setattr(rng_mm, "dice", lambda *_: next(dice_rolls))
    monkeypatch.setattr(rng_mm, "number_bits", lambda *_: next(bit_rolls))

    time_info.month = 0
    weather.sky = SkyState.CLOUDLESS
    weather.mmhg = 1016
    weather.change = 0

    weather_tick()
    assert weather.sky == SkyState.CLOUDY
    assert weather.change == -12
    assert weather.mmhg == 1004

    weather_tick()
    assert weather.sky == SkyState.CLOUDY
    assert weather.mmhg == 992

    weather_tick()
    assert weather.sky == SkyState.RAINING
    assert weather.mmhg == 980

    weather_tick()
    assert weather.sky == SkyState.LIGHTNING
    assert weather.mmhg == 968

    weather_tick()
    assert weather.sky == SkyState.LIGHTNING
    assert weather.mmhg == 960


def test_timed_event_fires_after_delay():
    triggered: list[int] = []
    schedule_event(2, lambda: triggered.append(1))
    game_tick()
    assert not triggered
    game_tick()
    assert triggered == [1]


def test_aggressive_mobile_attacks_player(monkeypatch):
    area = Area(name="Arena")
    room = Room(vnum=42, area=area)

    hero = Character(
        name="Hero",
        level=5,
        hit=20,
        max_hit=20,
        mana=10,
        max_mana=10,
        move=10,
        max_move=10,
        is_npc=False,
        position=int(Position.STANDING),
    )
    brute = Character(
        name="Brute",
        level=5,
        hit=20,
        max_hit=20,
        act=int(ActFlag.AGGRESSIVE),
        position=int(Position.STANDING),
    )

    room.add_character(hero)
    room.add_character(brute)
    character_registry.extend([hero, brute])

    monkeypatch.setattr(rng_mm, "number_bits", lambda _: 1)

    game_tick()

    assert brute.fighting is hero
    assert hero.fighting is brute


def test_mobile_update_runs_random_trigger(monkeypatch):
    area = Area(name="Shrine")
    room = Room(vnum=200, area=area)
    room_registry[room.vnum] = room

    oracle = Character(
        name="Oracle",
        is_npc=True,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    room.add_character(oracle)
    character_registry.append(oracle)

    calls: list[Character] = []

    monkeypatch.setattr(mobprog, "mp_delay_trigger", lambda mob: False)

    def fake_random(mob: Character) -> bool:
        calls.append(mob)
        return True

    monkeypatch.setattr(mobprog, "mp_random_trigger", fake_random)

    mobile_update()

    assert calls == [oracle]
    assert oracle.room is room


def test_mobile_update_scavenges_room_loot(monkeypatch):
    area = Area(name="Dump")
    room = Room(vnum=201, area=area)
    room_registry[room.vnum] = room

    scavenger = Character(
        name="Picker",
        is_npc=True,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
        act=int(ActFlag.SCAVENGER),
        carry_number=0,
        carry_weight=0,
    )
    room.add_character(scavenger)
    character_registry.append(scavenger)

    cheap = ObjectData(
        item_type=int(ItemType.TRASH),
        wear_flags=int(WearFlag.TAKE),
        cost=5,
        short_descr="tin can",
    )
    pricey = ObjectData(
        item_type=int(ItemType.TRASH),
        wear_flags=int(WearFlag.TAKE),
        cost=25,
        short_descr="bright gem",
    )
    room.add_object(cheap)
    room.add_object(pricey)

    def fake_number_bits(width: int) -> int:
        if width == 6:
            return 0
        if width == 3:
            return 1
        if width == 5:
            return 6
        return 0

    monkeypatch.setattr(rng_mm, "number_bits", fake_number_bits)

    mobile_update()

    assert pricey in getattr(scavenger, "inventory", [])
    assert pricey.carried_by is scavenger
    assert cheap in getattr(room, "contents", [])
    assert pricey not in getattr(room, "contents", [])
    assert scavenger.carry_number == 1


def test_char_update_applies_conditions(monkeypatch):
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 75)

    area = Area(name="Rest")
    room = Room(vnum=42, area=area)
    room_registry[room.vnum] = room

    pcdata = PCData(condition=[1, 2, 1, 1])
    hero = Character(
        name="Hero",
        level=5,
        ch_class=3,
        hit=5,
        max_hit=10,
        mana=3,
        max_mana=10,
        move=4,
        max_move=10,
        is_npc=False,
        position=int(Position.STANDING),
        size=int(Size.MEDIUM),
        pcdata=pcdata,
        perm_stat=[13, 13, 13, 13, 13],
    )
    room.add_character(hero)
    character_registry.append(hero)

    effect = SpellEffect(name="armor", duration=1, ac_mod=-10, wear_off_message="You feel less protected.")
    hero.apply_spell_effect(effect)

    char_update()

    assert hero.hit == 9
    assert hero.mana == 4
    assert hero.move == 10
    assert hero.pcdata.condition == [0, 0, 0, 0]
    assert hero.spell_effects == {}
    assert hero.messages == [
        "You feel less protected.",
        "You are sober.",
        "You are thirsty.",
        "You are hungry.",
    ]


def test_char_update_idles_linkdead():
    area = Area(name="Void")
    room = Room(vnum=100, area=area)
    limbo = Room(vnum=ROOM_VNUM_LIMBO, area=area)
    room_registry[room.vnum] = room
    room_registry[limbo.vnum] = limbo

    idle = Character(
        name="Sleeper",
        level=10,
        hit=20,
        max_hit=20,
        mana=15,
        max_mana=15,
        move=10,
        max_move=10,
        is_npc=False,
        position=int(Position.STANDING),
        pcdata=PCData(condition=[48, 48, 48, 48]),
        timer=11,
    )
    idle.desc = None
    room.add_character(idle)
    character_registry.append(idle)

    watcher = Character(
        name="Watcher",
        is_npc=False,
        position=int(Position.STANDING),
        pcdata=PCData(condition=[48, 48, 48, 48]),
    )
    watcher.desc = object()
    room.add_character(watcher)
    character_registry.append(watcher)

    char_update()

    assert idle.room is limbo
    assert idle.was_in_room is room
    assert idle in limbo.people
    assert idle not in room.people
    assert idle.messages[-1] == "You disappear into the void."
    assert "Sleeper disappears into the void." in watcher.messages


def test_obj_update_decays_corpse():
    area = Area(name="Battlefield")
    room = Room(vnum=200, area=area)
    room_registry[room.vnum] = room

    observer = Character(name="Onlooker", is_npc=False, pcdata=PCData(condition=[48, 48, 48, 48]))
    room.add_character(observer)
    character_registry.append(observer)

    proto = ObjIndex(vnum=1, short_descr="orc corpse")
    corpse = ObjectData(item_type=int(ItemType.CORPSE_NPC), timer=1, short_descr="orc corpse", pIndexData=proto)
    corpse.in_room = room
    room.contents.append(corpse)
    object_registry.extend([corpse])

    obj_update()

    assert corpse not in object_registry
    assert corpse not in room.contents
    assert "orc corpse decays into dust." in observer.messages


def test_obj_update_spills_floating_container():
    area = Area(name="Treasure")
    room = Room(vnum=300, area=area)
    room_registry[room.vnum] = room

    observer = Character(name="Collector", is_npc=False, pcdata=PCData(condition=[48, 48, 48, 48]))
    room.add_character(observer)
    character_registry.append(observer)

    chest = ObjectData(
        item_type=int(ItemType.CONTAINER),
        wear_flags=int(WearFlag.WEAR_FLOAT),
        timer=1,
        short_descr="drifting chest",
    )
    gem = ObjectData(item_type=int(ItemType.GEM), timer=0, short_descr="shiny gem")
    chest.contains.append(gem)
    gem.in_obj = chest

    room.contents.append(chest)
    chest.in_room = room
    object_registry.extend([chest, gem])

    obj_update()

    assert chest not in object_registry
    assert chest not in room.contents
    assert gem in room.contents
    assert gem.in_room is room
    assert "drifting chest flickers and vanishes, spilling its contents on the floor." in observer.messages
