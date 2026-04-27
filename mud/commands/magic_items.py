"""
Magic item commands (recite, brandish, zap).

ROM Reference: src/act_obj.c lines 1910-2157

This module mirrors ROM 2.4b6 do_recite/do_brandish/do_zap line-by-line:
- HOLD-slot lookup uses WearLocation.HOLD enum key (POUR-004 pattern)
- ItemType.SCROLL / STAFF / WAND (no ITEM_ prefix)
- WAIT_STATE applied via ch.wait before any charge gate
- Skill chance: 20 + c_div(skill * 4, 5) using number_percent (rng_mm)
- Messages routed through act_format + broadcast_room
- Spell dispatch delegates to obj_manipulation._obj_cast_spell
- Charges decremented after the cast attempt; destruction broadcast last
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.commands.obj_manipulation import _extract_obj, _obj_cast_spell
from mud.math.c_compat import c_div
from mud.models.constants import ItemType, WearLocation
from mud.net.protocol import broadcast_room
from mud.skills.registry import check_improve, skill_registry
from mud.utils import rng_mm
from mud.utils.act import act_format
from mud.world.char_find import get_char_room as _get_char_room
from mud.world.obj_find import get_obj_carry, get_obj_here as _get_obj_here

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.object import Object


# ROM PULSE_VIOLENCE = 3 * PULSE_PER_SECOND; combat engine uses 3 (see mud/combat/engine.py:293).
_PULSE_VIOLENCE = 3


def _skill_percent(character: "Character", name: str) -> int:
    """Return character's learned percent for ``name`` (0-100)."""
    pcdata = getattr(character, "pcdata", None)
    if not pcdata:
        return 0
    learned = getattr(pcdata, "learned", {})
    return int(learned.get(name, 0))


def _find_obj_here(ch: "Character", name: str) -> "Object | None":
    """ROM get_obj_here scoped to actor's room (visible items)."""
    return _get_obj_here(ch, name)


def _get_value(obj, idx: int, default: int = 0) -> int:
    """Safe accessor for obj.value[idx]."""
    values = getattr(obj, "value", None) or []
    if idx < len(values) and values[idx] is not None:
        try:
            return int(values[idx])
        except (TypeError, ValueError):
            return default
    return default


def _get_value_raw(obj, idx: int, default=None):
    """Raw accessor (preserves str spell names) for obj.value[idx]."""
    values = getattr(obj, "value", None) or []
    if idx < len(values) and values[idx] is not None:
        return values[idx]
    return default


def _set_value(obj, idx: int, val) -> None:
    values = getattr(obj, "value", None)
    if values is None:
        values = [0, 0, 0, 0, 0]
        obj.value = values
    while len(values) <= idx:
        values.append(0)
    values[idx] = val


def _resolve_target_kind(spell_name: str) -> str:
    """Return the target kind ('ignore'/'victim'/'friendly'/'self'/'object'/'character_or_object')."""
    skill = skill_registry.skills.get(spell_name)
    if skill is None:
        return "ignore"
    return getattr(skill, "target", "ignore") or "ignore"


def _broadcast(room, msg: str, *, exclude=None) -> None:
    """Broadcast ``msg`` to room, supporting an iterable ``exclude`` set.

    ``broadcast_room`` only accepts a single character; for ROM TO_NOTVICT we
    need to skip both actor and victim, so iterate manually when given a set.
    """
    if room is None or not msg:
        return
    if exclude is None or not isinstance(exclude, (list, tuple)):
        broadcast_room(room, msg, exclude=exclude)
        return
    skip = list(exclude)
    for char in list(getattr(room, "people", [])):
        if any(char is s for s in skip):
            continue
        msgs = getattr(char, "messages", None)
        if msgs is not None:
            msgs.append(msg)


def do_recite(ch: "Character", args: str) -> str:
    """Recite a scroll. ROM src/act_obj.c:1910-1974."""
    parts = (args or "").split()
    arg1 = parts[0] if parts else ""
    arg2 = parts[1] if len(parts) > 1 else ""

    if not arg1:
        return "What do you want to recite?"

    # ROM 1921: get_obj_carry(ch, arg1, ch)
    scroll = get_obj_carry(ch, arg1)
    if scroll is None:
        return "You do not have that scroll."

    # ROM 1927
    if scroll.item_type != int(ItemType.SCROLL):
        return "You can recite only scrolls."

    # ROM 1933 — level gate
    if int(getattr(ch, "level", 0)) < int(getattr(scroll, "level", 0)):
        return "This scroll is too complex for you to comprehend."

    victim: "Character | None" = None
    target_obj: "Object | None" = None
    if not arg2:
        # ROM 1942 — default to self
        victim = ch
    else:
        victim = _get_char_room(ch, arg2)
        if victim is None:
            target_obj = _find_obj_here(ch, arg2)
        if victim is None and target_obj is None:
            return "You can't find it."

    room = getattr(ch, "room", None)
    # ROM 1955-1956: act() pair fires before skill check
    _broadcast(room, act_format("$n recites $p.", recipient=None, actor=ch, arg1=scroll), exclude=ch)
    self_msg = act_format("You recite $p.", recipient=ch, actor=ch, arg1=scroll)

    # ROM 1958: number_percent() >= 20 + skill * 4 / 5  (failure branch)
    skill_pct = _skill_percent(ch, "scrolls")
    chance = 20 + c_div(skill_pct * 4, 5)
    if rng_mm.number_percent() >= chance:
        # ROM 1960
        out = self_msg + "\n\rYou mispronounce a syllable."
        check_improve(ch, "scrolls", False, 2)
    else:
        # ROM 1966-1968: cast all three slots
        spell_level = _get_value(scroll, 0, int(getattr(ch, "level", 1)))
        for slot in (1, 2, 3):
            spell = _get_value_raw(scroll, slot)
            if spell:
                _obj_cast_spell(spell, spell_level, ch, victim, target_obj)
        check_improve(ch, "scrolls", True, 2)
        out = self_msg

    # ROM 1972: extract_obj(scroll)
    _extract_obj(ch, scroll)
    return out


def _hold_slot(ch: "Character"):
    """ROM get_eq_char(ch, WEAR_HOLD). Equipment dict keyed by WearLocation.HOLD."""
    equipment = getattr(ch, "equipment", None) or {}
    return equipment.get(WearLocation.HOLD)


def _clear_hold(ch: "Character") -> None:
    equipment = getattr(ch, "equipment", None) or {}
    equipment.pop(WearLocation.HOLD, None)


def do_brandish(ch: "Character", args: str) -> str:
    """Brandish a staff. ROM src/act_obj.c:1978-2064."""
    staff = _hold_slot(ch)

    # ROM 1985
    if staff is None:
        return "You hold nothing in your hand."

    # ROM 1991
    if staff.item_type != int(ItemType.STAFF):
        return "You can brandish only with a staff."

    spell_name = _get_value_raw(staff, 3)
    # ROM 1997-2002: bad sn check (sn<0 || sn>=MAX_SKILL || spell_fun==0)
    if not spell_name:
        return ""  # ROM bugs out silently; suppress output

    # ROM 2004: WAIT_STATE BEFORE charge check
    ch.wait = max(getattr(ch, "wait", 0), 2 * _PULSE_VIOLENCE)

    room = getattr(ch, "room", None)
    out_lines: list[str] = []

    charges = _get_value(staff, 2, 0)
    # ROM 2006: if (staff->value[2] > 0)
    if charges > 0:
        # ROM 2008-2009: act pair
        _broadcast(room, act_format("$n brandishes $p.", recipient=None, actor=ch, arg1=staff), exclude=ch)
        out_lines.append(act_format("You brandish $p.", recipient=ch, actor=ch, arg1=staff))

        skill_pct = _skill_percent(ch, "staves")
        chance = 20 + c_div(skill_pct * 4, 5)
        # ROM 2010-2016
        if int(getattr(ch, "level", 0)) < int(getattr(staff, "level", 0)) or rng_mm.number_percent() >= chance:
            out_lines.append(act_format("You fail to invoke $p.", recipient=ch, actor=ch, arg1=staff))
            _broadcast(room, "...and nothing happens.", exclude=ch)
            check_improve(ch, "staves", False, 2)
        else:
            # ROM 2019-2053: per-target loop
            target_kind = _resolve_target_kind(spell_name)
            spell_level = _get_value(staff, 0, int(getattr(ch, "level", 1)))
            people = list(getattr(room, "people", [])) if room is not None else [ch]
            ch_is_npc = bool(getattr(ch, "is_npc", False))
            for vch in people:
                vch_is_npc = bool(getattr(vch, "is_npc", False))
                # Map ROM TAR_* via skill target string
                if target_kind == "ignore":
                    if vch is not ch:
                        continue
                elif target_kind == "victim":  # TAR_CHAR_OFFENSIVE
                    if (vch_is_npc if ch_is_npc else not vch_is_npc):
                        continue
                elif target_kind == "friendly":  # TAR_CHAR_DEFENSIVE
                    if (not vch_is_npc if ch_is_npc else vch_is_npc):
                        continue
                elif target_kind == "self":  # TAR_CHAR_SELF
                    if vch is not ch:
                        continue
                else:
                    # Unknown / non-supported target type for brandish in ROM bugs out
                    return "\n".join(filter(None, out_lines))

                _obj_cast_spell(spell_name, spell_level, ch, vch, None)
            check_improve(ch, "staves", True, 2)

    # ROM 2056: --staff->value[2] <= 0 (decrement unconditionally; check after)
    new_charges = charges - 1
    _set_value(staff, 2, new_charges)
    if new_charges <= 0:
        _broadcast(
            room,
            act_format("$n's $p blazes bright and is gone.", recipient=None, actor=ch, arg1=staff),
            exclude=ch,
        )
        out_lines.append(act_format("Your $p blazes bright and is gone.", recipient=ch, actor=ch, arg1=staff))
        _clear_hold(ch)
        _extract_obj(ch, staff)

    return "\n".join(line for line in out_lines if line)


def do_zap(ch: "Character", args: str) -> str:
    """Zap with a wand. ROM src/act_obj.c:2068-2157."""
    arg = (args or "").split()
    arg = arg[0] if arg else ""

    fighting = getattr(ch, "fighting", None)

    # ROM 2076: empty arg + no fight target
    if not arg and fighting is None:
        return "Zap whom or what?"

    wand = _hold_slot(ch)
    # ROM 2082
    if wand is None:
        return "You hold nothing in your hand."

    # ROM 2088
    if wand.item_type != int(ItemType.WAND):
        return "You can zap only with a wand."

    victim: "Character | None" = None
    target_obj: "Object | None" = None
    if not arg:
        # ROM 2095-2105
        if fighting is not None:
            victim = fighting
        else:
            return "Zap whom or what?"
    else:
        victim = _get_char_room(ch, arg)
        if victim is None:
            target_obj = _find_obj_here(ch, arg)
        if victim is None and target_obj is None:
            return "You can't find it."

    # ROM 2117: WAIT_STATE
    ch.wait = max(getattr(ch, "wait", 0), 2 * _PULSE_VIOLENCE)

    room = getattr(ch, "room", None)
    out_lines: list[str] = []

    charges = _get_value(wand, 2, 0)
    # ROM 2119: if (wand->value[2] > 0)
    if charges > 0:
        # ROM 2121-2131: messaging branches
        if victim is not None:
            # ROM TO_NOTVICT: exclude ch + victim. act_format uses arg2 for $N.
            _broadcast(
                room,
                act_format("$n zaps $N with $p.", recipient=None, actor=ch, arg1=wand, arg2=victim),
                exclude=[ch, victim],
            )
            out_lines.append(act_format("You zap $N with $p.", recipient=ch, actor=ch, arg1=wand, arg2=victim))
            if victim is not ch:
                vict_msg = act_format("$n zaps you with $p.", recipient=victim, actor=ch, arg1=wand, arg2=victim)
                msgs = getattr(victim, "messages", None)
                if msgs is not None and vict_msg:
                    msgs.append(vict_msg)
        else:
            _broadcast(
                room,
                act_format("$n zaps $P with $p.", recipient=None, actor=ch, arg1=wand, arg2=target_obj),
                exclude=ch,
            )
            out_lines.append(act_format("You zap $P with $p.", recipient=ch, actor=ch, arg1=wand, arg2=target_obj))

        skill_pct = _skill_percent(ch, "wands")
        chance = 20 + c_div(skill_pct * 4, 5)
        # ROM 2133-2146
        if int(getattr(ch, "level", 0)) < int(getattr(wand, "level", 0)) or rng_mm.number_percent() >= chance:
            out_lines.append(
                act_format("Your efforts with $p produce only smoke and sparks.", recipient=ch, actor=ch, arg1=wand)
            )
            _broadcast(
                room,
                act_format("$n's efforts with $p produce only smoke and sparks.", recipient=None, actor=ch, arg1=wand),
                exclude=ch,
            )
            check_improve(ch, "wands", False, 2)
        else:
            spell = _get_value_raw(wand, 3)
            spell_level = _get_value(wand, 0, int(getattr(ch, "level", 1)))
            if spell:
                _obj_cast_spell(spell, spell_level, ch, victim, target_obj)
            check_improve(ch, "wands", True, 2)

    # ROM 2149: --wand->value[2] <= 0
    new_charges = charges - 1
    _set_value(wand, 2, new_charges)
    if new_charges <= 0:
        _broadcast(
            room,
            act_format("$n's $p explodes into fragments.", recipient=None, actor=ch, arg1=wand),
            exclude=ch,
        )
        out_lines.append(act_format("Your $p explodes into fragments.", recipient=ch, actor=ch, arg1=wand))
        _clear_hold(ch)
        _extract_obj(ch, wand)

    return "\n".join(line for line in out_lines if line)
