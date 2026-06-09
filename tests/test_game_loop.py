from types import SimpleNamespace

import mud.game_loop as gl
import mud.mobprog as mobprog
from mud.ai import mobile_update
from mud.config import get_pulse_tick, get_pulse_violence
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
from mud.models.character import AffectData, Character, PCData, SpellEffect, character_registry
from mud.models.constants import (
    ROOM_VNUM_LIMBO,
    ActFlag,
    AffectFlag,
    ItemType,
    Position,
    RoomFlag,
    Size,
    WearFlag,
    WearLocation,
)
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex, object_registry
from mud.models.object import Object
from mud.models.room import Room, room_registry
from mud.models.shop import Shop
from mud.time import time_info
from mud.utils import rng_mm
from mud.wiznet import WiznetFlag


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
    gl._AUTOSAVE_ROTATION = 0
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


def test_weather_broadcasts_outdoor_characters(monkeypatch):
    area = Area(name="Field")
    outside = Room(vnum=101, area=area, room_flags=0)
    inside = Room(vnum=102, area=area, room_flags=int(RoomFlag.ROOM_INDOORS))
    sleepy_room = Room(vnum=103, area=area, room_flags=0)
    room_registry[outside.vnum] = outside
    room_registry[inside.vnum] = inside
    room_registry[sleepy_room.vnum] = sleepy_room

    awake_outdoor = Character(name="Scout", is_npc=False, position=int(Position.STANDING))
    awake_indoor = Character(name="Hermit", is_npc=False, position=int(Position.STANDING))
    asleep_outdoor = Character(name="Sleeper", is_npc=False, position=int(Position.SLEEPING))

    outside.add_character(awake_outdoor)
    inside.add_character(awake_indoor)
    sleepy_room.add_character(asleep_outdoor)

    character_registry.extend([awake_outdoor, awake_indoor, asleep_outdoor])

    time_info.month = 0
    weather.sky = SkyState.CLOUDLESS
    weather.mmhg = 980
    weather.change = 0

    monkeypatch.setattr(rng_mm, "dice", lambda *_: 0)
    monkeypatch.setattr(rng_mm, "number_bits", lambda *_: 1)

    weather_tick()

    assert awake_outdoor.messages == ["The sky is getting cloudy.\r\n"]
    assert not awake_indoor.messages
    assert not asleep_outdoor.messages


def test_timed_event_fires_after_delay():
    triggered: list[int] = []
    schedule_event(2, lambda: triggered.append(1))
    game_tick()
    assert not triggered
    game_tick()
    assert triggered == [1]


def test_point_pulse_emits_tick_wiznet_before_updates(monkeypatch):
    gl._pulse_counter = 0
    gl._point_counter = 1
    gl._area_counter = 999999
    gl._music_counter = 999999
    gl._mobile_counter = 999999
    gl._violence_counter = 999999

    calls: list[object] = []

    def fake_wiznet(message, sender=None, obj=None, flag=None, flag_skip=None, min_level=0):
        calls.append(("wiznet", message, flag))

    monkeypatch.setattr(gl, "wiznet", fake_wiznet)
    monkeypatch.setattr(gl, "time_tick", lambda: calls.append("time_tick"))
    monkeypatch.setattr(gl, "weather_tick", lambda: calls.append("weather_tick"))
    monkeypatch.setattr(gl, "char_update", lambda: calls.append("char_update"))
    monkeypatch.setattr(gl, "obj_update", lambda: calls.append("obj_update"))
    monkeypatch.setattr(gl, "pump_idle", lambda: calls.append("pump_idle"))
    monkeypatch.setattr(gl, "event_tick", lambda: calls.append("event_tick"))
    monkeypatch.setattr(gl, "aggressive_update", lambda: calls.append("aggressive_update"))

    game_tick()

    assert calls[0] == ("wiznet", "TICK!", WiznetFlag.WIZ_TICKS)
    assert calls[1:6] == [
        "time_tick",
        "weather_tick",
        "char_update",
        "obj_update",
        "pump_idle",
    ]


def test_violence_update_waits_for_pulse_violence(monkeypatch):
    room = object()
    attacker = Character(name="Attacker", is_npc=False, position=int(Position.FIGHTING))
    victim = Character(name="Victim", is_npc=False, position=int(Position.FIGHTING))
    attacker.room = room
    victim.room = room
    attacker.fighting = victim
    victim.fighting = attacker
    character_registry.extend([attacker, victim])

    gl._pulse_counter = 0
    gl._point_counter = 999999
    gl._area_counter = 999999
    gl._music_counter = 999999
    gl._mobile_counter = 999999
    gl._violence_counter = get_pulse_violence()

    calls: list[int] = []
    monkeypatch.setattr("mud.combat.engine.multi_hit", lambda ch, vic, dt=None: calls.append(gl._pulse_counter))
    monkeypatch.setattr("mud.combat.engine.stop_fighting", lambda ch, both=False: None)

    for _ in range(get_pulse_violence() - 1):
        game_tick()

    assert calls == []

    game_tick()

    assert calls == [get_pulse_violence(), get_pulse_violence()]


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


def test_mobile_update_mobprog_default_position_gate_precedes_standing_ai(monkeypatch):
    area = Area(name="Shrine")
    room = Room(vnum=202, area=area)
    room_registry[room.vnum] = room

    resting_guard = Character(
        name="Resting Guard",
        is_npc=True,
        position=int(Position.RESTING),
        default_pos=int(Position.STANDING),
        act=int(ActFlag.SCAVENGER),
        mprog_delay=1,
    )
    sleeping_oracle = Character(
        name="Sleeping Oracle",
        is_npc=True,
        position=int(Position.SLEEPING),
        default_pos=int(Position.SLEEPING),
        act=int(ActFlag.SCAVENGER),
    )
    room.add_character(resting_guard)
    room.add_character(sleeping_oracle)
    character_registry.extend([resting_guard, sleeping_oracle])

    relic = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=0, item_type=int(ItemType.TRASH), short_descr="silver relic"),
        wear_flags=int(WearFlag.TAKE),
        cost=50,
    )
    room.add_object(relic)

    calls: list[tuple[str, str]] = []

    def fake_delay(mob: Character) -> bool:
        calls.append(("delay", mob.name))
        return False

    def fake_random(mob: Character) -> bool:
        calls.append(("random", mob.name))
        return False

    monkeypatch.setattr(mobprog, "mp_delay_trigger", fake_delay)
    monkeypatch.setattr(mobprog, "mp_random_trigger", fake_random)
    monkeypatch.setattr(rng_mm, "number_bits", lambda _: 0)

    # Mirrors ROM src/update.c:443-465: delay/random fire only while the mob
    # is at default position, then non-standing mobs stop before scavenging.
    mobile_update()

    assert calls == [("delay", "Sleeping Oracle"), ("random", "Sleeping Oracle")]
    assert relic in getattr(room, "contents", [])
    assert relic not in getattr(resting_guard, "inventory", [])
    assert relic not in getattr(sleeping_oracle, "inventory", [])


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

    cheap = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=0, item_type=int(ItemType.TRASH), short_descr="tin can"),
        wear_flags=int(WearFlag.TAKE),
        cost=5,
    )
    pricey = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=0, item_type=int(ItemType.TRASH), short_descr="bright gem"),
        wear_flags=int(WearFlag.TAKE),
        cost=25,
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


def test_scavenger_pickup_dispatches_trig_act(monkeypatch):
    """Scavenger $n gets $p. broadcasts must dispatch TRIG_ACT — ROM src/update.c:491."""

    area = Area(name="Dump")
    room = Room(vnum=202, area=area)
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

    gem = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=0, item_type=int(ItemType.TRASH), short_descr="bright gem"),
        wear_flags=int(WearFlag.TAKE),
        cost=25,
    )
    room.add_object(gem)

    # NPC listener with a TRIG_ACT program watching for "bright gem"
    listener = Character(
        name="watcher",
        is_npc=True,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=9801, short_descr="a watcher", level=5)
    proto.mprogs = []
    listener.prototype = proto
    room.add_character(listener)
    character_registry.append(listener)

    fired: list[str] = []
    original_trigger = mobprog.mp_act_trigger

    def _probe(argument, recipient, *args, **kwargs):
        if recipient is listener:
            fired.append(str(argument))
        return original_trigger(argument, recipient, *args, **kwargs)

    monkeypatch.setattr(mobprog, "mp_act_trigger", _probe)

    def fake_number_bits(width: int) -> int:
        if width == 6:
            return 0  # scavenge fires
        if width == 3:
            return 1  # no wander
        if width == 5:
            return 6  # no wander
        return 0

    monkeypatch.setattr(rng_mm, "number_bits", fake_number_bits)

    mobile_update()

    assert any("bright gem" in msg for msg in fired), (
        "scavenger pickup must dispatch mp_act_trigger with '$n gets $p.' — ROM src/update.c:491"
    )


def test_mobile_update_refreshes_shopkeeper_wealth(monkeypatch):
    area = Area(name="Market")
    room = Room(vnum=305, area=area)
    room_registry[room.vnum] = room

    shop_proto = MobIndex(vnum=5000, wealth=6000)
    shop_proto.pShop = Shop(keeper=shop_proto.vnum)

    keeper = Character(
        name="Clerk",
        is_npc=True,
        gold=0,
        silver=50,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    keeper.prototype = shop_proto
    room.add_character(keeper)
    character_registry.append(keeper)

    rolls = iter([20, 20, 10, 10])
    monkeypatch.setattr(rng_mm, "number_range", lambda *_: next(rolls))

    mobile_update()
    assert keeper.gold == 0
    assert keeper.silver == 52

    mobile_update()
    assert keeper.gold == 0
    assert keeper.silver == 53


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
    assert "armor" in hero.spell_effects
    assert hero.spell_effects["armor"].duration == 0
    assert hero.messages == [
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


def test_char_update_autosaves_on_rotation(monkeypatch):
    area = Area(name="Inn")
    room = Room(vnum=501, area=area)
    room_registry[room.vnum] = room

    hero = Character(
        name="Saver",
        level=10,
        is_npc=False,
        position=int(Position.STANDING),
        pcdata=PCData(condition=[48, 48, 48, 48]),
    )
    hero.desc = SimpleNamespace(descriptor_id=30)
    room.add_character(hero)

    bystander = Character(
        name="Skipper",
        level=10,
        is_npc=False,
        position=int(Position.STANDING),
        pcdata=PCData(condition=[48, 48, 48, 48]),
    )
    bystander.desc = SimpleNamespace(descriptor_id=17)
    room.add_character(bystander)

    character_registry.extend([hero, bystander])

    saved: list[Character] = []
    monkeypatch.setattr(gl, "save_character", lambda ch: saved.append(ch))

    gl._AUTOSAVE_ROTATION = gl._AUTOSAVE_WINDOW - 1
    char_update()

    assert saved == [hero]


def test_char_update_auto_quits_linkdead(monkeypatch):
    area = Area(name="LimboLand")
    room = Room(vnum=200, area=area)
    limbo = Room(vnum=ROOM_VNUM_LIMBO, area=area)
    room_registry[room.vnum] = room
    room_registry[limbo.vnum] = limbo

    ghost = Character(name="Ghost", level=10, is_npc=False, pcdata=PCData(condition=[48, 48, 48, 48]))
    ghost.timer = 31
    ghost.room = limbo
    ghost.was_in_room = room
    limbo.add_character(ghost)
    character_registry.append(ghost)

    saved: list[Character] = []
    monkeypatch.setattr(gl, "save_character", lambda ch: saved.append(ch))

    char_update()

    assert saved == [ghost]
    assert ghost not in character_registry
    assert ghost.room is None


def test_light_decay_extinguishes_worn_torch():
    area = Area(name="Cavern")
    room = Room(vnum=300, area=area, light=2)
    room_registry[room.vnum] = room

    hero = Character(
        name="Torchbearer",
        level=5,
        is_npc=False,
        position=int(Position.STANDING),
        pcdata=PCData(condition=[48, 48, 48, 48]),
    )
    room.add_character(hero)
    character_registry.append(hero)

    watcher = Character(
        name="Watcher",
        level=5,
        is_npc=False,
        position=int(Position.STANDING),
        pcdata=PCData(condition=[48, 48, 48, 48]),
    )
    room.add_character(watcher)
    character_registry.append(watcher)

    torch = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=0, item_type=int(ItemType.LIGHT), short_descr="bronze torch"),
    )
    torch.value = [0, 0, 1]
    torch.wear_loc = int(WearLocation.LIGHT)
    torch.carried_by = hero
    object_registry.append(torch)
    hero.equipment[int(WearLocation.LIGHT)] = torch

    char_update()

    assert hero.equipment == {}
    assert torch not in object_registry
    assert room.light == 1
    assert "bronze torch flickers and goes out." in hero.messages
    assert "Bronze torch goes out." in watcher.messages


def test_char_update_decays_light_before_lethal_poison_tick():
    area = Area(name="Cavern")
    room = Room(vnum=301, area=area, light=2)
    room_registry[room.vnum] = room

    hero = Character(
        name="Poisoned",
        level=5,
        hit=1,
        max_hit=1,
        mana=1,
        max_mana=1,
        move=1,
        max_move=1,
        is_npc=False,
        position=int(Position.STANDING),
        pcdata=PCData(condition=[48, 48, 48, 48]),
    )
    room.add_character(hero)
    character_registry.append(hero)

    watcher = Character(
        name="Watcher",
        level=5,
        is_npc=False,
        position=int(Position.STANDING),
        pcdata=PCData(condition=[48, 48, 48, 48]),
    )
    room.add_character(watcher)
    character_registry.append(watcher)

    torch = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=0, item_type=int(ItemType.LIGHT), short_descr="brass lantern"),
    )
    torch.value = [0, 0, 1]
    torch.wear_loc = int(WearLocation.LIGHT)
    torch.carried_by = hero
    object_registry.append(torch)
    hero.equipment[int(WearLocation.LIGHT)] = torch

    # mirrors ROM src/update.c:721-862 — worn-light decay runs before
    # affect-tick poison damage, even when the poison tick is lethal.
    hero.add_affect(AffectFlag.POISON)
    hero.affected.append(
        AffectData(
            type="poison",  # type: ignore[arg-type]
            level=120,
            duration=-1,
            location=0,
            modifier=0,
            bitvector=int(AffectFlag.POISON),
        )
    )

    char_update()

    assert room.light == 1
    assert torch not in object_registry
    assert "brass lantern flickers and goes out." in hero.messages
    assert "Brass lantern goes out." in watcher.messages
    assert "Poisoned shivers and suffers." in watcher.messages


def test_char_update_extracts_out_of_zone_mob(monkeypatch):
    from mud.game_loop import char_update

    area_home = Area(name="Town")
    area_foreign = Area(name="Dungeon")
    home_room = Room(vnum=400, area=area_home)
    away_room = Room(vnum=401, area=area_foreign)
    room_registry[home_room.vnum] = home_room
    room_registry[away_room.vnum] = away_room

    wanderer = Character(
        name="Rover",
        short_descr="Rover",
        is_npc=True,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    wanderer.zone = area_home
    away_room.add_character(wanderer)
    character_registry.append(wanderer)

    watcher = Character(
        name="Watcher",
        is_npc=False,
        position=int(Position.STANDING),
        pcdata=PCData(condition=[48, 48, 48, 48]),
    )
    away_room.add_character(watcher)
    character_registry.append(watcher)

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 0)

    char_update()

    assert wanderer.room is None
    assert wanderer not in character_registry
    assert wanderer not in home_room.people
    assert wanderer not in away_room.people
    assert "Rover wanders on home." in watcher.messages


def test_wanders_home_dispatches_trig_act(monkeypatch):
    """NPC wanders-home broadcast must dispatch TRIG_ACT — ROM src/update.c:693."""

    area_home = Area(name="Town2")
    area_foreign = Area(name="Dungeon2")
    home_room = Room(vnum=405, area=area_home)
    away_room = Room(vnum=406, area=area_foreign)
    room_registry[home_room.vnum] = home_room
    room_registry[away_room.vnum] = away_room

    wanderer = Character(
        name="Drifter",
        short_descr="Drifter",
        is_npc=True,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    wanderer.zone = area_home
    away_room.add_character(wanderer)
    character_registry.append(wanderer)

    listener = Character(
        name="listener",
        is_npc=True,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=9802, short_descr="a listener", level=5)
    proto.mprogs = []
    listener.prototype = proto
    away_room.add_character(listener)
    character_registry.append(listener)

    fired: list[str] = []
    original_trigger = mobprog.mp_act_trigger

    def _probe(argument, recipient, *args, **kwargs):
        if recipient is listener:
            fired.append(str(argument))
        return original_trigger(argument, recipient, *args, **kwargs)

    monkeypatch.setattr(mobprog, "mp_act_trigger", _probe)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 0)

    char_update()

    assert any("wanders on home" in msg for msg in fired), (
        "wanders-on-home must dispatch mp_act_trigger to NPC observers — ROM src/update.c:693"
    )


def test_poison_shiver_dispatches_trig_act(monkeypatch):
    """Poison tick '$n shivers' broadcast must dispatch TRIG_ACT — ROM src/update.c:857."""
    area = Area(name="Swamp")
    room = Room(vnum=407, area=area)
    room_registry[room.vnum] = room

    victim = Character(
        name="Vic",
        is_npc=False,
        position=int(Position.STANDING),
        hit=50,
        max_hit=50,
        pcdata=PCData(condition=[48, 48, 48, 48]),
    )
    victim.add_affect(AffectFlag.POISON)
    victim.affected.append(
        AffectData(
            type="poison",  # type: ignore[arg-type]
            level=20,
            duration=5,
            location=0,
            modifier=0,
            bitvector=int(AffectFlag.POISON),
        )
    )
    room.add_character(victim)
    character_registry.append(victim)

    listener = Character(
        name="watcher",
        is_npc=True,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=9803, short_descr="a watcher", level=5)
    proto.mprogs = []
    listener.prototype = proto
    room.add_character(listener)
    character_registry.append(listener)

    fired: list[str] = []
    original_trigger = mobprog.mp_act_trigger

    def _probe(argument, recipient, *args, **kwargs):
        if recipient is listener:
            fired.append(str(argument))
        return original_trigger(argument, recipient, *args, **kwargs)

    monkeypatch.setattr(mobprog, "mp_act_trigger", _probe)

    char_update()

    assert any("shivers" in msg for msg in fired), (
        "poison '$n shivers and suffers.' must dispatch mp_act_trigger — ROM src/update.c:857"
    )


def test_obj_update_decays_corpse():
    area = Area(name="Battlefield")
    room = Room(vnum=200, area=area)
    room_registry[room.vnum] = room

    observer = Character(name="Onlooker", is_npc=False, pcdata=PCData(condition=[48, 48, 48, 48]))
    room.add_character(observer)
    character_registry.append(observer)

    proto = ObjIndex(vnum=1, short_descr="orc corpse", item_type=int(ItemType.CORPSE_NPC))
    corpse = Object(instance_id=None, prototype=proto, timer=1)
    corpse.in_room = room
    room.contents.append(corpse)
    object_registry.extend([corpse])

    obj_update()

    assert corpse not in object_registry
    assert corpse not in room.contents
    assert "Orc corpse decays into dust." in observer.messages


def test_obj_update_decay_dispatches_trig_act(monkeypatch):
    """Object decay room act() must dispatch TRIG_ACT — ROM src/update.c:1017-1022."""

    area = Area(name="Ruins")
    room = Room(vnum=207, area=area)
    room_registry[room.vnum] = room

    witness = Character(name="First", is_npc=False, pcdata=PCData(condition=[48, 48, 48, 48]))
    room.add_character(witness)
    character_registry.append(witness)

    listener = Character(
        name="watcher",
        is_npc=True,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=9804, short_descr="a watcher", level=5)
    proto.mprogs = []
    listener.prototype = proto
    room.add_character(listener)
    character_registry.append(listener)

    corpse = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=2, short_descr="kobold corpse", item_type=int(ItemType.CORPSE_NPC)),
        timer=1,
    )
    room.add_object(corpse)
    object_registry.append(corpse)

    fired: list[tuple[str, object | None]] = []
    original_trigger = mobprog.mp_act_trigger

    def _probe(argument, recipient, actor=None, *args, **kwargs):
        if recipient is listener:
            fired.append((str(argument), actor))
        return original_trigger(argument, recipient, actor, *args, **kwargs)

    monkeypatch.setattr(mobprog, "mp_act_trigger", _probe)

    obj_update()

    assert any("Kobold corpse decays into dust" in msg for msg, _ in fired), (
        "object decay act(message, rch, obj, TO_ROOM) must dispatch mp_act_trigger — ROM src/update.c:1017"
    )
    assert any(actor is room.people[0] for _, actor in fired), (
        "object decay TRIG_ACT actor must be room->people rch — ROM src/update.c:1014-1022"
    )


def test_object_affect_wear_off_dispatches_trig_act(monkeypatch):
    """Object affect wear-off room act() must dispatch TRIG_ACT — ROM src/update.c:937-959."""

    area = Area(name="Vault")
    room = Room(vnum=208, area=area)
    room_registry[room.vnum] = room

    witness = Character(name="First", is_npc=False, pcdata=PCData(condition=[48, 48, 48, 48]))
    room.add_character(witness)
    character_registry.append(witness)

    listener = Character(
        name="watcher",
        is_npc=True,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=9805, short_descr="a watcher", level=5)
    proto.mprogs = []
    listener.prototype = proto
    room.add_character(listener)
    character_registry.append(listener)

    amulet = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=3, short_descr="silver amulet", item_type=int(ItemType.TREASURE)),
        timer=0,
    )
    room.add_object(amulet)
    affect = AffectData(type="bless", level=10, duration=0, location=0, modifier=0, bitvector=0)
    affect.wear_off_message = "$p stops glowing."
    amulet.affected = [affect]

    fired: list[tuple[str, object | None]] = []
    original_trigger = mobprog.mp_act_trigger

    def _probe(argument, recipient, actor=None, *args, **kwargs):
        if recipient is listener:
            fired.append((str(argument), actor))
        return original_trigger(argument, recipient, actor, *args, **kwargs)

    monkeypatch.setattr(mobprog, "mp_act_trigger", _probe)

    gl._tick_object_affects(amulet)

    assert any("Silver amulet stops glowing" in msg for msg, _ in fired), (
        "object affect wear-off must dispatch mp_act_trigger for its room act() — ROM src/update.c:944-959"
    )
    assert any(actor is room.people[0] for _, actor in fired), (
        "object affect wear-off TRIG_ACT actor must be room->people rch — ROM src/update.c:944-959"
    )


def test_carried_object_affect_wear_off_is_to_char_only(monkeypatch):
    """Carried object affect wear-off is TO_CHAR only — ROM src/update.c:940-944."""

    area = Area(name="Vault")
    room = Room(vnum=209, area=area)
    room_registry[room.vnum] = room

    carrier = Character(name="Carrier", is_npc=False, pcdata=PCData(condition=[48, 48, 48, 48]))
    room.add_character(carrier)
    character_registry.append(carrier)

    listener = Character(
        name="watcher",
        is_npc=True,
        position=int(Position.STANDING),
        default_pos=int(Position.STANDING),
    )
    listener.messages = []
    proto = MobIndex(vnum=9806, short_descr="a watcher", level=5)
    proto.mprogs = []
    listener.prototype = proto
    room.add_character(listener)
    character_registry.append(listener)

    amulet = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=4, short_descr="silver amulet", item_type=int(ItemType.TREASURE)),
        timer=0,
    )
    carrier.add_object(amulet)
    affect = AffectData(type="bless", level=10, duration=0, location=0, modifier=0, bitvector=0)
    affect.wear_off_message = "$p stops glowing."
    amulet.affected = [affect]

    fired: list[str] = []
    original_trigger = mobprog.mp_act_trigger

    def _probe(argument, recipient, *args, **kwargs):
        if recipient is listener:
            fired.append(str(argument))
        return original_trigger(argument, recipient, *args, **kwargs)

    monkeypatch.setattr(mobprog, "mp_act_trigger", _probe)

    gl._tick_object_affects(amulet)

    assert "Silver amulet stops glowing." in carrier.messages
    assert listener.messages == []
    assert fired == []


def test_obj_update_spills_floating_container():
    area = Area(name="Treasure")
    room = Room(vnum=300, area=area)
    room_registry[room.vnum] = room

    observer = Character(name="Collector", is_npc=False, pcdata=PCData(condition=[48, 48, 48, 48]))
    room.add_character(observer)
    character_registry.append(observer)

    chest = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=0, item_type=int(ItemType.CONTAINER), short_descr="drifting chest"),
        wear_flags=int(WearFlag.WEAR_FLOAT),
        timer=1,
    )
    gem = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=0, item_type=int(ItemType.GEM), short_descr="shiny gem"),
        timer=0,
    )
    chest.contained_items.append(gem)
    gem.in_obj = chest

    room.contents.append(chest)
    chest.in_room = room
    object_registry.extend([chest, gem])

    obj_update()

    assert chest not in object_registry
    assert chest not in room.contents
    assert gem in room.contents
    assert gem.in_room is room
    assert "Drifting chest flickers and vanishes, spilling its contents on the floor." in observer.messages
