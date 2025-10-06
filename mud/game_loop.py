from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum

from mud.affects.engine import tick_spell_effects
from mud.ai import aggressive_update, mobile_update
from mud.characters.conditions import gain_condition
from mud.combat.engine import update_pos
from mud.config import get_pulse_area, get_pulse_music, get_pulse_tick, get_pulse_violence
from mud.imc import pump_idle
from mud.math.c_compat import c_div
from mud.admin_logging.admin import rotate_admin_log
from mud.models.character import Character, character_registry
from mud.models.constants import (
    AffectFlag,
    Condition,
    ItemType,
    Position,
    Size,
    Stat,
    WearFlag,
    WearLocation,
    LEVEL_IMMORTAL,
    ROOM_VNUM_LIMBO,
)
from mud.models.obj import ObjectData, object_registry
from mud.models.room import room_registry
from mud.net.protocol import broadcast_global
from mud.music import song_update
from mud.skills.registry import skill_registry
from mud.spawning.reset_handler import reset_tick
from mud.spec_funs import run_npc_specs
from mud.time import time_info
from mud.utils import rng_mm


class SkyState(IntEnum):
    """ROM sky states for weather updates."""

    CLOUDLESS = 0
    CLOUDY = 1
    RAINING = 2
    LIGHTNING = 3


@dataclass
class WeatherState:
    """ROM-style weather state tracking pressure and sky."""

    sky: SkyState
    mmhg: int
    change: int


def _seed_weather_state() -> WeatherState:
    """Mirror ROM boot-time weather seeding from db.c."""

    mmhg = 960
    if 7 <= time_info.month <= 12:
        mmhg += rng_mm.number_range(1, 50)
    else:
        mmhg += rng_mm.number_range(1, 80)

    if mmhg <= 980:
        sky = SkyState.LIGHTNING
    elif mmhg <= 1000:
        sky = SkyState.RAINING
    elif mmhg <= 1020:
        sky = SkyState.CLOUDY
    else:
        sky = SkyState.CLOUDLESS

    return WeatherState(sky=sky, mmhg=mmhg, change=0)


weather = _seed_weather_state()


@dataclass
class TimedEvent:
    ticks: int
    callback: Callable[[], None]


events: list[TimedEvent] = []


def schedule_event(ticks: int, callback: Callable[[], None]) -> None:
    """Schedule a callback to run after a number of ticks."""
    events.append(TimedEvent(ticks, callback))


def event_tick() -> None:
    """Advance timers and fire ready callbacks."""
    for ev in events[:]:
        ev.ticks -= 1
        if ev.ticks <= 0:
            ev.callback()
            events.remove(ev)


_CLASS_TABLE = {
    0: {"hp_max": 8, "f_mana": True},
    1: {"hp_max": 10, "f_mana": True},
    2: {"hp_max": 13, "f_mana": False},
    3: {"hp_max": 15, "f_mana": False},
}


def _get_class_entry(character: Character) -> dict[str, int | bool]:
    index = int(getattr(character, "ch_class", 0) or 0)
    return _CLASS_TABLE.get(index, {"hp_max": 10, "f_mana": False})


def _has_affect(character: Character, flag: AffectFlag) -> bool:
    if hasattr(character, "has_affect"):
        try:
            return bool(character.has_affect(flag))
        except Exception:
            return False
    affected = int(getattr(character, "affected_by", 0) or 0)
    return bool(affected & int(flag))


def _get_skill_percent(character: Character, skill_name: str) -> int:
    skills = getattr(character, "skills", {}) or {}
    if not isinstance(skills, dict):
        return 0
    direct = skills.get(skill_name)
    if direct is None:
        direct = skills.get(skill_name.lower())
    try:
        return int(direct or 0)
    except (TypeError, ValueError):
        return 0


def hit_gain(character: Character) -> int:
    """Mirror ROM hit_gain calculations using available character data."""

    room = getattr(character, "room", None)
    if room is None:
        return 0

    level = max(0, int(getattr(character, "level", 0) or 0))
    gain = 0

    if getattr(character, "is_npc", False):
        gain = 5 + level
        if _has_affect(character, AffectFlag.REGENERATION):
            gain *= 2
        position = Position(int(getattr(character, "position", Position.STANDING)))
        if position == Position.SLEEPING:
            gain = gain * 3 // 2
        elif position == Position.FIGHTING:
            gain = gain // 3
        elif position != Position.RESTING:
            gain = gain // 2
    else:
        con = character.get_curr_stat(Stat.CON) or 0
        gain = max(3, con - 3 + c_div(level, 2))
        gain += _get_class_entry(character)["hp_max"] - 10

        roll = rng_mm.number_percent()
        fast_healing = _get_skill_percent(character, "fast healing")
        if roll < fast_healing:
            gain += roll * gain // 100
            if getattr(character, "hit", 0) < getattr(character, "max_hit", 0):
                skill_registry.check_improve(character, "fast healing", True, 8)

        position = Position(int(getattr(character, "position", Position.STANDING)))
        if position == Position.SLEEPING:
            pass
        elif position == Position.RESTING:
            gain //= 2
        elif position == Position.FIGHTING:
            gain //= 6
        else:
            gain //= 4

        if getattr(character.pcdata, "condition", None):
            if character.pcdata.condition[Condition.HUNGER] == 0:
                gain //= 2
            if character.pcdata.condition[Condition.THIRST] == 0:
                gain //= 2

    gain = gain * getattr(room, "heal_rate", 100) // 100

    furniture = getattr(character, "on", None)
    if furniture is not None and getattr(furniture, "item_type", None) == ItemType.FURNITURE:
        values = getattr(furniture, "value", [100, 100, 100, 100, 100])
        if len(values) > 3:
            gain = gain * int(values[3]) // 100

    if _has_affect(character, AffectFlag.POISON):
        gain //= 4
    if _has_affect(character, AffectFlag.PLAGUE):
        gain //= 8
    if _has_affect(character, AffectFlag.HASTE) or _has_affect(character, AffectFlag.SLOW):
        gain //= 2

    deficit = max(0, int(getattr(character, "max_hit", 0)) - int(getattr(character, "hit", 0)))
    return max(0, min(gain, deficit))


def mana_gain(character: Character) -> int:
    room = getattr(character, "room", None)
    if room is None:
        return 0

    level = max(0, int(getattr(character, "level", 0) or 0))
    gain = 0

    if getattr(character, "is_npc", False):
        gain = 5 + level
        position = Position(int(getattr(character, "position", Position.STANDING)))
        if position == Position.SLEEPING:
            gain = gain * 3 // 2
        elif position == Position.FIGHTING:
            gain //= 3
        elif position != Position.RESTING:
            gain //= 2
    else:
        wis = character.get_curr_stat(Stat.WIS) or 0
        intelligence = character.get_curr_stat(Stat.INT) or 0
        gain = (wis + intelligence + level) // 2

        roll = rng_mm.number_percent()
        meditation = _get_skill_percent(character, "meditation")
        if roll < meditation:
            gain += roll * gain // 100
            if getattr(character, "mana", 0) < getattr(character, "max_mana", 0):
                skill_registry.check_improve(character, "meditation", True, 8)

        if not _get_class_entry(character)["f_mana"]:
            gain //= 2

        position = Position(int(getattr(character, "position", Position.STANDING)))
        if position == Position.SLEEPING:
            pass
        elif position == Position.RESTING:
            gain //= 2
        elif position == Position.FIGHTING:
            gain //= 6
        else:
            gain //= 4

        if getattr(character.pcdata, "condition", None):
            if character.pcdata.condition[Condition.HUNGER] == 0:
                gain //= 2
            if character.pcdata.condition[Condition.THIRST] == 0:
                gain //= 2

    gain = gain * getattr(room, "mana_rate", 100) // 100

    furniture = getattr(character, "on", None)
    if furniture is not None and getattr(furniture, "item_type", None) == ItemType.FURNITURE:
        values = getattr(furniture, "value", [100, 100, 100, 100, 100])
        if len(values) > 4:
            gain = gain * int(values[4]) // 100

    if _has_affect(character, AffectFlag.POISON):
        gain //= 4
    if _has_affect(character, AffectFlag.PLAGUE):
        gain //= 8
    if _has_affect(character, AffectFlag.HASTE) or _has_affect(character, AffectFlag.SLOW):
        gain //= 2

    deficit = max(0, int(getattr(character, "max_mana", 0)) - int(getattr(character, "mana", 0)))
    return max(0, min(gain, deficit))


def move_gain(character: Character) -> int:
    room = getattr(character, "room", None)
    if room is None:
        return 0

    level = max(0, int(getattr(character, "level", 0) or 0))

    if getattr(character, "is_npc", False):
        gain = level
    else:
        gain = max(15, level)
        position = Position(int(getattr(character, "position", Position.STANDING)))
        if position == Position.SLEEPING:
            gain += character.get_curr_stat(Stat.DEX) or 0
        elif position == Position.RESTING:
            gain += (character.get_curr_stat(Stat.DEX) or 0) // 2

        if getattr(character.pcdata, "condition", None):
            if character.pcdata.condition[Condition.HUNGER] == 0:
                gain //= 2
            if character.pcdata.condition[Condition.THIRST] == 0:
                gain //= 2

    gain = gain * getattr(room, "heal_rate", 100) // 100

    furniture = getattr(character, "on", None)
    if furniture is not None and getattr(furniture, "item_type", None) == ItemType.FURNITURE:
        values = getattr(furniture, "value", [100, 100, 100, 100, 100])
        if len(values) > 3:
            gain = gain * int(values[3]) // 100

    if _has_affect(character, AffectFlag.POISON):
        gain //= 4
    if _has_affect(character, AffectFlag.PLAGUE):
        gain //= 8
    if _has_affect(character, AffectFlag.HASTE) or _has_affect(character, AffectFlag.SLOW):
        gain //= 2

    deficit = max(0, int(getattr(character, "max_move", 0)) - int(getattr(character, "move", 0)))
    return max(0, min(gain, deficit))


def _send_to_char(character: Character, message: str) -> None:
    messages = getattr(character, "messages", None)
    if isinstance(messages, list):
        messages.append(message)


def _message_room(room, message: str, exclude: Character | None = None) -> None:
    if room is None:
        return

    if hasattr(room, "broadcast"):
        room.broadcast(message, exclude=exclude)
        return

    for occupant in getattr(room, "people", []):
        if occupant is exclude:
            continue
        _send_to_char(occupant, message)


def _apply_regeneration(character: Character) -> None:
    hit = hit_gain(character)
    if hit:
        character.hit = min(int(getattr(character, "max_hit", 0)), int(getattr(character, "hit", 0)) + hit)

    mana = mana_gain(character)
    if mana:
        character.mana = min(int(getattr(character, "max_mana", 0)), int(getattr(character, "mana", 0)) + mana)

    move = move_gain(character)
    if move:
        character.move = min(int(getattr(character, "max_move", 0)), int(getattr(character, "move", 0)) + move)

    skill_registry.tick(character)


def _idle_to_limbo(character: Character) -> None:
    room = getattr(character, "room", None)
    if room is None:
        return

    if getattr(character, "was_in_room", None) is None:
        character.was_in_room = room

    if getattr(character, "fighting", None) is not None:
        character.fighting = None

    name = getattr(character, "name", None) or "Someone"
    _message_room(room, f"{name} disappears into the void.", exclude=character)
    _send_to_char(character, "You disappear into the void.")
    room.remove_character(character)

    limbo = room_registry.get(ROOM_VNUM_LIMBO)
    if limbo is not None:
        limbo.add_character(character)


def char_update() -> None:
    """Port of ROM's char_update: regen, conditions, idle handling."""

    for character in list(character_registry):
        position = Position(int(getattr(character, "position", Position.STANDING)))
        if position >= Position.STUNNED:
            _apply_regeneration(character)

        if position == Position.STUNNED:
            update_pos(character)

        for message in tick_spell_effects(character):
            _send_to_char(character, message)

        if getattr(character, "is_npc", False):
            continue

        level = int(getattr(character, "level", 0) or 0)
        if level >= LEVEL_IMMORTAL:
            character.timer = 0
            continue

        size = Size(int(getattr(character, "size", Size.MEDIUM) or Size.MEDIUM))
        hunger_delta = -2 if size > Size.MEDIUM else -1
        full_delta = -4 if size > Size.MEDIUM else -2

        gain_condition(character, Condition.DRUNK, -1)
        gain_condition(character, Condition.FULL, full_delta)
        gain_condition(character, Condition.THIRST, -1)
        gain_condition(character, Condition.HUNGER, hunger_delta)

        descriptor = getattr(character, "desc", None) or getattr(character, "connection", None)
        if descriptor is not None:
            character.timer = 0
            continue

        character.timer = int(getattr(character, "timer", 0) or 0) + 1
        if character.timer >= 12:
            _idle_to_limbo(character)


def _render_obj_message(obj: ObjectData, template: str) -> str:
    short_descr = getattr(obj, "short_descr", None) or getattr(obj, "name", None) or "object"
    return template.replace("$p", str(short_descr))


def _remove_from_character(obj: ObjectData, character: Character) -> None:
    inventory = getattr(character, "inventory", None)
    if isinstance(inventory, list) and obj in inventory:
        inventory.remove(obj)

    equipment = getattr(character, "equipment", None)
    if isinstance(equipment, dict):
        for slot, equipped in list(equipment.items()):
            if equipped is obj:
                del equipment[slot]

    obj.carried_by = None


def _obj_to_room(obj: ObjectData, room) -> None:
    if hasattr(room, "add_object"):
        room.add_object(obj)
    else:
        contents = getattr(room, "contents", None)
        if isinstance(contents, list) and obj not in contents:
            contents.append(obj)
    obj.in_room = room
    obj.carried_by = None
    obj.in_obj = None


def _obj_to_char(obj: ObjectData, character: Character) -> None:
    inventory = getattr(character, "inventory", None)
    if isinstance(inventory, list) and obj not in inventory:
        inventory.append(obj)
    obj.carried_by = character
    obj.in_room = None
    obj.in_obj = None


def _obj_to_obj(obj: ObjectData, container: ObjectData) -> None:
    contents = getattr(container, "contains", None)
    if isinstance(contents, list):
        contents.append(obj)
    obj.in_obj = container
    obj.in_room = None
    obj.carried_by = None


def _obj_from_obj(obj: ObjectData) -> None:
    container = getattr(obj, "in_obj", None)
    if container is None:
        return

    contents = getattr(container, "contains", None)
    if isinstance(contents, list) and obj in contents:
        contents.remove(obj)
    obj.in_obj = None


def _extract_obj(obj: ObjectData) -> None:
    for child in list(getattr(obj, "contains", [])):
        _extract_obj(child)

    carrier = getattr(obj, "carried_by", None)
    if carrier is not None:
        _remove_from_character(obj, carrier)

    room = getattr(obj, "in_room", None)
    if room is not None:
        contents = getattr(room, "contents", None)
        if isinstance(contents, list) and obj in contents:
            contents.remove(obj)
        obj.in_room = None

    container = getattr(obj, "in_obj", None)
    if container is not None:
        contents = getattr(container, "contains", None)
        if isinstance(contents, list) and obj in contents:
            contents.remove(obj)
        obj.in_obj = None

    if obj in object_registry:
        object_registry.remove(obj)


def _object_decay_message(obj: ObjectData) -> str:
    item_type = getattr(obj, "item_type", None)
    if item_type == ItemType.FOUNTAIN:
        return "$p dries up."
    if item_type in (ItemType.CORPSE_NPC, ItemType.CORPSE_PC):
        return "$p decays into dust."
    if item_type == ItemType.FOOD:
        return "$p decomposes."
    if item_type == ItemType.POTION:
        return "$p has evaporated from disuse."
    if item_type == ItemType.PORTAL:
        return "$p fades out of existence."
    if item_type == ItemType.CONTAINER:
        wear_flags = int(getattr(obj, "wear_flags", 0) or 0)
        if wear_flags & int(WearFlag.WEAR_FLOAT):
            if getattr(obj, "contains", []):
                return "$p flickers and vanishes, spilling its contents on the floor."
            return "$p flickers and vanishes."
    return "$p crumbles into dust."


def _broadcast_decay(obj: ObjectData, message: str) -> None:
    carrier = getattr(obj, "carried_by", None)
    if carrier is not None:
        if getattr(carrier, "is_npc", False) and getattr(getattr(carrier, "pIndexData", None), "pShop", None) is not None:
            carrier.silver = int(getattr(carrier, "silver", 0)) + int(getattr(obj, "cost", 0)) // 5
        else:
            _send_to_char(carrier, message)
            if int(getattr(obj, "wear_loc", -1)) == int(WearLocation.FLOAT):
                _message_room(getattr(carrier, "room", None), message, exclude=carrier)
        return

    room = getattr(obj, "in_room", None)
    if room is not None:
        _message_room(room, message)


def _spill_contents(obj: ObjectData) -> None:
    for item in list(getattr(obj, "contains", [])):
        _obj_from_obj(item)
        if getattr(obj, "in_obj", None) is not None:
            _obj_to_obj(item, obj.in_obj)
        elif getattr(obj, "carried_by", None) is not None:
            carrier = obj.carried_by
            if int(getattr(obj, "wear_loc", -1)) == int(WearLocation.FLOAT):
                room = getattr(carrier, "room", None)
                if room is None:
                    _extract_obj(item)
                else:
                    _obj_to_room(item, room)
            else:
                _obj_to_char(item, carrier)
        elif getattr(obj, "in_room", None) is not None:
            _obj_to_room(item, obj.in_room)
        else:
            _extract_obj(item)


def _tick_object_affects(obj: ObjectData) -> None:
    affects = getattr(obj, "affected", None)
    if not affects:
        return
    for affect in list(affects):
        duration = int(getattr(affect, "duration", 0) or 0)
        if duration > 0:
            affect.duration = duration - 1
        elif duration == 0:
            affects.remove(affect)


def obj_update() -> None:
    """Port ROM obj_update timers, decay messaging, and spills."""

    for obj in list(object_registry):
        _tick_object_affects(obj)

        timer = int(getattr(obj, "timer", 0) or 0)
        if timer <= 0:
            continue

        obj.timer = timer - 1
        if obj.timer > 0:
            continue

        message = _render_obj_message(obj, _object_decay_message(obj))
        _broadcast_decay(obj, message)

        should_spill = False
        if getattr(obj, "contains", []):
            if getattr(obj, "item_type", None) == ItemType.CORPSE_PC:
                should_spill = True
            elif int(getattr(obj, "wear_loc", -1)) == int(WearLocation.FLOAT):
                should_spill = True
            elif (
                getattr(obj, "item_type", None) == ItemType.CONTAINER
                and int(getattr(obj, "wear_flags", 0) or 0) & int(WearFlag.WEAR_FLOAT)
            ):
                should_spill = True

        if should_spill:
            _spill_contents(obj)

        _extract_obj(obj)


def weather_tick() -> None:
    """Update barometric pressure and sky state like ROM weather_update."""

    if 9 <= time_info.month <= 16:
        diff = -2 if weather.mmhg > 985 else 2
    else:
        diff = -2 if weather.mmhg > 1015 else 2

    weather.change += diff * rng_mm.dice(1, 4)
    weather.change += rng_mm.dice(2, 6)
    weather.change -= rng_mm.dice(2, 6)
    weather.change = max(-12, min(weather.change, 12))

    weather.mmhg += weather.change
    weather.mmhg = max(960, min(weather.mmhg, 1040))

    if weather.sky == SkyState.CLOUDLESS:
        if weather.mmhg < 990 or (
            weather.mmhg < 1010 and rng_mm.number_bits(2) == 0
        ):
            weather.sky = SkyState.CLOUDY
    elif weather.sky == SkyState.CLOUDY:
        if weather.mmhg < 970 or (
            weather.mmhg < 990 and rng_mm.number_bits(2) == 0
        ):
            weather.sky = SkyState.RAINING
        elif weather.mmhg > 1030 and rng_mm.number_bits(2) == 0:
            weather.sky = SkyState.CLOUDLESS
    elif weather.sky == SkyState.RAINING:
        if weather.mmhg < 970 and rng_mm.number_bits(2) == 0:
            weather.sky = SkyState.LIGHTNING
        elif weather.mmhg > 1030 or (
            weather.mmhg > 1010 and rng_mm.number_bits(2) == 0
        ):
            weather.sky = SkyState.CLOUDY
    elif weather.sky == SkyState.LIGHTNING:
        if weather.mmhg > 1010 or (
            weather.mmhg > 990 and rng_mm.number_bits(2) == 0
        ):
            weather.sky = SkyState.RAINING
    else:
        weather.sky = SkyState.CLOUDLESS


def time_tick() -> None:
    """Advance world time and broadcast day/night transitions."""
    messages = time_info.advance_hour()
    if time_info.hour == 0:
        try:
            rotate_admin_log()
        except Exception:
            pass
    for message in messages:
        broadcast_global(message, channel="info")


_pulse_counter = 0
# Countdown counters mirror ROM's --pulse_X <= 0 semantics so cadence shifts
# (e.g., TIME_SCALE changes) take effect immediately after the next pulse.
_point_counter = get_pulse_tick()
_violence_counter = get_pulse_violence()
_area_counter = get_pulse_area()
_music_counter = get_pulse_music()


def violence_tick() -> None:
    """Consume wait/daze counters once per pulse for all characters."""

    for ch in list(character_registry):
        wait = int(getattr(ch, "wait", 0) or 0)
        if wait > 0:
            ch.wait = wait - 1
        else:
            ch.wait = 0

        if hasattr(ch, "daze"):
            daze = int(getattr(ch, "daze", 0) or 0)
            if daze > 0:
                ch.daze = daze - 1
            else:
                ch.daze = max(0, daze)


def game_tick() -> None:
    """Run a full game tick: time, regen, weather, timed events, and resets."""
    global _pulse_counter, _point_counter, _violence_counter, _area_counter, _music_counter
    _pulse_counter += 1

    # Consume wait/daze every pulse before evaluating cadence counters.
    violence_tick()

    # Track pulses for future violence update hooks (combat rounds, etc.).
    _violence_counter -= 1
    if _violence_counter <= 0:
        _violence_counter = get_pulse_violence()

    # Point pulses drive time/weather/regen updates.
    _point_counter -= 1
    point_pulse = _point_counter <= 0
    if point_pulse:
        _point_counter = get_pulse_tick()
        time_tick()
        weather_tick()
        char_update()
        obj_update()
        pump_idle()

    _area_counter -= 1
    if _area_counter <= 0:
        _area_counter = get_pulse_area()
        reset_tick()
    _music_counter -= 1
    if _music_counter <= 0:
        _music_counter = get_pulse_music()
        song_update()
    event_tick()
    mobile_update()
    aggressive_update()
    # Invoke NPC special functions after resets to mirror ROM's update cadence
    run_npc_specs()
