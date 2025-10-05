from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mud.combat import multi_hit
from mud.models.constants import OBJ_VNUM_WHISTLE, AffectFlag, CommFlag, PlayerFlag, Position
from mud.registry import room_registry
from mud.skills.registry import skill_registry as global_skill_registry
from mud.utils import rng_mm
from mud.world.vision import can_see_character

spec_fun_registry: dict[str, Callable[..., Any]] = {}


def register_spec_fun(name: str, func: Callable[..., Any]) -> None:
    """Register *func* under *name*, storing key in lowercase."""
    spec_fun_registry[name.lower()] = func


def get_spec_fun(name: str) -> Callable[..., Any] | None:
    """Return a spec_fun for *name* using case-insensitive lookup."""
    return spec_fun_registry.get(name.lower())


def run_npc_specs() -> None:
    """Invoke registered spec_funs for NPCs in all rooms.

    For each NPC (MobInstance) present in any room, if its prototype has a
    non-empty ``spec_fun`` name and a function is registered under that name,
    call it with the mob instance.
    """
    from mud.registry import room_registry

    for room in list(room_registry.values()):
        for entity in list(getattr(room, "people", [])):
            spec_attr = getattr(entity, "spec_fun", None)
            func = None

            if callable(spec_attr):
                func = spec_attr
            elif isinstance(spec_attr, str) and spec_attr:
                func = get_spec_fun(spec_attr)

            if func is None:
                proto = getattr(entity, "prototype", None)
                proto_spec = getattr(proto, "spec_fun", None)
                if callable(proto_spec):
                    func = proto_spec
                elif isinstance(proto_spec, str) and proto_spec:
                    func = get_spec_fun(proto_spec)

            if func is None:
                continue

            try:
                func(entity)
            except Exception:
                # Spec fun failures must not break the tick loop
                continue


def _get_position(ch: Any) -> Position:
    try:
        value = int(getattr(ch, "position", Position.STANDING))
    except Exception:
        value = int(Position.STANDING)
    try:
        return Position(value)
    except ValueError:
        return Position.STANDING


def _is_awake(ch: Any) -> bool:
    return _get_position(ch) > Position.SLEEPING


def _has_affect(ch: Any, flag: AffectFlag) -> bool:
    checker = getattr(ch, "has_affect", None)
    if callable(checker):
        try:
            return bool(checker(flag))
        except Exception:
            return False
    affected = getattr(ch, "affected_by", 0)
    try:
        return bool(int(affected) & int(flag))
    except Exception:
        return False


def _append_message(target: Any, message: str) -> None:
    inbox = getattr(target, "messages", None)
    if isinstance(inbox, list):
        inbox.append(message)


def _clear_comm_flag(ch: Any, flag: CommFlag) -> None:
    try:
        current = int(getattr(ch, "comm", 0) or 0)
    except Exception:
        current = 0
    ch.comm = current & ~int(flag)


def _spec_name(ch: Any) -> str | None:
    spec_attr = getattr(ch, "spec_fun", None)
    if isinstance(spec_attr, str) and spec_attr:
        return spec_attr.lower()
    proto = getattr(ch, "prototype", None)
    proto_spec = getattr(proto, "spec_fun", None)
    if isinstance(proto_spec, str) and proto_spec:
        return proto_spec.lower()
    return None


def _display_name(ch: Any) -> str:
    name = getattr(ch, "name", None) or getattr(ch, "short_descr", None)
    if not name:
        proto = getattr(ch, "prototype", None)
        name = getattr(proto, "short_descr", None) or getattr(proto, "player_name", None)
    return str(name or "Someone")


def _has_player_flag(ch: Any, flag: PlayerFlag) -> bool:
    act = getattr(ch, "act", 0)
    try:
        return bool(int(act) & int(flag))
    except Exception:
        return False


def _room_occupants(room: Any) -> list[Any]:
    people = getattr(room, "people", [])
    return list(people) if isinstance(people, list) else list(people or [])


def _find_fighting_victim(mob: Any) -> Any | None:
    if _get_position(mob) != Position.FIGHTING:
        return None
    room = getattr(mob, "room", None)
    if room is None:
        return None
    fallback = None
    for occupant in _room_occupants(room):
        if getattr(occupant, "fighting", None) is mob and rng_mm.number_bits(2) == 0:
            return occupant
        if getattr(occupant, "fighting", None) is mob and fallback is None:
            fallback = occupant
    return fallback


def _get_skill_registry():
    try:  # Local import avoids circular dependency during initialization
        from mud.world import world_state  # type: ignore
    except Exception:  # pragma: no cover - defensive
        world_state = None  # type: ignore

    registry = None
    if world_state is not None:  # type: ignore[truthy-bool]
        registry = getattr(world_state, "skill_registry", None)
    if registry is None:
        registry = global_skill_registry
    return registry


def _cast_spell(caster: Any, target: Any, spell_name: str) -> bool:
    registry = _get_skill_registry()
    if registry is None:
        return False
    skill = registry.find_spell(caster, spell_name) if hasattr(registry, "find_spell") else None
    handler = None
    if skill is not None:
        handler = registry.handlers.get(skill.name)
    if handler is None:
        handler = registry.handlers.get(spell_name)
    if handler is None:
        return False
    handler(caster, target)
    return True


def _select_spell(mob: Any, table: dict[int, tuple[int, str]], default: tuple[int, str]) -> str:
    level = int(getattr(mob, "level", 0) or 0)
    while True:
        roll = rng_mm.number_bits(4)
        min_level, spell = table.get(roll, default)
        if level >= min_level:
            return spell


def _equipped_items(mob: Any) -> list[Any]:
    equipment = getattr(mob, "equipment", None)
    if isinstance(equipment, dict):
        return [item for item in equipment.values() if item is not None]
    return []


def _find_whistle(mob: Any) -> Any | None:
    for item in _equipped_items(mob):
        proto = getattr(item, "prototype", None)
        vnum = getattr(proto, "vnum", None)
        if vnum == OBJ_VNUM_WHISTLE:
            return item
    return None


def _broadcast_area(room: Any, message: str) -> None:
    area = getattr(room, "area", None)
    if area is None:
        return
    for other_room in list(room_registry.values()):
        if other_room is room:
            continue
        if getattr(other_room, "area", None) is area:
            other_room.broadcast(message)


def _attack(mob: Any, victim: Any) -> None:
    multi_hit(mob, victim)


# --- Minimal ROM-like spec functions (rng_mm parity) ---


def spec_cast_adept(mob: Any) -> bool:
    """Simplified Adept spec that uses ROM RNG.

    ROM's `spec_cast_adept` periodically casts helpful spells on players.
    For parity of RNG usage, we roll `number_percent()` and return True when
    the roll is small. This function exists primarily to validate that the
    Mitchell–Moore RNG wiring matches ROM semantics.
    """
    roll = rng_mm.number_percent()
    # Return True on low roll to signal an action occurred (simplified).
    return roll <= 25


# Convenience registration name matching ROM conventions
register_spec_fun("spec_cast_adept", spec_cast_adept)


# --- Justice system special functions ---


def spec_executioner(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if room is None or not _is_awake(mob) or getattr(mob, "fighting", None) is not None:
        return False

    target = None
    crime = ""
    for occupant in _room_occupants(room):
        if getattr(occupant, "is_npc", False):
            continue
        if _has_player_flag(occupant, PlayerFlag.KILLER) and can_see_character(mob, occupant):
            target = occupant
            crime = "KILLER"
            break
        if _has_player_flag(occupant, PlayerFlag.THIEF) and can_see_character(mob, occupant):
            target = occupant
            crime = "THIEF"
            break

    if target is None:
        return False

    _clear_comm_flag(mob, CommFlag.NOSHOUT)
    declaration = (
        f"{getattr(target, 'name', 'Someone')} is a {crime}!  PROTECT THE INNOCENT!  MORE BLOOOOD!!!"
    )
    _append_message(mob, f"You yell '{declaration}'")
    room.broadcast(f"{_display_name(mob)} yells '{declaration}'", exclude=mob)
    _attack(mob, target)
    return True


def spec_guard(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if room is None or not _is_awake(mob) or getattr(mob, "fighting", None) is not None:
        return False

    target = None
    crime = ""
    max_evil = 300
    fallback = None

    for occupant in _room_occupants(room):
        if getattr(occupant, "is_npc", False):
            # Track evil fighters for fallback targeting
            opponent = getattr(occupant, "fighting", None)
            if opponent is not None and opponent is not mob:
                try:
                    alignment = int(getattr(occupant, "alignment", 0) or 0)
                except Exception:
                    alignment = 0
                if alignment < max_evil:
                    max_evil = alignment
                    fallback = occupant
            continue

        if _has_player_flag(occupant, PlayerFlag.KILLER) and can_see_character(mob, occupant):
            target = occupant
            crime = "KILLER"
            break
        if _has_player_flag(occupant, PlayerFlag.THIEF) and can_see_character(mob, occupant):
            target = occupant
            crime = "THIEF"
            break

        opponent = getattr(occupant, "fighting", None)
        if opponent is not None and opponent is not mob:
            try:
                alignment = int(getattr(occupant, "alignment", 0) or 0)
            except Exception:
                alignment = 0
            if alignment < max_evil:
                max_evil = alignment
                fallback = occupant

    if target is not None:
        _clear_comm_flag(mob, CommFlag.NOSHOUT)
        message = (
            f"{getattr(target, 'name', 'Someone')} is a {crime}!  PROTECT THE INNOCENT!!  BANZAI!!"
        )
        _append_message(mob, f"You yell '{message}'")
        room.broadcast(f"{_display_name(mob)} yells '{message}'", exclude=mob)
        _attack(mob, target)
        return True

    if fallback is not None:
        rally = "PROTECT THE INNOCENT!!  BANZAI!!"
        room.broadcast(f"{_display_name(mob)} screams '{rally}'", exclude=None)
        _attack(mob, fallback)
        return True

    return False


def spec_patrolman(mob: Any) -> bool:
    room = getattr(mob, "room", None)
    if (
        room is None
        or not _is_awake(mob)
        or getattr(mob, "fighting", None) is not None
        or _has_affect(mob, AffectFlag.CALM)
        or _has_affect(mob, AffectFlag.CHARM)
    ):
        return False

    victim = None
    count = 0
    for occupant in _room_occupants(room):
        if occupant is mob:
            continue
        opponent = getattr(occupant, "fighting", None)
        if opponent is None:
            continue
        # Prefer higher level combatant like ROM
        candidate = occupant
        try:
            if int(getattr(opponent, "level", 0) or 0) > int(getattr(occupant, "level", 0) or 0):
                candidate = opponent
        except Exception:
            pass
        if rng_mm.number_range(0, count if count > 0 else 0) == 0:
            victim = candidate
        count += 1

    if victim is None:
        return False

    victim_spec = _spec_name(victim)
    mob_spec = _spec_name(mob)
    if victim_spec is not None and victim_spec == mob_spec and getattr(victim, "is_npc", False):
        return False

    whistle = _find_whistle(mob)
    if whistle is not None:
        descriptor = getattr(whistle, "short_descr", None) or getattr(whistle, "name", "whistle")
        _append_message(mob, f"You blow down hard on {descriptor}.")
        room.broadcast(
            f"{_display_name(mob)} blows on {descriptor}, ***WHEEEEEEEEEEEET***",
            exclude=mob,
        )
        _broadcast_area(room, "You hear a shrill whistling sound.")

    message_map = {
        0: "yells 'All roit! All roit! break it up!'",
        1: "says 'Society's to blame, but what's a bloke to do?'",
        2: "mumbles 'bloody kids will be the death of us all.'",
        3: "shouts 'Stop that! Stop that!' and attacks.",
        4: "pulls out his billy and goes to work.",
        5: "sighs in resignation and proceeds to break up the fight.",
        6: "says 'Settle down, you hooligans!'",
    }
    roll = rng_mm.number_range(0, 6)
    speech = message_map.get(roll)
    if speech is not None:
        room.broadcast(f"{_display_name(mob)} {speech}", exclude=None)

    _attack(mob, victim)
    return True


# --- Caster special functions ---


def spec_cast_cleric(mob: Any) -> bool:
    victim = _find_fighting_victim(mob)
    if victim is None:
        return False

    table = {
        0: (0, "blindness"),
        1: (3, "cause serious"),
        2: (7, "earthquake"),
        3: (9, "cause critical"),
        4: (10, "dispel evil"),
        5: (12, "curse"),
        6: (12, "change sex"),
        7: (13, "flamestrike"),
        8: (15, "harm"),
        9: (15, "harm"),
        10: (15, "harm"),
        11: (15, "plague"),
    }
    default = (16, "dispel magic")
    spell = _select_spell(mob, table, default)
    return _cast_spell(mob, victim, spell)


def spec_cast_mage(mob: Any) -> bool:
    victim = _find_fighting_victim(mob)
    if victim is None:
        return False

    table = {
        0: (0, "blindness"),
        1: (3, "chill touch"),
        2: (7, "weaken"),
        3: (8, "teleport"),
        4: (11, "colour spray"),
        5: (12, "change sex"),
        6: (13, "energy drain"),
        7: (15, "fireball"),
        8: (15, "fireball"),
        9: (15, "fireball"),
        10: (20, "plague"),
    }
    default = (20, "acid blast")
    spell = _select_spell(mob, table, default)
    return _cast_spell(mob, victim, spell)


def spec_cast_undead(mob: Any) -> bool:
    victim = _find_fighting_victim(mob)
    if victim is None:
        return False

    table = {
        0: (0, "curse"),
        1: (3, "weaken"),
        2: (6, "chill touch"),
        3: (9, "blindness"),
        4: (12, "poison"),
        5: (15, "energy drain"),
        6: (18, "harm"),
        7: (21, "teleport"),
        8: (20, "plague"),
    }
    default = (18, "harm")
    spell = _select_spell(mob, table, default)
    return _cast_spell(mob, victim, spell)


def spec_cast_judge(mob: Any) -> bool:
    victim = _find_fighting_victim(mob)
    if victim is None:
        return False
    return _cast_spell(mob, victim, "high explosive")


register_spec_fun("spec_executioner", spec_executioner)
register_spec_fun("spec_guard", spec_guard)
register_spec_fun("spec_patrolman", spec_patrolman)
register_spec_fun("spec_cast_cleric", spec_cast_cleric)
register_spec_fun("spec_cast_mage", spec_cast_mage)
register_spec_fun("spec_cast_undead", spec_cast_undead)
register_spec_fun("spec_cast_judge", spec_cast_judge)
