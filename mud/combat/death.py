from __future__ import annotations

from collections.abc import Iterable

from mud.characters import is_clan_member
from mud.models.character import Character, character_registry
from mud.models.constants import (
    FormFlag,
    ItemType,
    PartFlag,
    PlayerFlag,
    Position,
    OBJ_VNUM_BRAINS,
    OBJ_VNUM_CORPSE_NPC,
    OBJ_VNUM_CORPSE_PC,
    OBJ_VNUM_GUTS,
    OBJ_VNUM_SEVERED_HEAD,
    OBJ_VNUM_SLICED_ARM,
    OBJ_VNUM_SLICED_LEG,
    OBJ_VNUM_TORN_HEART,
)
from mud.models.clans import get_clan_hall_vnum
from mud.models.races import get_race_by_index
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.social import expand_placeholders
from mud.spawning.obj_spawner import spawn_object
from mud.utils import rng_mm
from mud.world.world_state import get_room


def _clear_player_flag(character: Character, flag: PlayerFlag) -> None:
    """Clear *flag* from the player's act bitfield."""

    try:
        character.act = int(getattr(character, "act", 0)) & ~int(flag)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        character.act = 0


def _parts_has(victim: Character, flag: PartFlag) -> bool:
    try:
        parts = int(getattr(victim, "parts", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return False
    return bool(parts & int(flag))


def _form_has(victim: Character, flag: FormFlag) -> bool:
    try:
        form = int(getattr(victim, "form", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return False
    return bool(form & int(flag))


def _fallback_gore(
    vnum: int,
    *,
    short_template: str,
    description_template: str,
    item_type: ItemType,
) -> Object:
    proto = ObjIndex(
        vnum=vnum,
        short_descr=short_template,
        description=description_template,
    )
    proto.item_type = int(item_type)
    obj = Object(instance_id=None, prototype=proto)
    obj.item_type = int(item_type)
    return obj


def _format_gore_object(
    obj: Object,
    name: str,
    *,
    short_template: str,
    description_template: str,
) -> None:
    template_short = getattr(obj.prototype, "short_descr", None) or short_template
    template_desc = getattr(obj.prototype, "description", None) or description_template
    obj.short_descr = template_short.replace("%s", name)
    obj.description = template_desc.replace("%s", name)


def _normalize_item_type(value: object, default: ItemType) -> int:
    if isinstance(value, str):
        mapping = {
            "food": int(ItemType.FOOD),
            "trash": int(ItemType.TRASH),
            "corpse_npc": int(ItemType.CORPSE_NPC),
            "corpse_pc": int(ItemType.CORPSE_PC),
        }
        return mapping.get(value.lower(), int(default))
    try:
        return int(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return int(default)


def _spawn_gore(
    victim: Character,
    vnum: int,
    *,
    short_template: str,
    description_template: str,
    default_item_type: ItemType,
) -> None:
    room = getattr(victim, "room", None)
    if room is None:
        return

    gore = spawn_object(vnum)
    if gore is None:
        gore = _fallback_gore(
            vnum,
            short_template=short_template,
            description_template=description_template,
            item_type=default_item_type,
        )

    name = getattr(victim, "short_descr", None) or getattr(victim, "name", "someone")
    _format_gore_object(
        gore,
        name,
        short_template=short_template,
        description_template=description_template,
    )

    gore.timer = rng_mm.number_range(4, 7)

    gore.item_type = _normalize_item_type(getattr(gore, "item_type", None), default_item_type)

    if gore.item_type == int(ItemType.FOOD):
        if _form_has(victim, FormFlag.POISON):
            values = list(getattr(gore, "value", []) or [])
            while len(values) <= 3:
                values.append(0)
            values[3] = 1
            gore.value = values
        elif not _form_has(victim, FormFlag.EDIBLE):
            gore.item_type = int(ItemType.TRASH)

    room.add_object(gore)


def _broadcast_neighbor_cry(victim: Character) -> None:
    room = getattr(victim, "room", None)
    if room is None:
        return

    message = (
        "You hear something's death cry."
        if getattr(victim, "is_npc", False)
        else "You hear someone's death cry."
    )

    for exit_data in getattr(room, "exits", []) or []:
        if exit_data is None:
            continue
        target = getattr(exit_data, "to_room", None)
        if target is None or target is room:
            continue
        target.broadcast(message)


def death_cry(victim: Character) -> None:
    """Broadcast ROM-style death cry messaging with gore spawns."""

    room = getattr(victim, "room", None)
    if room is None:
        return

    message_template = "$n hits the ground ... DEAD."
    gore_spec: tuple[int, str, str, ItemType] | None = None

    roll = rng_mm.number_bits(4)

    while True:
        if roll == 0:
            break
        if roll == 1:
            if not getattr(victim, "material", None):
                message_template = "$n splatters blood on your armor."
                break
            roll = 2
            continue
        if roll == 2:
            if _parts_has(victim, PartFlag.GUTS):
                message_template = "$n spills $s guts all over the floor."
                gore_spec = (
                    OBJ_VNUM_GUTS,
                    "the guts of %s",
                    "A steaming pile of %s's entrails is lying here.",
                    ItemType.FOOD,
                )
                break
            roll = 3
            continue
        if roll == 3:
            if _parts_has(victim, PartFlag.HEAD):
                message_template = "$n's severed head plops on the ground."
                gore_spec = (
                    OBJ_VNUM_SEVERED_HEAD,
                    "the head of %s",
                    "The severed head of %s is lying here.",
                    ItemType.TRASH,
                )
                break
            roll = 4
            continue
        if roll == 4:
            if _parts_has(victim, PartFlag.HEART):
                message_template = "$n's heart is torn from $s chest."
                gore_spec = (
                    OBJ_VNUM_TORN_HEART,
                    "the heart of %s",
                    "The torn-out heart of %s is lying here.",
                    ItemType.FOOD,
                )
                break
            roll = 5
            continue
        if roll == 5:
            if _parts_has(victim, PartFlag.ARMS):
                message_template = "$n's arm is sliced from $s dead body."
                gore_spec = (
                    OBJ_VNUM_SLICED_ARM,
                    "the arm of %s",
                    "The sliced-off arm of %s is lying here.",
                    ItemType.FOOD,
                )
                break
            roll = 6
            continue
        if roll == 6:
            if _parts_has(victim, PartFlag.LEGS):
                message_template = "$n's leg is sliced from $s dead body."
                gore_spec = (
                    OBJ_VNUM_SLICED_LEG,
                    "the leg of %s",
                    "The sliced-off leg of %s is lying here.",
                    ItemType.FOOD,
                )
                break
            roll = 7
            continue
        if roll == 7:
            if _parts_has(victim, PartFlag.BRAINS):
                message_template = "$n's head is shattered, and $s brains splash all over you."
                gore_spec = (
                    OBJ_VNUM_BRAINS,
                    "the brains of %s",
                    "The splattered brains of %s are lying here.",
                    ItemType.FOOD,
                )
                break
        break

    room.broadcast(expand_placeholders(message_template, victim), exclude=victim)

    if gore_spec is not None:
        _spawn_gore(
            victim,
            gore_spec[0],
            short_template=gore_spec[1],
            description_template=gore_spec[2],
            default_item_type=gore_spec[3],
        )

    _broadcast_neighbor_cry(victim)


def _fallback_corpse(vnum: int, *, item_type: ItemType) -> Object:
    """Return a minimal corpse object when the real prototype is missing."""

    proto = ObjIndex(vnum=vnum, short_descr="a corpse", description="The corpse of someone lies here.")
    proto.item_type = int(item_type)
    corpse = Object(instance_id=None, prototype=proto)
    corpse.item_type = int(item_type)
    return corpse


def _strip_inventory(victim: Character) -> list:
    """Remove and return all carried and equipped objects from *victim*."""

    items: list = []
    inventory: Iterable = list(getattr(victim, "inventory", []) or [])
    for obj in inventory:
        victim.remove_object(obj)
        items.append(obj)
    equipment = getattr(victim, "equipment", {}) or {}
    for obj in list(equipment.values()):
        victim.remove_object(obj)
        items.append(obj)
    return items


def _set_corpse_coins(corpse: Object, gold: int, silver: int) -> None:
    """Persist coin totals on the corpse and mirror into ``value[0:2]``."""

    corpse.gold = gold
    corpse.silver = silver
    values = list(getattr(corpse, "value", []) or [])
    while len(values) < 2:
        values.append(0)
    values[0] = gold
    values[1] = silver
    corpse.value = values


def make_corpse(victim: Character) -> Object | None:
    """Create a corpse for *victim* mirroring ROM ``make_corpse`` semantics."""

    room = getattr(victim, "room", None)
    if room is None:
        return None

    is_npc = bool(getattr(victim, "is_npc", False))
    vnum = OBJ_VNUM_CORPSE_NPC if is_npc else OBJ_VNUM_CORPSE_PC
    corpse = spawn_object(vnum)
    if corpse is None:
        corpse = _fallback_corpse(vnum, item_type=ItemType.CORPSE_NPC if is_npc else ItemType.CORPSE_PC)
    corpse.item_type = int(ItemType.CORPSE_NPC if is_npc else ItemType.CORPSE_PC)
    corpse.cost = 0
    corpse.level = int(getattr(victim, "level", 0) or 0)
    corpse.timer = rng_mm.number_range(3, 6) if is_npc else rng_mm.number_range(25, 40)

    gold = max(0, int(getattr(victim, "gold", 0) or 0))
    silver = max(0, int(getattr(victim, "silver", 0) or 0))
    _set_corpse_coins(corpse, gold, silver)
    victim.gold = max(0, int(getattr(victim, "gold", 0) or 0) - gold)
    victim.silver = max(0, int(getattr(victim, "silver", 0) or 0) - silver)

    if not is_npc:
        _clear_player_flag(victim, PlayerFlag.CANLOOT)
        if not is_clan_member(victim):
            corpse.owner = getattr(victim, "name", None)

    for obj in _strip_inventory(victim):
        corpse.contained_items.append(obj)
        if hasattr(obj, "location"):
            obj.location = corpse

    room.add_object(corpse)
    return corpse


def _clear_spell_effects(victim: Character) -> None:
    """Remove all active spell effects restoring stat deltas."""

    if not hasattr(victim, "spell_effects"):
        return
    spell_effects = getattr(victim, "spell_effects", {})
    if not isinstance(spell_effects, dict):
        return
    if hasattr(victim, "remove_spell_effect"):
        for name in list(spell_effects.keys()):
            victim.remove_spell_effect(name)
    spell_effects.clear()


def _restore_race_affects(victim: Character) -> None:
    """Reset base affect flags from the character's race entry."""

    race = get_race_by_index(getattr(victim, "race", 0))
    if race is None:
        victim.affected_by = 0
        return
    victim.affected_by = int(getattr(race, "affect_flags", 0))


def _reset_player_armor(victim: Character) -> None:
    """Restore ROM default armor values (100 per AC slot)."""

    victim.armor = [100, 100, 100, 100]


def _move_player_to_death_room(victim: Character) -> None:
    """Place the player in their clan hall or the global death room."""

    hall_vnum = get_clan_hall_vnum(getattr(victim, "clan", 0))
    room = get_room(hall_vnum)
    if room is not None:
        room.add_character(victim)


def raw_kill(victim: Character) -> Object | None:
    """Handle character death by creating a corpse and removing the victim."""

    from mud.combat.engine import stop_fighting as _stop_fighting

    _stop_fighting(victim, True)
    death_cry(victim)
    corpse = make_corpse(victim)

    room = getattr(victim, "room", None)
    if room is not None:
        room.remove_character(victim)

    if getattr(victim, "is_npc", False):
        victim.fighting = None
        try:
            character_registry.remove(victim)
        except ValueError:  # pragma: no cover - defensive guard
            pass
        return corpse

    _clear_spell_effects(victim)
    _restore_race_affects(victim)
    _reset_player_armor(victim)

    victim.fighting = None
    victim.position = Position.RESTING
    victim.hit = max(1, int(getattr(victim, "hit", 0) or 0))
    victim.mana = max(1, int(getattr(victim, "mana", 0) or 0))
    victim.move = max(1, int(getattr(victim, "move", 0) or 0))
    victim.timer = 0
    _move_player_to_death_room(victim)
    return corpse


__all__ = ["death_cry", "make_corpse", "raw_kill"]
