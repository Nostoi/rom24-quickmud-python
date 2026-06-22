from __future__ import annotations

from collections.abc import Iterable

from mud.characters import is_clan_member
from mud.characters.follow import stop_follower
from mud.combat.kill_table import increment_killed
from mud.models.character import Character, character_registry
from mud.models.clans import get_clan_hall_vnum
from mud.models.constants import (
    ITEM_INVENTORY,
    ITEM_ROT_DEATH,
    ITEM_VIS_DEATH,
    OBJ_VNUM_BRAINS,
    OBJ_VNUM_CORPSE_NPC,
    OBJ_VNUM_CORPSE_PC,
    OBJ_VNUM_GUTS,
    OBJ_VNUM_SEVERED_HEAD,
    OBJ_VNUM_SLICED_ARM,
    OBJ_VNUM_SLICED_LEG,
    OBJ_VNUM_TORN_HEART,
    FormFlag,
    ItemType,
    PartFlag,
    PlayerFlag,
    Position,
    WearFlag,
    WearLocation,
)
from mud.models.obj import ObjIndex
from mud.models.object import Object, create_object
from mud.models.races import get_race_by_index
from mud.spawning.obj_spawner import spawn_object
from mud.utils import rng_mm
from mud.utils.act import act_to_room
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
    obj = create_object(proto)
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


def _get_extra_flags(obj: Object) -> int:
    try:
        return int(getattr(obj, "extra_flags", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return 0


def _clear_extra_flags(obj: Object, flags: int) -> None:
    obj.extra_flags = _get_extra_flags(obj) & ~int(flags)


def _has_extra_flag(obj: Object, flag: int) -> bool:
    return bool(_get_extra_flags(obj) & int(flag))


def _spill_contents_to_room(obj: Object, room) -> None:
    contents = list(getattr(obj, "contained_items", []) or [])
    for contained in contents:
        try:
            obj.contained_items.remove(contained)
        except (AttributeError, ValueError):  # pragma: no cover - defensive guard
            pass
        if hasattr(contained, "location") and getattr(contained, "location", None) is obj:
            contained.location = None
        room.add_object(contained)


def _is_floating_slot(slot: int | None, obj: Object) -> bool:
    if slot is not None:
        try:
            if int(slot) == int(WearLocation.FLOAT):
                return True
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            pass
    try:
        wear_loc = int(getattr(obj, "wear_loc", int(WearLocation.NONE)))
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        wear_loc = int(WearLocation.NONE)
    return wear_loc == int(WearLocation.FLOAT)


def _format_corpse_labels(corpse: Object, name: str) -> None:
    short_template = getattr(corpse.prototype, "short_descr", None) or getattr(
        corpse, "short_descr", "the corpse of %s"
    )
    desc_template = getattr(corpse.prototype, "description", None) or getattr(
        corpse, "description", "The corpse of %s is lying here."
    )
    corpse.short_descr = short_template.replace("%s", name)
    corpse.description = desc_template.replace("%s", name)


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


def _increment_kill_counters(victim: Character) -> None:
    proto = getattr(victim, "prototype", None) or getattr(victim, "mob_index", None)
    if proto is not None:
        try:
            current = int(getattr(proto, "killed", 0) or 0)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            current = 0
        proto.killed = current + 1

    increment_killed(getattr(victim, "level", 0))


def _broadcast_neighbor_cry(victim: Character) -> None:
    room = getattr(victim, "room", None)
    if room is None:
        return

    message = "You hear something's death cry." if getattr(victim, "is_npc", False) else "You hear someone's death cry."

    for exit_data in getattr(room, "exits", []) or []:
        if exit_data is None:
            continue
        target = getattr(exit_data, "to_room", None)
        if target is None or target is room:
            continue
        # mirroring ROM src/fight.c:1685 — act(msg, ch, NULL, NULL, TO_ROOM)
        # per exit, with no MOBtrigger wrap, so an NPC in the adjacent room
        # with a matching TRIG_ACT receives mp_act_trigger (INV-025). The
        # message has no $n, so PERS rendering is identical to a plain
        # broadcast; act_to_room adds the missing TRIG_ACT dispatch.
        act_to_room(target, message, victim)


def death_cry(victim: Character) -> None:
    """Broadcast ROM-style death cry messaging with gore spawns."""

    room = getattr(victim, "room", None)
    if room is None:
        return

    # mirroring ROM src/fight.c:1583 — default msg initialised to "death cry",
    # NOT case 0's text; rolls 8-15 (and cases 2-7 where part is absent) keep it.
    message_template = "You hear $n's death cry."
    gore_spec: tuple[int, str, str, ItemType] | None = None

    roll = rng_mm.number_bits(4)

    if roll == 0:
        # mirroring ROM src/fight.c:1587 case 0
        message_template = "$n hits the ground ... DEAD."
    elif roll == 1:
        # mirroring ROM src/fight.c:1589-1597 case 1 — falls through to case 2
        # only when material != 0 (i.e. non-flesh mobs).
        if not getattr(victim, "material", None):
            message_template = "$n splatters blood on your armor."
        elif _parts_has(victim, PartFlag.GUTS):
            message_template = "$n spills $s guts all over the floor."
            gore_spec = (
                OBJ_VNUM_GUTS,
                "the guts of %s",
                "A steaming pile of %s's entrails is lying here.",
                ItemType.FOOD,
            )
    elif roll == 2:
        # mirroring ROM src/fight.c:1598-1603 case 2 — break is unconditional.
        if _parts_has(victim, PartFlag.GUTS):
            message_template = "$n spills $s guts all over the floor."
            gore_spec = (
                OBJ_VNUM_GUTS,
                "the guts of %s",
                "A steaming pile of %s's entrails is lying here.",
                ItemType.FOOD,
            )
    elif roll == 3:
        if _parts_has(victim, PartFlag.HEAD):
            message_template = "$n's severed head plops on the ground."
            gore_spec = (
                OBJ_VNUM_SEVERED_HEAD,
                "the head of %s",
                "The severed head of %s is lying here.",
                ItemType.TRASH,
            )
    elif roll == 4:
        if _parts_has(victim, PartFlag.HEART):
            message_template = "$n's heart is torn from $s chest."
            gore_spec = (
                OBJ_VNUM_TORN_HEART,
                "the heart of %s",
                "The torn-out heart of %s is lying here.",
                ItemType.FOOD,
            )
    elif roll == 5:
        if _parts_has(victim, PartFlag.ARMS):
            message_template = "$n's arm is sliced from $s dead body."
            gore_spec = (
                OBJ_VNUM_SLICED_ARM,
                "the arm of %s",
                "The sliced-off arm of %s is lying here.",
                ItemType.FOOD,
            )
    elif roll == 6:
        if _parts_has(victim, PartFlag.LEGS):
            message_template = "$n's leg is sliced from $s dead body."
            gore_spec = (
                OBJ_VNUM_SLICED_LEG,
                "the leg of %s",
                "The sliced-off leg of %s is lying here.",
                ItemType.FOOD,
            )
    elif roll == 7:
        if _parts_has(victim, PartFlag.BRAINS):
            message_template = "$n's head is shattered, and $s brains splash all over you."
            gore_spec = (
                OBJ_VNUM_BRAINS,
                "the brains of %s",
                "The splattered brains of %s are lying here.",
                ItemType.FOOD,
            )
    # rolls 8-15: no matching case → message_template stays as "You hear $n's death cry."

    # mirroring ROM src/fight.c:1640 — act(msg, ch, NULL, NULL, TO_ROOM) renders
    # $n through PERS(ch, to) per recipient, so an invisible corpse-to-be masks
    # to "Someone" for a sightless witness (INV-025/INV-027). Baking victim.name
    # via expand_placeholders leaked the name to every listener.
    act_to_room(room, message_template, victim, exclude=victim)

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

    proto = ObjIndex(vnum=vnum, short_descr="the corpse of %s", description="The corpse of %s is lying here.")
    proto.item_type = int(item_type)
    corpse = create_object(proto)
    corpse.item_type = int(item_type)
    return corpse


def _strip_inventory(victim: Character) -> list[tuple[Object, bool]]:
    """Remove carried/equipped objects returning ``(obj, was_floating)`` tuples."""

    items: list[tuple[Object, bool]] = []
    inventory: Iterable = list(getattr(victim, "inventory", []) or [])
    for obj in inventory:
        victim.remove_object(obj)
        obj.location = None
        obj.wear_loc = int(WearLocation.NONE)
        items.append((obj, False))
    equipment = getattr(victim, "equipment", {}) or {}
    for slot, obj in list(equipment.items()):
        was_floating = _is_floating_slot(slot, obj)
        victim.remove_object(obj)
        obj.location = None
        obj.wear_loc = int(WearLocation.NONE)
        items.append((obj, was_floating))
    return items


def _handle_corpse_item(
    corpse: Object,
    room,
    obj: Object,
    *,
    was_floating: bool,
) -> None:
    """Apply ROM corpse-handling semantics for *obj*."""

    if obj is None or room is None:
        return

    item_type = _normalize_item_type(getattr(obj, "item_type", None), ItemType.TRASH)
    if item_type == int(ItemType.POTION):
        obj.timer = rng_mm.number_range(500, 1000)
    elif item_type == int(ItemType.SCROLL):
        obj.timer = rng_mm.number_range(1000, 2500)

    had_rot_death = _has_extra_flag(obj, ITEM_ROT_DEATH)
    if had_rot_death and not was_floating:
        obj.timer = rng_mm.number_range(5, 10)
        _clear_extra_flags(obj, ITEM_ROT_DEATH)

    _clear_extra_flags(obj, ITEM_VIS_DEATH)

    if _has_extra_flag(obj, ITEM_INVENTORY):
        return

    if was_floating:
        if had_rot_death:
            _spill_contents_to_room(obj, room)
            return
        room.add_object(obj)
        return

    # INV-039 / class-13: ROM src/fight.c:1472 obj_to_obj head-inserts each
    # item into the corpse. Route through the contained-items chokepoint.
    contained = getattr(corpse, "contained_items", None)
    if isinstance(contained, list):
        contained.insert(0, obj)
    if hasattr(obj, "location"):
        obj.location = corpse


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
    try:
        wear_flags = int(getattr(corpse, "wear_flags", 0) or 0)
    except (TypeError, ValueError):
        wear_flags = 0
    corpse.wear_flags = wear_flags | int(WearFlag.TAKE)
    corpse.cost = 0
    corpse.level = int(getattr(victim, "level", 0) or 0)
    corpse.timer = rng_mm.number_range(3, 6) if is_npc else rng_mm.number_range(25, 40)

    gold = max(0, int(getattr(victim, "gold", 0) or 0))
    silver = max(0, int(getattr(victim, "silver", 0) or 0))

    # ROM make_corpse money transfer is NPC/PC-split.
    # - NPC (src/fight.c:1473): `if (ch->gold > 0)` ONLY — a mob carrying silver
    #   but zero gold mints NO money object; the silver is lost on extraction.
    # - PC (src/fight.c:1483-1495): non-clan corpses are owner-locked and keep
    #   all coins on the PC; clan corpses are unowned and drop half the coins
    #   when either denomination is > 1. FIGHT-079 fixed the previous full-coin
    #   drop + zeroing approximation.
    # FIGHT-078: the silver-only NPC case dropped phantom silver before this gate.
    money_gold = gold
    money_silver = silver
    if not is_npc:
        money_gold = 0
        money_silver = 0
        if is_clan_member(victim) and (gold > 1 or silver > 1):
            money_gold = gold // 2
            money_silver = silver // 2

    money_gate = gold > 0 if is_npc else (money_gold > 0 or money_silver > 0)
    if money_gate:
        from mud.handler import create_money

        money_obj = create_money(money_gold, money_silver)
        if money_obj:
            # INV-039 / class-13: ROM src/handler.c:1968 obj_to_obj head-inserts.
            corpse.contained_items.insert(0, money_obj)
            # ROM src/handler.c:1968 obj_to_obj — money lives inside corpse,
            # so in_obj=corpse, in_room=None, carried_by=None.
            money_obj.location = corpse

    if not is_npc:
        _clear_player_flag(victim, PlayerFlag.CANLOOT)
        if not is_clan_member(victim):
            corpse.owner = getattr(victim, "name", None)
        else:
            corpse.owner = None
            victim.gold = gold - money_gold
            victim.silver = silver - money_silver
    else:
        victim.gold = 0
        victim.silver = 0

    if is_npc:
        name = getattr(victim, "short_descr", None) or getattr(victim, "name", "someone")
    else:
        name = getattr(victim, "name", "someone")
    if isinstance(name, str):
        _format_corpse_labels(corpse, name)

    for obj, was_floating in _strip_inventory(victim):
        _handle_corpse_item(corpse, room, obj, was_floating=was_floating)

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


def _nuke_pets(victim: Character, room) -> None:
    """Dismiss charmed pets when their owner is extracted."""

    pet = getattr(victim, "pet", None)
    if pet is None:
        return

    try:
        stop_follower(pet)
    except Exception:  # pragma: no cover - defensive guard
        pet.master = None
        pet.leader = None

    victim.pet = None

    pet_room = getattr(pet, "room", None) or room
    if pet_room is not None:
        # mirroring ROM src/act_comm.c:1648 — act("$N slowly fades away.", ch,
        # NULL, pet, TO_NOTVICT): $N renders via PERS(pet, to) per recipient (an
        # invisible pet masks to "someone", INV-027), TO_NOTVICT excludes BOTH
        # the owner (ch) and the pet, and — with no MOBtrigger wrap — dispatches
        # TRIG_ACT to listening NPCs (INV-025). act_to_room auto-excludes the
        # actor (owner); exclude=pet supplies the second TO_NOTVICT exclusion.
        act_to_room(pet_room, "$N slowly fades away.", victim, arg2=pet, exclude=pet)
        pet_room.remove_character(pet)

    for obj in list(getattr(pet, "inventory", []) or []):
        try:
            pet.remove_object(obj)
        except Exception:  # pragma: no cover - defensive guard
            try:
                pet.inventory.remove(obj)
            except (AttributeError, ValueError):
                pass
        if hasattr(obj, "location") and getattr(obj, "location", None) is pet:
            obj.location = None

    for _, equipped in list(getattr(pet, "equipment", {}).items()):
        try:
            pet.remove_object(equipped)
        except Exception:  # pragma: no cover - defensive guard
            pass
        if hasattr(equipped, "location") and getattr(equipped, "location", None) is pet:
            equipped.location = None

    # mirroring ROM src/handler.c:2121 — extract_char calls stop_fighting(pet, TRUE)
    # before removing the pet from char_list, clearing fighting pointers on all
    # characters that were fighting the pet (and the pet's own pointer).
    # Without this, enemies fighting the charmed pet get ghost pointers after
    # nuke_pets; must run while pet is still in character_registry.
    # INV-043 enforcement point.
    from mud.combat.engine import stop_fighting as _stop_fighting

    _stop_fighting(pet, both=True)

    try:
        character_registry.remove(pet)
    except ValueError:
        pass


def clear_extract_target_refs(victim: Character) -> None:
    """Clear dangling single-target pointers aimed at an extracted character.

    Mirrors ROM ``extract_char``'s ``char_list`` walk (``src/handler.c:2151-2157``)
    that nullifies two pointers on EVERY extraction:

        for (wch = char_list; wch != NULL; wch = wch->next)
        {
            if (wch->reply == ch)        wch->reply = NULL;
            if (ch->mprog_target == wch) wch->mprog_target = NULL;
        }

    The ``reply`` line is correct dangling-pointer hygiene. The ``mprog_target``
    line is a faithfully-replicated ROM 2.4b6 quirk: it tests the *extracted*
    char's target (``ch->mprog_target == wch``) and clears *that target's* OWN
    ``mprog_target`` — so it does NOT clear mobs whose ``mprog_target`` points AT
    the extracted char, and it DOES wipe the remembered target of whoever the
    extracted char was targeting. We replicate the buggy line verbatim, not the
    "corrected" ``wch->mprog_target == ch`` form many derivatives shipped.

    INV-047: ROM has a single ``extract_char`` that always runs this loop; the
    Python port split extraction across several call sites, so this helper is the
    shared cleanup every extract path must invoke (``_extract_character``, the
    ``do_quit``/link-dead leg, and the clean-disconnect teardown).
    """
    from mud.models.character import character_registry

    victim_target = getattr(victim, "mprog_target", None)
    for other in list(character_registry):
        if other is victim:
            continue
        if getattr(other, "reply", None) is victim:
            other.reply = None
        if victim_target is other:
            other.mprog_target = None


def extract_carried_objects(victim: Character) -> None:
    """Extract every object a character is carrying or wearing.

    Mirrors ROM ``extract_char`` (``src/handler.c:2123-2127``)::

        for (obj = ch->carrying; obj != NULL; obj = obj_next)
        {
            obj_next = obj->next_content;
            extract_obj (obj);
        }

    In ROM, worn items live on ``ch->carrying`` (they only carry an extra
    ``wear_loc``), so a single walk frees inventory AND equipment. The Python
    port splits them into ``char.inventory`` and the ``char.equipment`` dict, so
    a faithful "extract all carrying" must drain BOTH — otherwise a quitting /
    disconnecting PC leaves their objects lingering in ``object_registry``
    (phantom-object leak, the INV-046 class on the extract path).

    INV-020 step (v): ROM has a single ``extract_char`` that always runs this
    loop; the Python port split extraction across call sites, so this is the
    shared object-cleanup every extract path must invoke.
    """
    from mud.game_loop import _extract_obj

    for obj in list(getattr(victim, "inventory", []) or []):
        _extract_obj(obj)
    equipment = getattr(victim, "equipment", None)
    if isinstance(equipment, dict):
        for obj in list(equipment.values()):
            _extract_obj(obj)


def _move_player_to_death_room(victim: Character) -> None:
    """Place the player in their clan hall or the global death room."""

    hall_vnum = get_clan_hall_vnum(getattr(victim, "clan", 0))
    room = get_room(hall_vnum)
    if room is not None:
        room.add_character(victim)


def raw_kill(victim: Character) -> Object | None:
    """Handle character death by creating a corpse and removing the victim."""

    from mud.characters.follow import die_follower
    from mud.combat.engine import stop_fighting as _stop_fighting

    # TRIG_DEATH fired in _handle_death (engine.py) after group_gain, before raw_kill.
    # ROM Reference: src/fight.c:918-924 (mp_percent_trigger then raw_kill)

    _nuke_pets(victim, room=getattr(victim, "room", None))

    # mirroring ROM src/handler.c:2120-2122 — die_follower is gated behind
    # fPull=TRUE (NPCs only).  ROM raw_kill calls extract_char(victim, IS_NPC),
    # so PC death (fPull=FALSE) does NOT dissolve group/follower relationships.
    if getattr(victim, "is_npc", False):
        die_follower(victim)

    _stop_fighting(victim, True)
    death_cry(victim)
    corpse = make_corpse(victim)

    room = getattr(victim, "room", None)
    if room is not None:
        room.remove_character(victim)

    if getattr(victim, "is_npc", False):
        _increment_kill_counters(victim)
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
