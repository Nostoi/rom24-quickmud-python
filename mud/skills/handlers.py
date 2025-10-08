from __future__ import annotations

# Auto-generated skill handlers
# TODO: Replace stubs with actual ROM spell/skill implementations
from mud.affects.saves import check_dispel, saves_dispel, saves_spell
from mud.combat.engine import (
    apply_damage,
    attack_round,
    get_wielded_weapon,
    is_evil,
    is_good,
    is_neutral,
    set_fighting,
    stop_fighting,
    update_pos,
)
from mud.game_loop import SkyState, weather
from mud.characters import is_clan_member, is_same_clan
from mud.characters.follow import add_follower, stop_follower
from mud.magic.effects import (
    SpellTarget,
    acid_effect,
    cold_effect,
    fire_effect,
    poison_effect,
    shock_effect,
)
from mud.math.c_compat import c_div
from mud.models.character import Character, SpellEffect
from mud.models.constants import (
    AffectFlag,
    DamageType,
    ExtraFlag,
    ImmFlag,
    ItemType,
    Position,
    RoomFlag,
    Stat,
    WearLocation,
    LEVEL_HERO,
    LIQ_WATER,
    OBJ_VNUM_DISC,
    OBJ_VNUM_MUSHROOM,
    OBJ_VNUM_SPRING,
)
from mud.models.object import Object
from mud.net.protocol import broadcast_room
from mud.spawning.obj_spawner import spawn_object
from mud.utils import rng_mm
from mud.world.look import look
from mud.world.vision import can_see_room


def _send_to_char(character: Character, message: str) -> None:
    """Append a message to the character similar to ROM send_to_char."""

    if hasattr(character, "send_to_char"):
        try:
            character.send_to_char(message)
            return
        except Exception:  # pragma: no cover - defensive parity guard
            pass
    if hasattr(character, "messages"):
        character.messages.append(message)


def _is_outside(character: Character) -> bool:
    """Return True when the character is in a room without ROOM_INDOORS."""

    room = getattr(character, "room", None)
    if room is None:
        return False
    try:
        flags = int(getattr(room, "room_flags", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - invalid flags fall back
        flags = 0
    return not bool(flags & int(RoomFlag.ROOM_INDOORS))


def _normalize_value_list(obj: Object, *, minimum: int = 3) -> list[int]:
    """Return a mutable copy of an object's value list with at least ``minimum`` slots."""

    raw_values = getattr(obj, "value", None)
    if isinstance(raw_values, list):
        values = list(raw_values)
    else:
        values = []
    if len(values) < minimum:
        values.extend([0] * (minimum - len(values)))
    return values


def _coerce_int(value: object) -> int:
    """Best-effort conversion mirroring ROM's permissive int coercion."""

    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _resolve_item_type(value: object) -> ItemType | None:
    """Translate assorted item type representations to ``ItemType``."""

    if isinstance(value, ItemType):
        return value
    if isinstance(value, int):
        try:
            return ItemType(value)
        except ValueError:
            return None
    if isinstance(value, str):
        normalized = value.strip().replace(" ", "_").replace("-", "_").upper()
        if not normalized:
            return None
        aliases = {
            "DRINK": ItemType.DRINK_CON,
            "DRINKCON": ItemType.DRINK_CON,
            "DRINK_CONTAINER": ItemType.DRINK_CON,
            "DRINK_CON": ItemType.DRINK_CON,
        }
        item = aliases.get(normalized)
        if item is not None:
            return item
        try:
            return ItemType[normalized]
        except KeyError:
            return None
    return None


def _object_short_descr(obj: Object) -> str:
    """Return a user-facing short description for messaging."""

    short_descr = getattr(getattr(obj, "prototype", None), "short_descr", None)
    if isinstance(short_descr, str) and short_descr.strip():
        return short_descr.strip()
    return "Something"


def _character_name(character: Character | None) -> str:
    """Return the character's display name or a fallback placeholder."""

    if character is None:
        return "Someone"
    name = getattr(character, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    short_descr = getattr(character, "short_descr", None)
    if isinstance(short_descr, str) and short_descr.strip():
        return short_descr.strip()
    return "Someone"


def _breath_damage(
    caster: Character,
    level: int,
    *,
    min_hp: int,
    low_divisor: int,
    high_divisor: int,
    dice_size: int,
    high_cap: int | None = None,
) -> tuple[int, int]:
    """Return (hp_dam, total_damage) using ROM breath formulas."""

    caster_hit = int(getattr(caster, "hit", 0) or 0)
    hpch = max(min_hp, caster_hit)

    low = c_div(hpch, low_divisor) + 1
    if high_cap is not None:
        high = high_cap
    else:
        high = c_div(hpch, high_divisor)
    if high < low:
        high = low

    hp_dam = rng_mm.number_range(low, high)
    dice_dam = rng_mm.dice(level, dice_size)
    dam = max(hp_dam + c_div(dice_dam, 10), dice_dam + c_div(hp_dam, 10))
    return hp_dam, dam


def acid_blast(caster: Character, target: Character | None = None) -> int:
    """ROM spell_acid_blast: dice(level, 12) with save-for-half."""
    if target is None:
        raise ValueError("acid_blast requires a target")

    level = max(getattr(caster, "level", 0), 0)
    damage = rng_mm.dice(level, 12)
    if saves_spell(level, target, DamageType.ACID):
        damage = c_div(damage, 2)

    target.hit -= damage
    update_pos(target)
    return damage


def acid_breath(caster: Character, target: Character | None = None) -> int:
    """ROM spell_acid_breath with save-for-half and acid effects."""

    if caster is None or target is None:
        raise ValueError("acid_breath requires caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    _, dam = _breath_damage(
        caster,
        level,
        min_hp=12,
        low_divisor=11,
        high_divisor=6,
        dice_size=16,
    )

    if saves_spell(level, target, DamageType.ACID):
        acid_effect(target, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
        damage = c_div(dam, 2)
    else:
        acid_effect(target, level, dam, SpellTarget.CHAR)
        damage = dam

    target.hit -= damage
    update_pos(target)
    return damage


def armor(caster: Character, target: Character | None = None) -> bool:
    """ROM spell_armor: apply -20 AC affect with 24 tick duration."""
    target = target or caster
    if target is None:
        raise ValueError("armor requires a target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(name="armor", duration=24, level=level, ac_mod=-20)
    return target.apply_spell_effect(effect)


def axe(caster, target=None):
    """Stub implementation for axe.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def backstab(
    caster: Character,
    target: Character | None = None,
) -> str:
    """Perform a ROM-style backstab using the core attack pipeline."""

    if caster is None or target is None:
        raise ValueError("backstab requires a caster and target")

    weapon = get_wielded_weapon(caster)
    if weapon is None:
        raise ValueError("backstab requires a wielded weapon")

    # Delegate to the shared attack pipeline so THAC0/defense logic applies.
    return attack_round(caster, target, dt="backstab")


def bash(
    caster: Character,
    target: Character | None = None,
    *,
    success: bool | None = None,
    chance: int | None = None,
) -> str:
    """Replicate ROM bash knockdown and damage spread."""

    if caster is None or target is None:
        raise ValueError("bash requires both caster and target")

    bash_type = int(DamageType.BASH)
    if not success:
        return apply_damage(caster, target, 0, bash_type)

    chance = int(chance or 0)
    size = max(0, int(getattr(caster, "size", 0) or 0))
    upper = 2 + 2 * size + c_div(chance, 20)
    damage = rng_mm.number_range(2, max(2, upper))

    # DAZE_STATE in ROM applies 3 * PULSE_VIOLENCE to the victim.
    from mud.config import get_pulse_violence

    victim_daze = 3 * get_pulse_violence()
    target.daze = max(int(getattr(target, "daze", 0) or 0), victim_daze)
    result = apply_damage(caster, target, damage, bash_type)
    target.position = Position.RESTING
    return result


def berserk(
    caster: Character,
    target: Character | None = None,
    *,
    duration: int | None = None,
) -> bool:
    """Apply ROM-style berserk affect bonuses."""

    if caster is None:
        raise ValueError("berserk requires a caster")

    level = max(1, int(getattr(caster, "level", 1) or 1))
    hit_mod = max(1, c_div(level, 5))
    ac_penalty = max(10, 10 * c_div(level, 5))

    if duration is None:
        base = max(1, c_div(level, 8))
        duration = rng_mm.number_fuzzy(base)

    effect = SpellEffect(
        name="berserk",
        duration=duration,
        level=level,
        ac_mod=ac_penalty,
        hitroll_mod=hit_mod,
        damroll_mod=hit_mod,
        affect_flag=AffectFlag.BERSERK,
    )
    return caster.apply_spell_effect(effect)


def bless(caster: Character, target: Character | None = None) -> bool:
    """ROM spell_bless for characters: +hitroll, -saving_throw."""
    target = target or caster
    if target is None:
        raise ValueError("bless requires a target")

    if target.position == Position.FIGHTING:
        return False

    level = max(getattr(caster, "level", 0), 0)
    modifier = c_div(level, 8)
    effect = SpellEffect(
        name="bless",
        duration=6 + level,
        level=level,
        hitroll_mod=modifier,
        saving_throw_mod=-modifier,
    )
    return target.apply_spell_effect(effect)


def blindness(caster: Character, target: Character | None = None) -> bool:
    """Apply ROM ``spell_blindness`` affect and messaging."""

    if caster is None or target is None:
        raise ValueError("blindness requires a target")

    if target.has_affect(AffectFlag.BLIND) or target.has_spell_effect("blindness"):
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if saves_spell(level, target, int(DamageType.OTHER)):
        return False

    effect = SpellEffect(
        name="blindness",
        duration=1 + level,
        level=level,
        hitroll_mod=-4,
        affect_flag=AffectFlag.BLIND,
        wear_off_message="You can see again.",
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    if hasattr(target, "messages"):
        target.messages.append("You are blinded!")

    room = getattr(target, "room", None)
    if room is not None:
        if target.name:
            room_message = f"{target.name} appears to be blinded."
        else:
            room_message = "Someone appears to be blinded."
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(room_message)

    return True


def burning_hands(caster: Character, target: Character | None = None) -> int:
    """ROM spell_burning_hands damage table with save-for-half."""
    if target is None:
        raise ValueError("burning_hands requires a target")

    dam_each = [
        0,
        0,
        0,
        0,
        0,
        14,
        17,
        20,
        23,
        26,
        29,
        29,
        29,
        30,
        30,
        31,
        31,
        32,
        32,
        33,
        33,
        34,
        34,
        35,
        35,
        36,
        36,
        37,
        37,
        38,
        38,
        39,
        39,
        40,
        40,
        41,
        41,
        42,
        42,
        43,
        43,
        44,
        44,
        45,
        45,
        46,
        46,
        47,
        47,
        48,
        48,
    ]

    level = max(getattr(caster, "level", 0), 0)
    capped_level = max(0, min(level, len(dam_each) - 1))
    base = dam_each[capped_level]
    low = c_div(base, 2)
    high = base * 2
    damage = rng_mm.number_range(low, high)

    if saves_spell(level, target, DamageType.FIRE):
        damage = c_div(damage, 2)

    target.hit -= damage
    update_pos(target)
    return damage


def call_lightning(caster: Character, target: Character | None = None) -> int:
    """ROM spell_call_lightning: dice(level/2, 8) with save-for-half."""
    if target is None:
        raise ValueError("call_lightning requires a target")

    if not _is_outside(caster):
        _send_to_char(caster, "You must be out of doors.")
        return 0

    if weather.sky < SkyState.RAINING:
        _send_to_char(caster, "You need bad weather.")
        return 0

    caster_room = getattr(caster, "room", None)
    target_room = getattr(target, "room", None)
    if caster_room is None or target_room is None or caster_room is not target_room:
        return 0

    level = max(getattr(caster, "level", 0), 0)
    dice_level = max(0, c_div(level, 2))
    damage = rng_mm.dice(dice_level, 8)

    if damage <= 0:
        return 0

    _send_to_char(caster, "Mota's lightning strikes your foes!")
    caster_room.broadcast("$n calls Mota's lightning to strike $s foes!", exclude=caster)

    if saves_spell(level, target, DamageType.LIGHTNING):
        damage = c_div(damage, 2)

    target.hit -= damage
    update_pos(target)
    return damage


def calm(caster, target=None):
    """Stub implementation for calm.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def cause_critical(caster, target=None):
    """Stub implementation for cause_critical.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def cause_light(caster, target=None):
    """Stub implementation for cause_light.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def cause_serious(caster, target=None):
    """Stub implementation for cause_serious.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def chain_lightning(caster, target=None):
    """Stub implementation for chain_lightning.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def change_sex(caster, target=None):
    """Stub implementation for change_sex.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def charm_person(caster: Character, target: Character | None = None) -> bool:
    """Apply ROM ``spell_charm_person`` safeguards and charm affect."""

    if caster is None or target is None:
        raise ValueError("charm_person requires a target")

    if target is caster:
        if hasattr(caster, "messages") and isinstance(caster.messages, list):
            caster.messages.append("You like yourself even better!")
        return False

    if target.has_affect(AffectFlag.CHARM) or target.has_spell_effect("charm person"):
        return False

    if caster.has_affect(AffectFlag.CHARM):
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    victim_level = max(int(getattr(target, "level", 0) or 0), 0)
    if level < victim_level:
        return False

    imm_flags = int(getattr(target, "imm_flags", 0) or 0)
    if imm_flags & int(ImmFlag.CHARM):
        return False

    room = getattr(target, "room", None)
    if room is not None:
        flags = int(getattr(room, "room_flags", 0) or 0)
        if flags & int(RoomFlag.ROOM_LAW):
            if hasattr(caster, "messages") and isinstance(caster.messages, list):
                caster.messages.append(
                    "The mayor does not allow charming in the city limits."
                )
            return False

    if saves_spell(level, target, DamageType.CHARM):
        return False

    if getattr(target, "master", None) is not None:
        stop_follower(target)

    add_follower(target, caster)
    target.leader = caster

    base_duration = max(1, c_div(level, 4))
    duration = rng_mm.number_fuzzy(base_duration)

    effect = SpellEffect(
        name="charm person",
        duration=duration,
        level=level,
        affect_flag=AffectFlag.CHARM,
        wear_off_message="You feel more self-confident.",
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        stop_follower(target)
        return False

    actor_name = getattr(caster, "name", None) or "Someone"
    target_messages = getattr(target, "messages", None)
    if isinstance(target_messages, list):
        target_messages.append(f"Isn't {actor_name} just so nice?")

    if caster is not target:
        target_name = getattr(target, "name", None) or "Someone"
        caster_messages = getattr(caster, "messages", None)
        if isinstance(caster_messages, list):
            caster_messages.append(f"{target_name} looks at you with adoring eyes.")

    return True


def chill_touch(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_chill_touch`` cold damage plus strength debuff."""

    if caster is None or target is None:
        raise ValueError("chill_touch requires a target")

    dam_each = [
        0,
        0,
        0,
        6,
        7,
        8,
        9,
        12,
        13,
        13,
        13,
        14,
        14,
        14,
        15,
        15,
        15,
        16,
        16,
        16,
        17,
        17,
        17,
        18,
        18,
        18,
        19,
        19,
        19,
        20,
        20,
        20,
        21,
        21,
        21,
        22,
        22,
        22,
        23,
        23,
        23,
        24,
        24,
        24,
        25,
        25,
        25,
        26,
        26,
        26,
        27,
    ]

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    capped = max(0, min(level, len(dam_each) - 1))
    base = dam_each[capped]
    low = c_div(base, 2)
    high = base * 2
    damage = rng_mm.number_range(low, high)

    if saves_spell(capped, target, DamageType.COLD):
        damage = c_div(damage, 2)
    else:
        room = getattr(target, "room", None)
        if room is not None:
            target_name = getattr(target, "name", None) or "Someone"
            message = f"{target_name} turns blue and shivers."
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is target:
                    continue
                if hasattr(occupant, "messages"):
                    occupant.messages.append(message)

        effect = SpellEffect(
            name="chill touch",
            duration=6,
            level=capped,
            stat_modifiers={Stat.STR: -1},
        )
        target.apply_spell_effect(effect)

    target.hit -= damage
    update_pos(target)
    return damage


def colour_spray(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_colour_spray`` damage with blindness on failed save."""

    if caster is None or target is None:
        raise ValueError("colour_spray requires a target")

    dam_each = [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        30,
        35,
        40,
        45,
        50,
        55,
        55,
        55,
        56,
        57,
        58,
        58,
        59,
        60,
        61,
        61,
        62,
        63,
        64,
        64,
        65,
        66,
        67,
        67,
        68,
        69,
        70,
        70,
        71,
        72,
        73,
        73,
        74,
        75,
        76,
        76,
        77,
        78,
        79,
        79,
    ]

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    capped = max(0, min(level, len(dam_each) - 1))
    base = dam_each[capped]
    damage = rng_mm.number_range(c_div(base, 2), base * 2)

    caster_name = getattr(caster, "name", None) or "Someone"
    target_name = getattr(target, "name", None) or "Someone"
    caster_msg = (
        f"{{3You spray {{1red{{x, {{4blue{{x, and {{6yellow{{x light at {target_name}!{{x"
    )
    target_msg = (
        f"{{3{caster_name} sprays {{1red{{x, {{4blue{{x, and {{6yellow{{x light across your vision!{{x"
    )
    room_msg = (
        f"{{3{caster_name} sprays {{1red{{x, {{4blue{{x, and {{6yellow{{x light at {target_name}!{{x"
    )

    if hasattr(caster, "messages"):
        caster.messages.append(caster_msg)
    if hasattr(target, "messages"):
        target.messages.append(target_msg)

    room = getattr(caster, "room", None)
    if room is not None:
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is caster or occupant is target:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(room_msg)

    if saves_spell(capped, target, DamageType.LIGHT):
        damage = c_div(damage, 2)
    else:
        blind_level = c_div(capped, 2)
        original_level = getattr(caster, "level", 0)
        setattr(caster, "level", blind_level)
        try:
            blindness(caster, target)
        finally:
            setattr(caster, "level", original_level)

    target.hit -= damage
    update_pos(target)
    return damage


def continual_light(caster, target=None):
    """Stub implementation for continual_light.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def control_weather(caster, target=None):
    """Stub implementation for control_weather.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def create_food(caster: Character, target: Object | None = None) -> Object | None:
    """ROM ``spell_create_food`` conjures a mushroom object in the room."""

    if caster is None:
        raise ValueError("create_food requires a caster")

    room = getattr(caster, "room", None)
    if room is None:
        return None

    mushroom = spawn_object(OBJ_VNUM_MUSHROOM)
    if mushroom is None:
        return None

    level = max(_coerce_int(getattr(caster, "level", 0)), 0)
    values = _normalize_value_list(mushroom, minimum=2)
    values[0] = c_div(level, 2)
    values[1] = level
    mushroom.value = values

    room.add_object(mushroom)
    message = f"{_object_short_descr(mushroom)} suddenly appears."
    room.broadcast(message, exclude=caster)
    _send_to_char(caster, message)
    return mushroom


def create_rose(caster, target=None):
    """Stub implementation for create_rose.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def create_spring(caster: Character, target: Object | None = None) -> Object | None:
    """ROM ``spell_create_spring`` conjures a spring with a level-based timer."""

    if caster is None:
        raise ValueError("create_spring requires a caster")

    room = getattr(caster, "room", None)
    if room is None:
        return None

    spring = spawn_object(OBJ_VNUM_SPRING)
    if spring is None:
        return None

    spring.timer = max(_coerce_int(getattr(caster, "level", 0)), 0)
    room.add_object(spring)

    message = f"{_object_short_descr(spring)} flows from the ground."
    room.broadcast(message, exclude=caster)
    _send_to_char(caster, message)
    return spring


def create_water(caster: Character, target: Object | None = None) -> bool:
    """ROM ``spell_create_water`` fills drink containers with water."""

    if caster is None or target is None:
        raise ValueError("create_water requires a drink container target")

    raw_item_type = getattr(target, "item_type", None)
    if raw_item_type is None:
        raw_item_type = getattr(getattr(target, "prototype", None), "item_type", None)

    item_type = _resolve_item_type(raw_item_type)
    if item_type is not ItemType.DRINK_CON:
        _send_to_char(caster, "It is unable to hold water.")
        return False

    values = _normalize_value_list(target, minimum=3)
    capacity = max(_coerce_int(values[0]), 0)
    current = max(_coerce_int(values[1]), 0)
    liquid_type = _coerce_int(values[2])

    if liquid_type not in (LIQ_WATER, 0) and current != 0:
        _send_to_char(caster, "It contains some other liquid.")
        return False

    level = max(_coerce_int(getattr(caster, "level", 0)), 0)
    multiplier = 4 if int(weather.sky) >= int(SkyState.RAINING) else 2
    space_remaining = max(0, capacity - current)
    water = min(level * multiplier, space_remaining)

    if water <= 0:
        _send_to_char(caster, "It is already full of water.")
        return False

    values[2] = LIQ_WATER
    values[1] = current + water
    target.value = values

    message = f"{_object_short_descr(target)} is filled."
    _send_to_char(caster, message)
    room = getattr(caster, "room", None)
    if room is not None:
        room.broadcast(message, exclude=caster)
    return True


def cure_blindness(
    caster: Character, target: Character | None = None
) -> bool:
    """Dispel ROM blindness affect with success/failure messaging."""

    victim = target or caster
    if victim is None:
        raise ValueError("cure_blindness requires a target")

    if not (
        victim.has_affect(AffectFlag.BLIND)
        or victim.has_spell_effect("blindness")
    ):
        if victim is caster:
            _send_to_char(victim, "You aren't blind.")
        else:
            name = getattr(victim, "name", None) or "Someone"
            _send_to_char(caster, f"{name} doesn't appear to be blinded.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if check_dispel(level, victim, "blindness"):
        _send_to_char(victim, "Your vision returns!")
        room = getattr(victim, "room", None)
        if room is not None:
            name = getattr(victim, "name", None) or "Someone"
            message = f"{name} is no longer blinded."
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is victim:
                    continue
                if hasattr(occupant, "messages"):
                    occupant.messages.append(message)
        return True

    _send_to_char(caster, "Spell failed.")
    return False


def cure_critical(
    caster: Character, target: Character | None = None
) -> int:
    """ROM ``spell_cure_critical`` healing dice and messaging."""

    target = target or caster
    if target is None:
        raise ValueError("cure_critical requires a target")

    level = int(getattr(caster, "level", 0) or 0)
    heal = rng_mm.dice(3, 8) + level - 6

    max_hit = getattr(target, "max_hit", 0)
    if max_hit > 0:
        target.hit = min(target.hit + heal, max_hit)
    else:
        target.hit += heal

    update_pos(target)
    _send_to_char(target, "You feel better!")
    if caster is not target:
        _send_to_char(caster, "Ok.")
    return heal


def cure_disease(
    caster: Character, target: Character | None = None
) -> bool:
    """Dispel ROM plague affect with messaging for success/failure."""

    victim = target or caster
    if victim is None:
        raise ValueError("cure_disease requires a target")

    if not (
        victim.has_affect(AffectFlag.PLAGUE)
        or victim.has_spell_effect("plague")
    ):
        if victim is caster:
            _send_to_char(victim, "You aren't ill.")
        else:
            name = getattr(victim, "name", None) or "Someone"
            _send_to_char(caster, f"{name} doesn't appear to be diseased.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if check_dispel(level, victim, "plague"):
        _send_to_char(victim, "Your sores vanish.")
        room = getattr(victim, "room", None)
        if room is not None:
            name = getattr(victim, "name", None) or "Someone"
            message = f"{name} looks relieved as their sores vanish."
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is victim:
                    continue
                if hasattr(occupant, "messages"):
                    occupant.messages.append(message)
        return True

    _send_to_char(caster, "Spell failed.")
    return False


def cure_light(caster: Character, target: Character | None = None) -> int:
    """ROM spell_cure_light: heal dice(1,8) + level/3."""
    target = target or caster
    if target is None:
        raise ValueError("cure_light requires a target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    heal = rng_mm.dice(1, 8) + c_div(level, 3)

    max_hit = getattr(target, "max_hit", 0)
    if max_hit > 0:
        target.hit = min(target.hit + heal, max_hit)
    else:
        target.hit += heal

    update_pos(target)
    _send_to_char(target, "You feel better!")
    if caster is not target:
        _send_to_char(caster, "Ok.")
    return heal


def cure_poison(
    caster: Character, target: Character | None = None
) -> bool:
    """Dispel ROM poison affect with messaging on outcome."""

    victim = target or caster
    if victim is None:
        raise ValueError("cure_poison requires a target")

    if not (
        victim.has_affect(AffectFlag.POISON)
        or victim.has_spell_effect("poison")
    ):
        if victim is caster:
            _send_to_char(victim, "You aren't poisoned.")
        else:
            name = getattr(victim, "name", None) or "Someone"
            _send_to_char(caster, f"{name} doesn't appear to be poisoned.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    if check_dispel(level, victim, "poison"):
        _send_to_char(victim, "A warm feeling runs through your body.")
        room = getattr(victim, "room", None)
        if room is not None:
            name = getattr(victim, "name", None) or "Someone"
            message = f"{name} looks much better."
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is victim:
                    continue
                if hasattr(occupant, "messages"):
                    occupant.messages.append(message)
        return True

    _send_to_char(caster, "Spell failed.")
    return False


def cure_serious(
    caster: Character, target: Character | None = None
) -> int:
    """ROM ``spell_cure_serious`` healing dice and messaging."""

    target = target or caster
    if target is None:
        raise ValueError("cure_serious requires a target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    heal = rng_mm.dice(2, 8) + c_div(level, 2)

    max_hit = getattr(target, "max_hit", 0)
    if max_hit > 0:
        target.hit = min(target.hit + heal, max_hit)
    else:
        target.hit += heal

    update_pos(target)
    _send_to_char(target, "You feel better!")
    if caster is not target:
        _send_to_char(caster, "Ok.")
    return heal


def curse(caster, target=None):
    """Port of ROM ``spell_curse`` for characters and objects."""

    if caster is None:
        raise ValueError("curse requires a caster")

    if target is None:
        target = caster

    # Object curse branch mirrors src/magic.c:1725-1778
    if isinstance(target, Object):
        obj = target
        extra_flags = int(getattr(obj, "extra_flags", 0) or 0)
        if extra_flags & int(ExtraFlag.NOUNCURSE):
            return False
        if extra_flags & int(ExtraFlag.EVIL):
            _send_to_char(caster, f"{obj.short_descr or 'It'} is already filled with evil.")
            return False

        level = int(getattr(caster, "level", 0) or 0)
        if extra_flags & int(ExtraFlag.BLESS):
            obj_level = int(getattr(obj, "level", getattr(obj.prototype, "level", 0)) or 0)
            if saves_dispel(level, obj_level, duration=0):
                _send_to_char(
                    caster,
                    f"The holy aura of {obj.short_descr or 'it'} is too powerful for you to overcome.",
                )
                return False
            obj.extra_flags = extra_flags & ~int(ExtraFlag.BLESS)
            _send_to_char(caster, f"{obj.short_descr or 'It'} glows with a red aura.")
            extra_flags = int(getattr(obj, "extra_flags", 0) or 0)

        obj.extra_flags = extra_flags | int(ExtraFlag.EVIL)
        _send_to_char(caster, f"{obj.short_descr or 'It'} glows with a malevolent aura.")
        return True

    if not isinstance(target, Character):
        raise TypeError("curse target must be Character or Object")

    victim = target
    if victim.has_affect(AffectFlag.CURSE) or victim.has_spell_effect("curse"):
        return False

    level = int(getattr(caster, "level", 0) or 0)
    if saves_spell(level, victim, DamageType.NEGATIVE):
        return False

    modifier = c_div(level, 8)
    duration = 2 * level
    effect = SpellEffect(
        name="curse",
        duration=duration,
        level=level,
        hitroll_mod=-modifier,
        saving_throw_mod=modifier,
        affect_flag=AffectFlag.CURSE,
        wear_off_message="The curse wears off.",
    )
    applied = victim.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(victim, "You feel unclean.")
    if victim is not caster:
        victim_name = getattr(victim, "name", None) or "Someone"
        _send_to_char(caster, f"{victim_name} looks very uncomfortable.")
    return True


def dagger(caster, target=None):
    """Stub implementation for dagger.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def demonfire(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_demonfire`` negative damage plus curse side effects."""

    if caster is None:
        raise ValueError("demonfire requires a caster")

    victim = target or caster
    if victim is None:
        raise ValueError("demonfire requires a target")

    if not getattr(caster, "is_npc", True) and not is_evil(caster):
        victim = caster
        _send_to_char(caster, "The demons turn upon you!")

    caster.alignment = max(-1000, int(getattr(caster, "alignment", 0) or 0) - 50)

    if victim is not caster:
        room = getattr(caster, "room", None)
        caster_name = getattr(caster, "name", None) or "Someone"
        victim_name = getattr(victim, "name", None) or "Someone"
        if room is not None:
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is caster:
                    continue
                message = f"{caster_name} calls forth the demons of Hell upon {victim_name}!"
                _send_to_char(occupant, message)
        _send_to_char(victim, f"{caster_name} has assailed you with the demons of Hell!")
        _send_to_char(caster, "You conjure forth the demons of hell!")

    level = max(1, int(getattr(caster, "level", 0) or 0))
    damage = rng_mm.dice(level, 10)
    if saves_spell(level, victim, DamageType.NEGATIVE):
        damage = c_div(damage, 2)

    victim.hit -= damage
    update_pos(victim)

    curse_level = max(0, c_div(3 * level, 4))
    if (
        curse_level > 0
        and not victim.has_affect(AffectFlag.CURSE)
        and not victim.has_spell_effect("curse")
        and not saves_spell(curse_level, victim, DamageType.NEGATIVE)
    ):
        modifier = c_div(curse_level, 8)
        duration = 2 * curse_level
        effect = SpellEffect(
            name="curse",
            duration=duration,
            level=curse_level,
            hitroll_mod=-modifier,
            saving_throw_mod=modifier,
            affect_flag=AffectFlag.CURSE,
            wear_off_message="The curse wears off.",
        )
        if victim.apply_spell_effect(effect):
            _send_to_char(victim, "You feel unclean.")
            if victim is not caster:
                victim_name = getattr(victim, "name", None) or "Someone"
                _send_to_char(caster, f"{victim_name} looks very uncomfortable.")

    return damage


def detect_evil(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_detect_evil`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("detect_evil requires a target")

    if target.has_affect(AffectFlag.DETECT_EVIL) or target.has_spell_effect("detect evil"):
        if target is caster:
            _send_to_char(caster, "You can already sense evil.")
        else:
            target_name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{target_name} can already detect evil.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="detect evil",
        duration=level,
        level=level,
        affect_flag=AffectFlag.DETECT_EVIL,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "Your eyes tingle.")
    if target is not caster:
        _send_to_char(caster, "Ok.")
    return True


def detect_good(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_detect_good`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("detect_good requires a target")

    if target.has_affect(AffectFlag.DETECT_GOOD) or target.has_spell_effect("detect good"):
        if target is caster:
            _send_to_char(caster, "You can already sense good.")
        else:
            target_name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{target_name} can already detect good.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="detect good",
        duration=level,
        level=level,
        affect_flag=AffectFlag.DETECT_GOOD,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "Your eyes tingle.")
    if target is not caster:
        _send_to_char(caster, "Ok.")
    return True


def detect_hidden(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_detect_hidden`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("detect_hidden requires a target")

    if target.has_affect(AffectFlag.DETECT_HIDDEN) or target.has_spell_effect("detect hidden"):
        if target is caster:
            _send_to_char(caster, "You are already as alert as you can be.")
        else:
            target_name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{target_name} can already sense hidden lifeforms.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="detect hidden",
        duration=level,
        level=level,
        affect_flag=AffectFlag.DETECT_HIDDEN,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "Your awareness improves.")
    if target is not caster:
        _send_to_char(caster, "Ok.")
    return True


def detect_invis(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_detect_invis`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("detect_invis requires a target")

    if target.has_affect(AffectFlag.DETECT_INVIS) or target.has_spell_effect("detect invis"):
        if target is caster:
            _send_to_char(caster, "You can already see invisible.")
        else:
            target_name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{target_name} can already see invisible things.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="detect invis",
        duration=level,
        level=level,
        affect_flag=AffectFlag.DETECT_INVIS,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "Your eyes tingle.")
    if target is not caster:
        _send_to_char(caster, "Ok.")
    return True


def detect_magic(caster: Character, target: Character | None = None) -> bool:
    """ROM ``spell_detect_magic`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("detect_magic requires a target")

    if target.has_affect(AffectFlag.DETECT_MAGIC) or target.has_spell_effect("detect magic"):
        if target is caster:
            _send_to_char(caster, "You can already sense magical auras.")
        else:
            target_name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{target_name} can already detect magic.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="detect magic",
        duration=level,
        level=level,
        affect_flag=AffectFlag.DETECT_MAGIC,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    _send_to_char(target, "Your eyes tingle.")
    if target is not caster:
        _send_to_char(caster, "Ok.")
    return True


def detect_poison(caster: Character, target: Object | None = None) -> bool:
    """ROM ``spell_detect_poison`` inspection messaging."""

    if caster is None:
        raise ValueError("detect_poison requires a caster")
    if target is None:
        raise ValueError("detect_poison requires an object target")

    item_type = _resolve_item_type(getattr(target, "item_type", None))
    if item_type is None and hasattr(target, "prototype"):
        item_type = _resolve_item_type(getattr(target.prototype, "item_type", None))

    if item_type in (ItemType.DRINK_CON, ItemType.FOOD):
        values = _normalize_value_list(target, minimum=4)
        if values[3]:
            _send_to_char(caster, "You smell poisonous fumes.")
        else:
            _send_to_char(caster, "It looks delicious.")
    else:
        _send_to_char(caster, "It doesn't look poisoned.")
    return True


def dirt_kicking(caster, target=None):
    """Stub implementation for dirt_kicking.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def disarm(caster, target=None):
    """Stub implementation for disarm.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def dispel_evil(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_dispel_evil`` holy damage with alignment gating."""

    if caster is None:
        raise ValueError("dispel_evil requires a caster")

    victim = target or caster
    if victim is None:
        raise ValueError("dispel_evil requires a target")

    if not getattr(caster, "is_npc", True) and is_evil(caster):
        victim = caster

    if is_good(victim):
        victim_name = getattr(victim, "name", None) or "Someone"
        room = getattr(caster, "room", None)
        if room is not None:
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is caster:
                    continue
                _send_to_char(occupant, f"Mota protects {victim_name}.")
        _send_to_char(caster, f"Mota protects {victim_name}.")
        return 0

    if is_neutral(victim):
        victim_name = getattr(victim, "name", None) or "Someone"
        _send_to_char(caster, f"{victim_name} does not seem to be affected.")
        return 0

    level = max(1, int(getattr(caster, "level", 0) or 0))
    victim_hit = max(0, int(getattr(victim, "hit", 0) or 0))
    if victim_hit > level * 4:
        damage = rng_mm.dice(level, 4)
    else:
        damage = max(victim_hit, rng_mm.dice(level, 4))
    if saves_spell(level, victim, DamageType.HOLY):
        damage = c_div(damage, 2)

    victim.hit -= damage
    update_pos(victim)
    return damage


def dispel_good(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_dispel_good`` negative damage with alignment gating."""

    if caster is None:
        raise ValueError("dispel_good requires a caster")

    victim = target or caster
    if victim is None:
        raise ValueError("dispel_good requires a target")

    if not getattr(caster, "is_npc", True) and is_good(caster):
        victim = caster

    if is_evil(victim):
        victim_name = getattr(victim, "name", None) or "Someone"
        room = getattr(caster, "room", None)
        if room is not None:
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is caster:
                    continue
                _send_to_char(occupant, f"{victim_name} is protected by {victim_name}'s evil.")
        _send_to_char(caster, f"{victim_name} is protected by {victim_name}'s evil.")
        return 0

    if is_neutral(victim):
        victim_name = getattr(victim, "name", None) or "Someone"
        _send_to_char(caster, f"{victim_name} does not seem to be affected.")
        return 0

    level = max(1, int(getattr(caster, "level", 0) or 0))
    victim_hit = max(0, int(getattr(victim, "hit", 0) or 0))
    if victim_hit > level * 4:
        damage = rng_mm.dice(level, 4)
    else:
        damage = max(victim_hit, rng_mm.dice(level, 4))
    if saves_spell(level, victim, DamageType.NEGATIVE):
        damage = c_div(damage, 2)

    victim.hit -= damage
    update_pos(victim)
    return damage


def dispel_magic(caster: Character, target: Character | None = None) -> bool:
    """ROM-style dispel_magic: attempt to strip active spell effects."""

    if caster is None:
        raise ValueError("dispel_magic requires a caster")

    target = target or caster
    if target is None:
        raise ValueError("dispel_magic requires a target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effects = getattr(target, "spell_effects", {})
    if not isinstance(effects, dict) or not effects:
        return False

    success = False
    for effect_name in list(effects.keys()):
        if check_dispel(level, target, effect_name):
            success = True

    return success


def dodge(caster, target=None):
    """Stub implementation for dodge.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def earthquake(caster, target=None):
    """Stub implementation for earthquake.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def enchant_armor(caster, target=None):
    """Stub implementation for enchant_armor.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def enchant_weapon(caster, target=None):
    """Stub implementation for enchant_weapon.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def energy_drain(caster, target=None):
    """Stub implementation for energy_drain.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def enhanced_damage(caster, target=None):
    """Stub implementation for enhanced_damage.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def envenom(caster, target=None):
    """Stub implementation for envenom.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def faerie_fire(caster, target=None):
    """Stub implementation for faerie_fire.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def faerie_fog(caster, target=None):
    """Stub implementation for faerie_fog.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def farsight(caster, target=None):
    """Stub implementation for farsight.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def fast_healing(caster, target=None):
    """Stub implementation for fast_healing.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def fire_breath(caster: Character, target: Character | None = None) -> int:
    """ROM spell_fire_breath with room splash damage."""

    if caster is None or target is None:
        raise ValueError("fire_breath requires caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    _, dam = _breath_damage(
        caster,
        level,
        min_hp=10,
        low_divisor=9,
        high_divisor=5,
        dice_size=20,
    )

    room = getattr(target, "room", None) or getattr(caster, "room", None)
    occupants: list[Character] = []
    if room is not None:
        fire_effect(room, level, c_div(dam, 2), SpellTarget.ROOM)
        people = getattr(room, "people", None)
        if people:
            occupants.extend(people)
    if target not in occupants:
        occupants.append(target)

    primary_damage = 0
    seen: set[int] = set()
    for person in occupants:
        if person is None or person is caster:
            continue
        ident = id(person)
        if ident in seen:
            continue
        seen.add(ident)

        if person is target:
            if saves_spell(level, person, DamageType.FIRE):
                fire_effect(person, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
                actual = c_div(dam, 2)
            else:
                fire_effect(person, level, dam, SpellTarget.CHAR)
                actual = dam
            primary_damage = actual
        else:
            save_level = max(0, level - 2)
            if saves_spell(save_level, person, DamageType.FIRE):
                fire_effect(person, c_div(level, 4), c_div(dam, 8), SpellTarget.CHAR)
                actual = c_div(dam, 4)
            else:
                fire_effect(person, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
                actual = c_div(dam, 2)

        person.hit -= actual
        update_pos(person)

    return primary_damage


def fireball(caster, target=None):
    """Stub implementation for fireball.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def fireproof(caster, target=None):
    """Stub implementation for fireproof.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def flail(caster, target=None):
    """Stub implementation for flail.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def flamestrike(caster, target=None):
    """Stub implementation for flamestrike.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def floating_disc(caster: Character, target=None):  # noqa: ARG001 - parity signature
    """Create and equip the ROM floating disc container."""

    if caster is None:
        raise ValueError("floating_disc requires a caster")

    equipment = getattr(caster, "equipment", {}) or {}
    floating_item = None
    if isinstance(equipment, dict):
        floating_item = equipment.get("float") or equipment.get("floating")

    if floating_item is not None:
        flags = int(getattr(floating_item, "extra_flags", 0) or 0)
        if not flags and hasattr(floating_item, "prototype"):
            try:
                flags = int(getattr(floating_item.prototype, "extra_flags", 0) or 0)
            except (TypeError, ValueError):
                flags = 0
        if flags & int(ExtraFlag.NOREMOVE):
            _send_to_char(caster, f"You can't remove {_object_short_descr(floating_item)}.")
            return False
        if isinstance(equipment, dict):
            equipment.pop("float", None)
            equipment.pop("floating", None)
        floating_item.wear_loc = int(WearLocation.NONE)
        if hasattr(caster, "add_object"):
            caster.add_object(floating_item)

    disc = spawn_object(OBJ_VNUM_DISC)
    if disc is None:
        raise ValueError("floating_disc requires OBJ_VNUM_DISC prototype")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    values = _normalize_value_list(disc, minimum=4)
    values[0] = level * 10
    values[3] = level * 5
    disc.value = values

    timer_reduction = rng_mm.number_range(0, c_div(level, 2))
    disc.timer = max(level * 2 - timer_reduction, 0)
    disc.wear_loc = int(WearLocation.FLOAT)

    caster.add_object(disc)
    caster.equip_object(disc, "float")

    room = getattr(caster, "room", None)
    if room is not None:
        broadcast_room(room, f"{_character_name(caster)} has created a floating black disc.", exclude=caster)
    _send_to_char(caster, "You create a floating disc.")

    return disc


def fly(caster, target=None):
    """ROM ``spell_fly`` affect application with duplicate handling."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("fly requires a target")

    already_airborne = False
    if hasattr(target, "has_affect") and target.has_affect(AffectFlag.FLYING):
        already_airborne = True
    if getattr(target, "has_spell_effect", None):
        if target.has_spell_effect("fly"):
            already_airborne = True

    if already_airborne:
        if target is caster:
            _send_to_char(caster, "You are already airborne.")
        else:
            name = getattr(target, "name", None) or "Someone"
            _send_to_char(caster, f"{name} doesn't need your help to fly.")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="fly",
        duration=level + 3,
        level=level,
        affect_flag=AffectFlag.FLYING,
        wear_off_message="You slowly float to the ground.",
    )

    applied = target.apply_spell_effect(effect) if hasattr(target, "apply_spell_effect") else False
    if not applied:
        return False

    _send_to_char(target, "Your feet rise off the ground.")

    room = getattr(target, "room", None)
    if room is not None:
        message = (
            f"{target.name}'s feet rise off the ground."
            if getattr(target, "name", None)
            else "Someone's feet rise off the ground."
        )
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            _send_to_char(occupant, message)

    return True


def frenzy(caster: Character, target: Character | None = None) -> bool:  # noqa: ARG001 - parity signature
    """Clerical frenzy buff mirroring ROM ``spell_frenzy``."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("frenzy requires a target")

    already_frenzied = False
    if getattr(target, "has_spell_effect", None):
        if target.has_spell_effect("frenzy"):
            already_frenzied = True
    if hasattr(target, "has_affect") and target.has_affect(AffectFlag.BERSERK):
        already_frenzied = True

    if already_frenzied:
        if target is caster:
            _send_to_char(caster, "You are already in a frenzy.")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} is already in a frenzy.")
        return False

    if getattr(target, "has_spell_effect", None) and target.has_spell_effect("calm"):
        if target is caster:
            _send_to_char(caster, "Why don't you just relax for a while?")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} doesn't look like they want to fight anymore.")
        return False

    if hasattr(target, "has_affect") and target.has_affect(AffectFlag.CALM):
        if target is caster:
            _send_to_char(caster, "Why don't you just relax for a while?")
        else:
            name = _character_name(target)
            _send_to_char(caster, f"{name} doesn't look like they want to fight anymore.")
        return False

    caster_good = is_good(caster)
    caster_neutral = is_neutral(caster)
    caster_evil = is_evil(caster)
    target_good = is_good(target)
    target_neutral = is_neutral(target)
    target_evil = is_evil(target)

    if (caster_good and not target_good) or (caster_neutral and not target_neutral) or (caster_evil and not target_evil):
        name = _character_name(target)
        _send_to_char(caster, f"Your god doesn't seem to like {name}")
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    duration = c_div(level, 3)
    hit_dam_mod = c_div(level, 6)
    ac_penalty = 10 * c_div(level, 12)

    effect = SpellEffect(
        name="frenzy",
        duration=duration,
        level=level,
        hitroll_mod=hit_dam_mod,
        damroll_mod=hit_dam_mod,
        ac_mod=ac_penalty,
        wear_off_message="Your rage ebbs.",
    )

    applied = target.apply_spell_effect(effect) if hasattr(target, "apply_spell_effect") else False
    if not applied:
        return False

    _send_to_char(target, "You are filled with holy wrath!")

    room = getattr(target, "room", None)
    if room is not None:
        name = _character_name(target)
        message = f"{name} gets a wild look in their eyes!"
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            _send_to_char(occupant, message)

    return True


def frost_breath(caster: Character, target: Character | None = None) -> int:
    """ROM spell_frost_breath mirroring cold room effects."""

    if caster is None or target is None:
        raise ValueError("frost_breath requires caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    _, dam = _breath_damage(
        caster,
        level,
        min_hp=12,
        low_divisor=11,
        high_divisor=6,
        dice_size=16,
    )

    room = getattr(target, "room", None) or getattr(caster, "room", None)
    occupants: list[Character] = []
    if room is not None:
        cold_effect(room, level, c_div(dam, 2), SpellTarget.ROOM)
        people = getattr(room, "people", None)
        if people:
            occupants.extend(people)
    if target not in occupants:
        occupants.append(target)

    primary_damage = 0
    seen: set[int] = set()
    for person in occupants:
        if person is None or person is caster:
            continue
        ident = id(person)
        if ident in seen:
            continue
        seen.add(ident)

        if person is target:
            if saves_spell(level, person, DamageType.COLD):
                cold_effect(person, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
                actual = c_div(dam, 2)
            else:
                cold_effect(person, level, dam, SpellTarget.CHAR)
                actual = dam
            primary_damage = actual
        else:
            save_level = max(0, level - 2)
            if saves_spell(save_level, person, DamageType.COLD):
                cold_effect(person, c_div(level, 4), c_div(dam, 8), SpellTarget.CHAR)
                actual = c_div(dam, 4)
            else:
                cold_effect(person, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
                actual = c_div(dam, 2)

        person.hit -= actual
        update_pos(person)

    return primary_damage


def gas_breath(caster: Character, target: Character | None = None) -> int:
    """ROM spell_gas_breath poisoning everyone in the room."""

    if caster is None:
        raise ValueError("gas_breath requires a caster")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    _, dam = _breath_damage(
        caster,
        level,
        min_hp=16,
        low_divisor=15,
        high_divisor=15,
        dice_size=12,
        high_cap=8,
    )

    room = getattr(caster, "room", None) or getattr(target, "room", None)
    occupants: list[Character] = []
    if room is not None:
        poison_effect(room, level, dam, SpellTarget.ROOM)
        people = getattr(room, "people", None)
        if people:
            occupants.extend(people)
    if target is not None and target not in occupants:
        occupants.append(target)

    primary_damage = 0
    seen: set[int] = set()
    for person in occupants:
        if person is None or person is caster:
            continue
        ident = id(person)
        if ident in seen:
            continue
        seen.add(ident)

        if saves_spell(level, person, DamageType.POISON):
            poison_effect(person, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
            actual = c_div(dam, 2)
        else:
            poison_effect(person, level, dam, SpellTarget.CHAR)
            actual = dam

        person.hit -= actual
        update_pos(person)

        if primary_damage == 0 and ((target is None) or person is target):
            primary_damage = actual

    return primary_damage


def _gate_fail(caster: Character | None) -> bool:
    if caster is not None:
        _send_to_char(caster, "You failed.")
    return False


def gate(caster: Character, target: Character | None = None):
    """Teleport the caster (and pet) to the target's room per ROM ``spell_gate``."""

    if caster is None or target is None:
        raise ValueError("gate requires a target")

    current_room = getattr(caster, "room", None)
    target_room = getattr(target, "room", None)
    if current_room is None or target_room is None or caster is target:
        return _gate_fail(caster)

    if not can_see_room(caster, target_room):
        return _gate_fail(caster)

    def _room_flags(room) -> int:
        try:
            return int(getattr(room, "room_flags", 0) or 0)
        except (TypeError, ValueError):
            return 0

    target_flags = _room_flags(target_room)
    current_flags = _room_flags(current_room)

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    try:
        target_level = int(getattr(target, "level", 0) or 0)
    except (TypeError, ValueError):
        target_level = 0

    if target_flags & int(RoomFlag.ROOM_SAFE):
        return _gate_fail(caster)
    if target_flags & int(RoomFlag.ROOM_PRIVATE):
        return _gate_fail(caster)
    if target_flags & int(RoomFlag.ROOM_SOLITARY):
        return _gate_fail(caster)
    if target_flags & int(RoomFlag.ROOM_NO_RECALL):
        return _gate_fail(caster)
    if current_flags & int(RoomFlag.ROOM_NO_RECALL):
        return _gate_fail(caster)
    if target_level >= level + 3:
        return _gate_fail(caster)
    if is_clan_member(target) and not is_same_clan(caster, target):
        return _gate_fail(caster)

    is_target_npc = bool(getattr(target, "is_npc", True))
    if not is_target_npc and target_level >= LEVEL_HERO:
        return _gate_fail(caster)

    if is_target_npc:
        try:
            imm_flags = int(getattr(target, "imm_flags", 0) or 0)
        except (TypeError, ValueError):
            imm_flags = 0
        if imm_flags & int(ImmFlag.SUMMON):
            return _gate_fail(caster)
        if saves_spell(level, target, DamageType.OTHER):
            return _gate_fail(caster)

    caster_name = _character_name(caster)
    broadcast_room(current_room, f"{caster_name} steps through a gate and vanishes.", exclude=caster)
    _send_to_char(caster, "You step through a gate and vanish.")

    caster.was_in_room = current_room
    current_room.remove_character(caster)
    target_room.add_character(caster)

    broadcast_room(target_room, f"{caster_name} has arrived through a gate.", exclude=caster)
    view = look(caster)
    if view:
        _send_to_char(caster, view)

    pet = getattr(caster, "pet", None)
    if isinstance(pet, Character) and getattr(pet, "room", None) is current_room:
        pet_name = _character_name(pet)
        broadcast_room(current_room, f"{pet_name} steps through a gate and vanishes.", exclude=pet)
        _send_to_char(pet, "You step through a gate and vanish.")

        pet.was_in_room = current_room
        current_room.remove_character(pet)
        target_room.add_character(pet)

        broadcast_room(target_room, f"{pet_name} has arrived through a gate.", exclude=pet)
        pet_view = look(pet)
        if pet_view:
            _send_to_char(pet, pet_view)

    return True


def general_purpose(caster, target=None):
    """Stub implementation for general_purpose.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def giant_strength(caster, target=None):
    """Stub implementation for giant_strength.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def haggle(caster, target=None):
    """Stub implementation for haggle.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def hand_to_hand(caster, target=None):
    """Stub implementation for hand_to_hand.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def haste(caster, target=None):
    """Stub implementation for haste.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def heal(caster: Character, target: Character | None = None) -> int:
    """ROM ``spell_heal`` fixed healing with warm feeling messaging."""

    target = target or caster
    if target is None:
        raise ValueError("heal requires a target")

    heal_amount = 100
    max_hit = getattr(target, "max_hit", 0)
    if max_hit > 0:
        target.hit = min(target.hit + heal_amount, max_hit)
    else:
        target.hit += heal_amount

    update_pos(target)
    _send_to_char(target, "A warm feeling fills your body.")
    if caster is not target:
        _send_to_char(caster, "Ok.")
    return heal_amount


def heat_metal(caster, target=None):
    """Stub implementation for heat_metal.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def hide(caster, target=None):
    """Stub implementation for hide.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def high_explosive(caster, target=None):
    """Stub implementation for high_explosive.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def holy_word(caster, target=None):
    """Stub implementation for holy_word.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def identify(caster, target=None):
    """Stub implementation for identify.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def infravision(caster, target=None):
    """Stub implementation for infravision.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def invis(caster, target=None):
    """Stub implementation for invis.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def kick(
    caster: Character,
    target: Character | None = None,
    *,
    success: bool | None = None,
    roll: int | None = None,
) -> str:
    """ROM do_kick: strike the current opponent for level-based damage."""

    if caster is None:
        raise ValueError("kick requires a caster")

    opponent = target or getattr(caster, "fighting", None)
    if opponent is None:
        raise ValueError("kick requires an opponent")

    try:
        raw_chance = getattr(caster, "skills", {}).get("kick", 0)
        chance = max(0, min(100, int(raw_chance)))
    except (TypeError, ValueError):
        chance = 0

    if roll is None:
        roll = rng_mm.number_percent()
    if success is None:
        success = chance > roll

    if success:
        level = max(1, int(getattr(caster, "level", 1) or 1))
        damage = rng_mm.number_range(1, level)
    else:
        damage = 0

    return apply_damage(caster, opponent, damage, DamageType.BASH)


def know_alignment(caster, target=None):
    """Stub implementation for know_alignment.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def lightning_bolt(caster, target=None):
    """Stub implementation for lightning_bolt.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def lightning_breath(caster: Character, target: Character | None = None) -> int:
    """ROM spell_lightning_breath with save-for-half."""

    if caster is None or target is None:
        raise ValueError("lightning_breath requires caster and target")

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    _, dam = _breath_damage(
        caster,
        level,
        min_hp=10,
        low_divisor=9,
        high_divisor=5,
        dice_size=20,
    )

    if saves_spell(level, target, DamageType.LIGHTNING):
        shock_effect(target, c_div(level, 2), c_div(dam, 4), SpellTarget.CHAR)
        damage = c_div(dam, 2)
    else:
        shock_effect(target, level, dam, SpellTarget.CHAR)
        damage = dam

    target.hit -= damage
    update_pos(target)
    return damage


def locate_object(caster, target=None):
    """Stub implementation for locate_object.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def lore(caster, target=None):
    """Stub implementation for lore.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def mace(caster, target=None):
    """Stub implementation for mace.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def magic_missile(caster, target=None):
    """Stub implementation for magic_missile.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def mass_healing(caster, target=None):
    """Stub implementation for mass_healing.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def mass_invis(caster, target=None):
    """Stub implementation for mass_invis.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def meditation(caster, target=None):
    """Stub implementation for meditation.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def nexus(caster, target=None):
    """Stub implementation for nexus.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def parry(caster, target=None):
    """Stub implementation for parry.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def pass_door(caster, target=None):
    """Stub implementation for pass_door.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def peek(caster, target=None):
    """Stub implementation for peek.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def pick_lock(caster, target=None):
    """Stub implementation for pick_lock.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def plague(caster, target=None):
    """Stub implementation for plague.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def poison(caster, target=None):
    """Stub implementation for poison.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def polearm(caster, target=None):
    """Stub implementation for polearm.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def portal(caster, target=None):
    """Stub implementation for portal.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def protection_evil(caster, target=None):
    """Stub implementation for protection_evil.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def protection_good(caster, target=None):
    """Stub implementation for protection_good.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def ray_of_truth(caster, target=None):
    """Stub implementation for ray_of_truth.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def recall(caster, target=None):
    """Stub implementation for recall.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def recharge(caster, target=None):
    """Stub implementation for recharge.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def refresh(caster, target=None):
    """Stub implementation for refresh.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def remove_curse(caster, target=None):
    """Stub implementation for remove_curse.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def rescue(
    caster: Character,
    target: Character | None = None,
    *,
    opponent: Character | None = None,
) -> str:
    """ROM ``do_rescue`` tank swap.

    Args:
        caster: Character performing the rescue.
        target: Ally being rescued.
        opponent: Target's opponent (defaults to ``target.fighting``).

    Returns:
        Attacker-facing rescue message mirroring ROM colour codes.
    """

    if caster is None or target is None:
        raise ValueError("rescue requires a caster and target")

    foe = opponent or getattr(target, "fighting", None)
    if foe is None:
        raise ValueError("rescue requires an opponent")

    rescuer_name = getattr(caster, "name", "someone") or "someone"
    victim_name = getattr(target, "name", "someone") or "someone"

    char_msg = f"{{5You rescue {victim_name}!{{x"
    vict_msg = f"{{5{rescuer_name} rescues you!{{x"
    room_msg = f"{{5{rescuer_name} rescues {victim_name}!{{x"

    if hasattr(caster, "messages"):
        caster.messages.append(char_msg)
    if hasattr(target, "messages"):
        target.messages.append(vict_msg)

    room = getattr(caster, "room", None)
    if room is not None:
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is caster or occupant is target:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(room_msg)

    stop_fighting(foe, False)
    stop_fighting(target, False)
    set_fighting(caster, foe)
    set_fighting(foe, caster)

    return char_msg


def sanctuary(caster, target=None):
    """ROM ``spell_sanctuary`` affect application."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("sanctuary requires a target")

    if target.has_affect(AffectFlag.SANCTUARY) or target.has_spell_effect("sanctuary"):
        message = "You are already in sanctuary." if target is caster else f"{target.name} is already in sanctuary."
        if hasattr(caster, "messages"):
            caster.messages.append(message)
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="sanctuary",
        duration=c_div(level, 6),
        level=level,
        affect_flag=AffectFlag.SANCTUARY,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    if hasattr(target, "messages"):
        target.messages.append("You are surrounded by a white aura.")

    room = getattr(target, "room", None)
    if room is not None:
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(
                    f"{target.name} is surrounded by a white aura."
                    if target.name
                    else "Someone is surrounded by a white aura."
                )

    return True


def scrolls(caster, target=None):
    """Stub implementation for scrolls.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def second_attack(caster, target=None):
    """Stub implementation for second_attack.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def shield(caster, target=None):
    """ROM ``spell_shield`` AC reduction aura."""

    target = target or caster
    if caster is None or target is None:
        raise ValueError("shield requires a target")

    if target.has_spell_effect("shield"):
        message = (
            "You are already shielded from harm."
            if target is caster
            else f"{target.name} is already protected by a shield."
        )
        if hasattr(caster, "messages"):
            caster.messages.append(message)
        return False

    level = max(int(getattr(caster, "level", 0) or 0), 0)
    effect = SpellEffect(
        name="shield",
        duration=8 + level,
        level=level,
        ac_mod=-20,
    )
    applied = target.apply_spell_effect(effect)
    if not applied:
        return False

    if hasattr(target, "messages"):
        target.messages.append("You are surrounded by a force shield.")

    room = getattr(target, "room", None)
    if room is not None:
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is target:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(
                    f"{target.name} is surrounded by a force shield."
                    if target.name
                    else "Someone is surrounded by a force shield."
                )

    return True


def shield_block(caster, target=None):
    """Stub implementation for shield_block.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def shocking_grasp(caster, target=None):
    """Stub implementation for shocking_grasp.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def sleep(caster, target=None):
    """Stub implementation for sleep.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def slow(caster, target=None):
    """Stub implementation for slow.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def sneak(caster, target=None):
    """Stub implementation for sneak.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def spear(caster, target=None):
    """Stub implementation for spear.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def staves(caster, target=None):
    """Stub implementation for staves.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def steal(caster, target=None):
    """Stub implementation for steal.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def stone_skin(caster, target=None):
    """Stub implementation for stone_skin.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def summon(caster, target=None):
    """Stub implementation for summon.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def sword(caster, target=None):
    """Stub implementation for sword.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def teleport(caster, target=None):
    """Stub implementation for teleport.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def third_attack(caster, target=None):
    """Stub implementation for third_attack.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def trip(caster, target=None):
    """Stub implementation for trip.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def ventriloquate(caster, target=None):
    """Stub implementation for ventriloquate.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def wands(caster, target=None):
    """Stub implementation for wands.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def weaken(caster, target=None):
    """Stub implementation for weaken.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def whip(caster, target=None):
    """Stub implementation for whip.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def word_of_recall(caster, target=None):
    """Stub implementation for word_of_recall.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect
