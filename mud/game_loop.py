from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum

from mud.account.account_manager import save_character
from mud.admin_logging.admin import rotate_admin_log
from mud.affects.engine import tick_spell_effects
from mud.ai import aggressive_update, mobile_update
from mud.characters.conditions import gain_condition
from mud.combat.engine import update_pos
from mud.config import get_pulse_area, get_pulse_music, get_pulse_tick, get_pulse_violence
from mud.imc import pump_idle
from mud.math.c_compat import c_div
from mud.models.character import Character, character_registry
from mud.models.constants import (
    LEVEL_IMMORTAL,
    ROOM_VNUM_LIMBO,
    AffectFlag,
    Condition,
    ItemType,
    Position,
    RoomFlag,
    Size,
    Stat,
    WearFlag,
    WearLocation,
)
from mud.models.obj import ObjectData, object_registry
from mud.models.room import room_registry
from mud.music import song_update
from mud.net.protocol import broadcast_global
from mud.skills.registry import skill_registry
from mud.spawning.reset_handler import reset_tick
from mud.spec_funs import run_npc_specs
from mud.time import time_info
from mud.utils import rng_mm

_AUTOSAVE_ROTATION = 0
_AUTOSAVE_WINDOW = 30


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

# Track boot time for do_time command (ROM C: extern char str_boot_time[])
# Initialized at module load time (when server starts)
from datetime import datetime

boot_time = datetime.now()

_TO_OBJECT = 1
_TO_WEAPON = 2


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
    if furniture is not None:
        item_type = getattr(furniture.prototype, "item_type", None)
        if item_type == ItemType.FURNITURE or item_type == int(ItemType.FURNITURE):
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

    # ROM src/update.c:297 — mana uses mana_rate, not heal_rate
    gain = gain * getattr(room, "mana_rate", 100) // 100

    furniture = getattr(character, "on", None)
    if furniture is not None:
        item_type = getattr(furniture.prototype, "item_type", None)
        if item_type == ItemType.FURNITURE or item_type == int(ItemType.FURNITURE):
            values = getattr(furniture, "value", [100, 100, 100, 100, 100])
            # ROM src/update.c:300 — mana furniture bonus uses value[4], not value[3]
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
    if furniture is not None:
        item_type = getattr(furniture.prototype, "item_type", None)
        if item_type == ItemType.FURNITURE or item_type == int(ItemType.FURNITURE):
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
    """Deliver a message to a character, mirroring ROM C write_to_buffer."""
    writer = getattr(character, "connection", None)
    if writer is not None:
        from mud.net.protocol import send_to_char as _send

        asyncio.create_task(_send(character, message))
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


def _find_equipped_light(character: Character) -> tuple[object | None, object | None]:
    """Locate the descriptor slot and object for a worn light."""

    equipment = getattr(character, "equipment", None)
    if not isinstance(equipment, dict) or not equipment:
        return None, None

    for slot, obj in equipment.items():
        if isinstance(slot, str):
            if slot.strip().lower() in {"light", WearLocation.LIGHT.name.lower()}:
                return slot, obj
        else:
            try:
                if int(slot) == int(WearLocation.LIGHT):
                    return slot, obj
            except (TypeError, ValueError):  # pragma: no cover - defensive guard
                continue
    return None, None


def _is_light_object(obj: object) -> bool:
    item_type = getattr(obj, "item_type", None)
    if item_type is None:
        return False
    try:
        return int(item_type) == int(ItemType.LIGHT)
    except (TypeError, ValueError):
        if isinstance(item_type, str):
            return item_type.lower() == "light"
        return False


def _get_light_remaining(obj: object) -> int:
    values = getattr(obj, "value", None)
    if isinstance(values, list) and len(values) > 2:
        try:
            return int(values[2])
        except (TypeError, ValueError):
            return 0
    if isinstance(values, tuple) and len(values) > 2:
        try:
            return int(values[2])
        except (TypeError, ValueError):
            return 0
    return 0


def _set_light_remaining(obj: object, remaining: int) -> None:
    values = getattr(obj, "value", None)
    if isinstance(values, list):
        while len(values) <= 2:
            values.append(0)
        values[2] = remaining
        return
    if isinstance(values, tuple):
        updated = list(values)
        while len(updated) <= 2:
            updated.append(0)
        updated[2] = remaining
        obj.value = updated


def _destroy_light(character: Character, slot_key: object | None, obj: object) -> None:
    equipment = getattr(character, "equipment", None)
    if isinstance(equipment, dict):
        for slot, equipped in list(equipment.items()):
            if equipped is obj or slot == slot_key:
                del equipment[slot]
                break

    if hasattr(obj, "pIndexData"):
        _extract_obj(obj)  # type: ignore[arg-type]
        return

    try:
        weight = getattr(getattr(obj, "prototype", None), "weight", 0) or getattr(obj, "weight", 0)
        if weight:
            current_weight = int(getattr(character, "carry_weight", 0) or 0)
            character.carry_weight = max(0, current_weight - int(weight))
    except Exception:  # pragma: no cover - defensive guard
        pass

    try:
        current_number = int(getattr(character, "carry_number", 0) or 0)
        if current_number > 0:
            character.carry_number = current_number - 1
    except Exception:  # pragma: no cover - defensive guard
        pass


def _decay_worn_light(character: Character) -> None:
    slot_key, light = _find_equipped_light(character)
    if light is None or not _is_light_object(light):
        return

    remaining = _get_light_remaining(light)
    if remaining <= 0:
        return

    new_remaining = remaining - 1
    _set_light_remaining(light, new_remaining)

    room = getattr(character, "room", None)
    if new_remaining <= 0:
        if room is not None:
            current_light = int(getattr(room, "light", 0) or 0)
            room.light = max(0, current_light - 1)
            _message_room(room, _render_obj_message(light, "$p goes out."), exclude=character)
            _send_to_char(character, _render_obj_message(light, "$p flickers and goes out."))
        else:
            _send_to_char(character, _render_obj_message(light, "$p flickers and goes out."))
        _destroy_light(character, slot_key, light)
    elif new_remaining <= 5 and room is not None:
        _send_to_char(character, _render_obj_message(light, "$p flickers."))


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

    if getattr(room, "vnum", None) == ROOM_VNUM_LIMBO:
        return

    if getattr(character, "was_in_room", None) is None:
        character.was_in_room = room

    # ROM src/update.c:741-744 — stop_fighting(ch, TRUE) to clean both sides
    if getattr(character, "fighting", None) is not None:
        from mud.combat.engine import stop_fighting
        stop_fighting(character, both=True)

    if int(getattr(character, "level", 0) or 0) > 1:
        try:
            save_character(character)
        except Exception:  # pragma: no cover - defensive safeguard
            pass

    name = getattr(character, "name", None) or "Someone"
    _message_room(room, f"{name} disappears into the void.", exclude=character)
    _send_to_char(character, "You disappear into the void.")
    room.remove_character(character)

    limbo = room_registry.get(ROOM_VNUM_LIMBO)
    if limbo is not None:
        limbo.add_character(character)


def _auto_quit_character(character: Character) -> None:
    try:
        save_character(character)
    except Exception:  # pragma: no cover - defensive safeguard
        pass

    room = getattr(character, "room", None)
    if room is not None:
        remover = getattr(room, "remove_character", None)
        if callable(remover):
            remover(character)
        else:
            occupants = getattr(room, "people", None)
            if occupants and character in occupants:
                occupants.remove(character)
        character.room = None

    try:
        character_registry.remove(character)
    except ValueError:
        pass

    try:
        character.was_in_room = None
    except Exception:
        pass


def _char_update_tick_effects(character: Character) -> bool:
    """Apply per-tick affect damage (plague, poison, incap, mortal).

    Mirrors ROM src/update.c:char_update lines 793-871.
    Returns True if character was extracted (caller must skip remaining processing).
    """
    from mud.combat.engine import apply_damage as _damage
    from mud.models.constants import DamageType

    # Plague tick — ROM src/update.c:794-846
    if _has_affect(character, AffectFlag.PLAGUE):
        room = getattr(character, "room", None)
        if room is None:
            return False

        _message_room(room, f"{getattr(character, 'name', 'Someone')} writhes in agony as plague sores erupt from their skin.")
        _send_to_char(character, "You writhe in agony from the plague.\r\n")

        # Find the plague affect to get its level
        affects = getattr(character, "affected", None) or []
        plague_af = None
        for af in affects:
            spell_name = getattr(af, "type", None) or getattr(af, "spell_name", None)
            if spell_name == "plague":
                plague_af = af
                break

        if plague_af is None:
            # Bit set but no affect entry — clear the flag
            affected_by = int(getattr(character, "affected_by", 0) or 0)
            character.affected_by = affected_by & ~int(AffectFlag.PLAGUE)
        else:
            af_level = int(getattr(plague_af, "level", 1) or 1)
            if af_level > 1:
                # Spread to room occupants — ROM src/update.c:828-841
                spread_level = af_level - 1
                for vch in list(getattr(room, "people", [])):
                    if vch is character:
                        continue
                    if _has_affect(vch, AffectFlag.PLAGUE):
                        continue
                    if int(getattr(vch, "level", 0) or 0) >= LEVEL_IMMORTAL:
                        continue
                    if rng_mm.number_bits(4) != 0:
                        continue
                    # saves_spell check — simplified: use level check
                    from mud.affects.saves import saves_spell
                    from mud.models.constants import DamageType
                    if saves_spell(spread_level - 2, vch, int(DamageType.DISEASE)):
                        continue
                    _send_to_char(vch, "You feel hot and feverish.\r\n")
                    _message_room(room, f"{getattr(vch, 'name', 'Someone')} shivers and looks very ill.", exclude=vch)
                    if hasattr(vch, "add_affect"):
                        from mud.models.character import AffectData
                        new_af = AffectData(
                            type="plague",
                            level=spread_level,
                            duration=rng_mm.number_range(1, 2 * spread_level),
                            location="str",
                            modifier=-5,
                            bitvector=int(AffectFlag.PLAGUE),
                        )
                        vch.add_affect(new_af)

            # Drain mana and move — ROM src/update.c:843-845
            dam = min(int(getattr(character, "level", 1) or 1), af_level // 5 + 1)
            character.mana = max(0, int(getattr(character, "mana", 0) or 0) - dam)
            character.move = max(0, int(getattr(character, "move", 0) or 0) - dam)
            try:
                _damage(character, character, dam, int(DamageType.DISEASE))
            except Exception:
                pass
        return False

    # Poison tick — ROM src/update.c:848-862
    if _has_affect(character, AffectFlag.POISON) and not _has_affect(character, AffectFlag.SLOW):
        affects = getattr(character, "affected", None) or []
        poison_af = None
        for af in affects:
            spell_name = getattr(af, "type", None) or getattr(af, "spell_name", None)
            if spell_name == "poison":
                poison_af = af
                break
        if poison_af is not None:
            room = getattr(character, "room", None)
            if room is not None:
                _message_room(room, f"{getattr(character, 'name', 'Someone')} shivers and suffers.", exclude=character)
            _send_to_char(character, "You shiver and suffer.\r\n")
            af_level = int(getattr(poison_af, "level", 1) or 1)
            dam = af_level // 10 + 1
            try:
                _damage(character, character, dam, int(DamageType.POISON))
            except Exception:
                pass
        return False

    # Incapacitated — ROM src/update.c:864-867 — 50% chance of 1 damage
    pos = Position(int(getattr(character, "position", Position.STANDING)))
    if pos == Position.INCAP and rng_mm.number_range(0, 1) == 0:
        try:
            _damage(character, character, 1, int(DamageType.NONE) if hasattr(DamageType, "NONE") else 0)
        except Exception:
            pass
        return False

    # Mortal — ROM src/update.c:868-871 — 1 damage every tick
    if pos == Position.MORTAL:
        try:
            _damage(character, character, 1, int(DamageType.NONE) if hasattr(DamageType, "NONE") else 0)
        except Exception:
            pass

    return False


def char_update() -> None:
    """Port of ROM's char_update: regen, conditions, idle handling.

    Mirrors ROM src/update.c:char_update.
    """
    global _AUTOSAVE_ROTATION
    _AUTOSAVE_ROTATION = (_AUTOSAVE_ROTATION + 1) % _AUTOSAVE_WINDOW

    autosave_candidates: list[Character] = []
    autoquit_candidates: list[Character] = []

    for character in list(character_registry):
        position = Position(int(getattr(character, "position", Position.STANDING)))
        if position >= Position.STUNNED:
            # GL-009: NPC wanders home — ROM src/update.c:688-696
            # If an NPC is outside its home zone and not fighting/charmed,
            # 5% chance per tick to be extracted (despawned).
            if getattr(character, "is_npc", False):
                room = getattr(character, "room", None)
                ch_zone = getattr(character, "zone", None)
                if (
                    ch_zone is not None
                    and room is not None
                    and getattr(room, "area", None) is not ch_zone
                    and getattr(character, "desc", None) is None
                    and getattr(character, "fighting", None) is None
                    and not _has_affect(character, AffectFlag.CHARM)
                    and rng_mm.number_percent() < 5
                ):
                    from mud.mob_cmds import _extract_character
                    _message_room(room, f"{getattr(character, 'name', 'Someone')} wanders on home.")
                    _extract_character(character, fPull=True)
                    continue

            _apply_regeneration(character)

        if position == Position.STUNNED:
            update_pos(character)

        # Spell affect duration ticks (wear-off messages)
        for message in tick_spell_effects(character):
            _send_to_char(character, message)

        # Per-tick damage effects: plague, poison, incap, mortal (GL-011..GL-014)
        # ROM src/update.c:793-871
        _char_update_tick_effects(character)

        if getattr(character, "is_npc", False):
            continue

        level = int(getattr(character, "level", 0) or 0)
        if level < LEVEL_IMMORTAL:
            _decay_worn_light(character)
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

        descriptor = getattr(character, "desc", None)
        if descriptor is not None:
            character.timer = 0
            descriptor_id = getattr(descriptor, "descriptor_id", None)
            if descriptor_id is None:
                descriptor_id = id(descriptor)
            if descriptor_id % _AUTOSAVE_WINDOW == _AUTOSAVE_ROTATION:
                autosave_candidates.append(character)
            continue

        character.timer = int(getattr(character, "timer", 0) or 0) + 1
        if (
            character.timer >= 12
            and getattr(character, "was_in_room", None) is None
            and getattr(character, "room", None) is not None
        ):
            _idle_to_limbo(character)
        if character.timer > 30:
            autoquit_candidates.append(character)

    for candidate in autosave_candidates:
        try:
            save_character(candidate)
        except Exception:  # pragma: no cover - defensive safeguard
            pass

    for candidate in autoquit_candidates:
        _auto_quit_character(candidate)


def _render_obj_message(obj: ObjectData, template: str) -> str:
    short_descr = (
        getattr(obj, "short_descr", None)
        or getattr(obj, "name", None)
        or getattr(getattr(obj, "prototype", None), "short_descr", None)
        or "object"
    )
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


def _get_weight_mult(obj: ObjectData) -> int:
    """Get container weight multiplier (WEIGHT_MULT macro from ROM C handler.c).

    Returns value[4] for containers (weight reduction percentage), 100 otherwise.
    ROM C Reference: handler.c WEIGHT_MULT macro
    """
    from mud.models.constants import ItemType

    # Get item type
    item_type = getattr(obj, "item_type", None)
    if item_type is None:
        proto = getattr(obj, "prototype", None)
        if proto:
            item_type = getattr(proto, "item_type", None)

    # Only containers have weight multipliers
    if item_type != ItemType.CONTAINER:
        return 100

    # Get value[4] (weight multiplier) - prefer instance value, fallback to prototype
    # Get value[4] (weight multiplier) - prefer instance value, fallback to prototype
    # Note: 0 is valid (weightless bag), but [0,0,0,0,0] default means "use prototype"
    values = getattr(obj, "value", None)
    mult = None

    # Check instance value - but only if it's not the default [0,0,0,0,0]
    if values and len(values) >= 5:
        if values != [0, 0, 0, 0, 0] or sum(values) != 0:
            mult = values[4]

    # Fall back to prototype if instance has default values
    if mult is None:
        proto = getattr(obj, "prototype", None)
        if proto:
            proto_values = getattr(proto, "value", None)
            if proto_values and len(proto_values) >= 5:
                mult = proto_values[4]

    try:
        mult_int = int(mult if mult is not None else 100)
        return mult_int if mult_int >= 0 else 100
    except (TypeError, ValueError, IndexError):
        return 100


def _get_obj_number_recursive(obj: ObjectData) -> int:
    """Count how many items recursively (ROM C get_obj_number).

    ROM C Reference: handler.c:2488-2503
    """
    from mud.models.constants import ItemType

    # Get item type
    item_type = getattr(obj, "item_type", None)
    if item_type is None:
        proto = getattr(obj, "prototype", None)
        if proto:
            item_type = getattr(proto, "item_type", None)

    # ROM C: containers, money, gems, jewelry don't count
    if item_type in (ItemType.CONTAINER, ItemType.MONEY, ItemType.GEM):
        number = 0
    else:
        number = 1

    # Add contents recursively (support both Object.contained_items and ObjectData.contains)
    contains = getattr(obj, "contained_items", None) or getattr(obj, "contains", [])
    for contained in contains:
        number += _get_obj_number_recursive(contained)

    return number


def _get_obj_weight_recursive(obj: ObjectData) -> int:
    """Get object weight including contents with WEIGHT_MULT applied.

    ROM C Reference: handler.c:2509-2519 get_obj_weight
    """
    # Get base weight
    weight = getattr(obj, "weight", 0)
    if weight == 0:
        proto = getattr(obj, "prototype", None)
        if proto:
            weight = getattr(proto, "weight", 0)

    # Add contents weight with multiplier (support both Object.contained_items and ObjectData.contains)
    contains = getattr(obj, "contained_items", None) or getattr(obj, "contains", [])
    for contained in contains:
        weight += _get_obj_weight_recursive(contained) * _get_weight_mult(obj) // 100

    return weight


def _obj_to_obj(obj: ObjectData, container: ObjectData) -> None:
    """Add object to container and update carrier weights.

    ROM C Reference: handler.c:1968-1989 obj_to_obj
    """
    # Support both Object.contained_items and ObjectData.contains
    contents = getattr(container, "contained_items", None) or getattr(container, "contains", None)
    if isinstance(contents, list):
        contents.append(obj)
    obj.in_obj = container
    obj.in_room = None
    obj.carried_by = None

    # ROM C handler.c:1978-1986 - Update carrier weights for nested containers
    obj_number = _get_obj_number_recursive(obj)
    obj_weight = _get_obj_weight_recursive(obj)

    current_container = container
    while current_container is not None:
        carrier = getattr(current_container, "carried_by", None)
        if carrier is not None:
            # Update carrier's carry counts
            carry_number = getattr(carrier, "carry_number", 0)
            carry_weight = getattr(carrier, "carry_weight", 0)

            carrier.carry_number = carry_number + obj_number
            carrier.carry_weight = carry_weight + (obj_weight * _get_weight_mult(current_container) // 100)

        # Move up container hierarchy
        current_container = getattr(current_container, "in_obj", None)


def _obj_from_obj(obj: ObjectData) -> None:
    """Remove object from container and update carrier weights.

    ROM C Reference: handler.c:1996-2044 obj_from_obj
    """
    container = getattr(obj, "in_obj", None)
    if container is None:
        return

    # Support both Object.contained_items and ObjectData.contains
    contents = getattr(container, "contained_items", None) or getattr(container, "contains", None)
    if isinstance(contents, list) and obj in contents:
        contents.remove(obj)
    obj.in_obj = None

    # ROM C handler.c:2033-2041 - Update carrier weights for nested containers
    obj_number = _get_obj_number_recursive(obj)
    obj_weight = _get_obj_weight_recursive(obj)

    current_container = container
    while current_container is not None:
        carrier = getattr(current_container, "carried_by", None)
        if carrier is not None:
            # Update carrier's carry counts
            carry_number = getattr(carrier, "carry_number", 0)
            carry_weight = getattr(carrier, "carry_weight", 0)

            carrier.carry_number = carry_number - obj_number
            carrier.carry_weight = carry_weight - (obj_weight * _get_weight_mult(current_container) // 100)

        # Move up container hierarchy
        current_container = getattr(current_container, "in_obj", None)


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
        if (
            getattr(carrier, "is_npc", False)
            and getattr(getattr(carrier, "pIndexData", None), "pShop", None) is not None
        ):
            carrier.silver = int(getattr(carrier, "silver", 0)) + int(getattr(obj, "cost", 0)) // 5
        else:
            _send_to_char(carrier, message)
            if int(getattr(obj, "wear_loc", -1)) == int(WearLocation.FLOAT):
                _message_room(getattr(carrier, "room", None), message, exclude=carrier)
        return

    room = getattr(obj, "in_room", None)
    if room is not None:
        # GL-018: ROM src/update.c:1017-1018 — suppress decay message if obj is
        # inside a pit (vnum 3010) that cannot be taken.
        in_obj = getattr(obj, "in_obj", None)
        if in_obj is not None:
            proto = getattr(in_obj, "pIndexData", None) or getattr(in_obj, "prototype", None)
            in_vnum = int(getattr(proto, "vnum", -1) or -1)
            in_wear = int(getattr(in_obj, "wear_flags", 0) or 0)
            if in_vnum == 3010 and not (in_wear & int(WearFlag.TAKE)):
                return
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


def _resolve_object_room(obj: ObjectData) -> object | None:
    room = getattr(obj, "in_room", None)
    if room is not None:
        return room
    return getattr(obj, "location", None)


def _clear_object_affect(obj: ObjectData, affect) -> None:
    affects = getattr(obj, "affected", None)
    if isinstance(affects, list) and affect in affects:
        affects.remove(affect)

    where = int(getattr(affect, "where", 0) or 0)
    bitvector = int(getattr(affect, "bitvector", 0) or 0)
    if bitvector:
        if where == _TO_OBJECT:
            flags = int(getattr(obj, "extra_flags", 0) or 0)
            obj.extra_flags = flags & ~bitvector
        elif where == _TO_WEAPON:
            values = getattr(obj, "value", None)
            if isinstance(values, list) and len(values) > 4:
                values[4] = int(values[4]) & ~bitvector


def _broadcast_object_wear_off(obj: ObjectData, affect) -> None:
    message: str | None = getattr(affect, "wear_off_message", None)
    if not message:
        spell_name = getattr(affect, "spell_name", None)
        try:
            skill = skill_registry.get(spell_name) if spell_name else None
        except KeyError:
            skill = None
        if skill is not None:
            messages = getattr(skill, "messages", {}) or {}
            message = messages.get("object")
    if not message:
        return

    rendered = _render_obj_message(obj, message)

    carrier = getattr(obj, "carried_by", None)
    if carrier is not None:
        _send_to_char(carrier, rendered)
        _message_room(getattr(carrier, "room", None), rendered, exclude=carrier)
        return

    room = _resolve_object_room(obj)
    _message_room(room, rendered)


def _tick_object_affects(obj: ObjectData) -> None:
    affects = getattr(obj, "affected", None)
    if not affects:
        return

    for affect in list(affects):
        duration = int(getattr(affect, "duration", 0) or 0)
        if duration > 0:
            affect.duration = duration - 1
            level = int(getattr(affect, "level", 0) or 0)
            if level > 0 and rng_mm.number_range(0, 4) == 0:
                affect.level = level - 1
            continue

        if duration < 0:
            continue

        _clear_object_affect(obj, affect)
        _broadcast_object_wear_off(obj, affect)


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
            elif getattr(obj, "item_type", None) == ItemType.CONTAINER and int(
                getattr(obj, "wear_flags", 0) or 0
            ) & int(WearFlag.WEAR_FLOAT):
                should_spill = True

        if should_spill:
            _spill_contents(obj)

        _extract_obj(obj)


def _is_outside(character: Character) -> bool:
    room = getattr(character, "room", None)
    if room is None:
        return False
    flags = int(getattr(room, "room_flags", 0) or 0)
    return not bool(flags & int(RoomFlag.ROOM_INDOORS))


def _should_receive_weather(character: Character) -> bool:
    if not hasattr(character, "is_awake"):
        return False
    if not character.is_awake():
        return False
    return _is_outside(character)


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

    messages: list[str] = []
    if weather.sky == SkyState.CLOUDLESS:
        if weather.mmhg < 990 or (weather.mmhg < 1010 and rng_mm.number_bits(2) == 0):
            weather.sky = SkyState.CLOUDY
            messages.append("The sky is getting cloudy.\r\n")
    elif weather.sky == SkyState.CLOUDY:
        if weather.mmhg < 970 or (weather.mmhg < 990 and rng_mm.number_bits(2) == 0):
            weather.sky = SkyState.RAINING
            messages.append("It starts to rain.\r\n")
        elif weather.mmhg > 1030 and rng_mm.number_bits(2) == 0:
            weather.sky = SkyState.CLOUDLESS
            messages.append("The clouds disappear.\r\n")
    elif weather.sky == SkyState.RAINING:
        if weather.mmhg < 970 and rng_mm.number_bits(2) == 0:
            weather.sky = SkyState.LIGHTNING
            messages.append("Lightning flashes in the sky.\r\n")
        elif weather.mmhg > 1030 or (weather.mmhg > 1010 and rng_mm.number_bits(2) == 0):
            weather.sky = SkyState.CLOUDY
            messages.append("The rain stopped.\r\n")
    elif weather.sky == SkyState.LIGHTNING:
        if weather.mmhg > 1010 or (weather.mmhg > 990 and rng_mm.number_bits(2) == 0):
            weather.sky = SkyState.RAINING
            messages.append("The lightning has stopped.\r\n")
    else:
        weather.sky = SkyState.CLOUDLESS

    for message in messages:
        broadcast_global(message, channel="weather", should_send=_should_receive_weather)


def time_tick() -> None:
    """Advance world time and broadcast day/night transitions."""
    messages = time_info.advance_hour()
    if time_info.hour == 0:
        try:
            rotate_admin_log()
        except Exception:
            pass
    for message in messages:
        broadcast_global(
            message,
            channel="weather",
            should_send=_should_receive_weather,
        )


_pulse_counter = 0
# Countdown counters mirror ROM's --pulse_X <= 0 semantics so cadence shifts
# (e.g., TIME_SCALE changes) take effect immediately after the next pulse.
_point_counter = get_pulse_tick()
_area_counter = get_pulse_area()
_music_counter = get_pulse_music()
_mobile_counter = 0  # Will be initialized on first tick
_violence_counter = 0  # Will be initialized on first tick


def violence_tick(*, do_combat: bool = False) -> None:
    """Process wait/daze counters every pulse, and combat rounds on PULSE_VIOLENCE cadence.

    Mirrors ROM src/fight.c:violence_update — wait/daze decay happens every
    pulse, but multi_hit() (actual combat rounds) only fires when do_combat=True,
    which game_tick() sets on PULSE_VIOLENCE intervals.
    # mirroring ROM src/update.c:update_handler (pulse_violence gate)
    """
    from mud.combat.engine import multi_hit, stop_fighting

    for ch in list(character_registry):
        # Consume wait/daze timers every pulse (ROM behavior)
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

        if not do_combat:
            continue

        # Process combat rounds (ROM src/fight.c:72-96)
        victim = getattr(ch, "fighting", None)
        if victim is None or getattr(ch, "room", None) is None:
            continue

        # If awake and in same room, fight! Otherwise stop fighting
        # Use getattr to support both Character and MobInstance types.
        if (getattr(ch, "position", Position.STANDING) > Position.SLEEPING
                and getattr(ch, "room", None) == getattr(victim, "room", None)):
            multi_hit(ch, victim, dt=None)
        else:
            stop_fighting(ch, both=False)


def game_tick() -> None:
    """Run a full game tick: time, regen, weather, timed events, and resets.

    Order mirrors ROM src/update.c:update_handler exactly:
        area → music → mobile → violence → point(time/weather/char/obj) → aggr
    Python-only additions (event_tick, pump_idle) are inserted at the
    closest logical position without breaking ROM ordering.
    """
    global _pulse_counter, _point_counter, _area_counter, _music_counter, _mobile_counter, _violence_counter
    _pulse_counter += 1

    # Initialize counters on first tick
    if _mobile_counter == 0:
        from mud.config import get_pulse_mobile

        _mobile_counter = get_pulse_mobile()

    if _violence_counter == 0:
        _violence_counter = get_pulse_violence()

    # 1. Area resets — ROM: if (--pulse_area <= 0)
    _area_counter -= 1
    if _area_counter <= 0:
        _area_counter = get_pulse_area()
        reset_tick()

    # 2. Music — ROM: if (--pulse_music <= 0)
    _music_counter -= 1
    if _music_counter <= 0:
        _music_counter = get_pulse_music()
        song_update()

    # 3. Mobile AI + NPC spec_funs — ROM: if (--pulse_mobile <= 0) { mobile_update(); }
    #    spec_fun is called inside mobile_update in ROM src/update.c:408-430.
    _mobile_counter -= 1
    if _mobile_counter <= 0:
        from mud.config import get_pulse_mobile

        _mobile_counter = get_pulse_mobile()
        mobile_update()
        run_npc_specs()

    # 4. Violence (combat rounds) — ROM: if (--pulse_violence <= 0)
    #    wait/daze decrement happens every pulse; multi_hit only on cadence.
    _violence_counter -= 1
    do_combat = _violence_counter <= 0
    if do_combat:
        _violence_counter = get_pulse_violence()
    violence_tick(do_combat=do_combat)

    # 5. Point pulse: time/weather/regen — ROM: if (--pulse_point <= 0)
    _point_counter -= 1
    if _point_counter <= 0:
        _point_counter = get_pulse_tick()
        time_tick()
        weather_tick()
        char_update()
        obj_update()
        pump_idle()

    # 6. Every-pulse housekeeping — ROM: aggr_update(); tail_chain();
    event_tick()
    aggressive_update()


async def async_game_loop() -> None:
    """Background task that drives the game tick continuously.

    Runs at PULSE_PER_SECOND rate (default 4 Hz = 250ms per pulse).
    This is the main heartbeat of the MUD that advances time, processes
    combat, regeneration, weather, resets, and all timed events.

    Mirroring ROM src/update.c:update_handler, this loop never terminates
    except on server shutdown (CancelledError).
    """
    import asyncio

    from mud.config import PULSE_PER_SECOND

    # ROM standard: 4 pulses per second (250ms per pulse)
    tick_interval = 1.0 / PULSE_PER_SECOND

    while True:
        try:
            game_tick()  # Call existing synchronous tick function
            await asyncio.sleep(tick_interval)
        except asyncio.CancelledError:
            # Server shutdown - clean exit
            print("Game loop shutting down...")
            break
        except Exception as e:
            # Log errors but don't crash the game loop
            import traceback

            print(f"Error in game loop: {e}")
            traceback.print_exc()
            # Back off on errors to prevent tight error loops
            await asyncio.sleep(1.0)
