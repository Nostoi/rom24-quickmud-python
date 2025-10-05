from __future__ import annotations

# Auto-generated skill handlers
# TODO: Replace stubs with actual ROM spell/skill implementations
from mud.affects.saves import check_dispel, saves_spell
from mud.combat.engine import apply_damage, attack_round, get_wielded_weapon, update_pos
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
from mud.models.constants import AffectFlag, DamageType, Position
from mud.utils import rng_mm


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


def blindness(caster, target=None):
    """Stub implementation for blindness.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


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

    level = max(getattr(caster, "level", 0), 0)
    dice_level = max(0, c_div(level, 2))
    damage = rng_mm.dice(dice_level, 8)

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


def charm_person(caster, target=None):
    """Stub implementation for charm_person.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def chill_touch(caster, target=None):
    """Stub implementation for chill_touch.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def colour_spray(caster, target=None):
    """Stub implementation for colour_spray.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


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


def create_food(caster, target=None):
    """Stub implementation for create_food.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def create_rose(caster, target=None):
    """Stub implementation for create_rose.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def create_spring(caster, target=None):
    """Stub implementation for create_spring.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def create_water(caster, target=None):
    """Stub implementation for create_water.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def cure_blindness(caster, target=None):
    """Stub implementation for cure_blindness.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def cure_critical(caster, target=None):
    """Stub implementation for cure_critical.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def cure_disease(caster, target=None):
    """Stub implementation for cure_disease.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def cure_light(caster: Character, target: Character | None = None) -> int:
    """ROM spell_cure_light: heal dice(1,8) + level/3."""
    target = target or caster
    if target is None:
        raise ValueError("cure_light requires a target")

    level = max(getattr(caster, "level", 0), 0)
    heal = rng_mm.dice(1, 8) + c_div(level, 3)

    max_hit = getattr(target, "max_hit", 0)
    if max_hit > 0:
        target.hit = min(target.hit + heal, max_hit)
    else:
        target.hit += heal

    update_pos(target)
    return heal


def cure_poison(caster, target=None):
    """Stub implementation for cure_poison.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def cure_serious(caster, target=None):
    """Stub implementation for cure_serious.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def curse(caster, target=None):
    """Stub implementation for curse.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def dagger(caster, target=None):
    """Stub implementation for dagger.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def demonfire(caster, target=None):
    """Stub implementation for demonfire.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def detect_evil(caster, target=None):
    """Stub implementation for detect_evil.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def detect_good(caster, target=None):
    """Stub implementation for detect_good.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def detect_hidden(caster, target=None):
    """Stub implementation for detect_hidden.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def detect_invis(caster, target=None):
    """Stub implementation for detect_invis.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def detect_magic(caster, target=None):
    """Stub implementation for detect_magic.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def detect_poison(caster, target=None):
    """Stub implementation for detect_poison.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


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


def dispel_evil(caster, target=None):
    """Stub implementation for dispel_evil.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def dispel_good(caster, target=None):
    """Stub implementation for dispel_good.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


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


def floating_disc(caster, target=None):
    """Stub implementation for floating_disc.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def fly(caster, target=None):
    """Stub implementation for fly.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def frenzy(caster, target=None):
    """Stub implementation for frenzy.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


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

        if primary_damage == 0 and (
            (target is None) or person is target
        ):
            primary_damage = actual

    return primary_damage


def gate(caster, target=None):
    """Stub implementation for gate.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


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


def heal(caster, target=None):
    """Stub implementation for heal.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


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


def rescue(caster, target=None):
    """Stub implementation for rescue.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


def sanctuary(caster, target=None):
    """Stub implementation for sanctuary.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


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
    """Stub implementation for shield.
    TODO: Implement actual ROM logic from C source.
    """
    return 42  # Placeholder damage/effect


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
