"""
Thief skill commands - sneak, hide, visible, steal.

ROM Reference: src/act_move.c do_sneak, do_hide, do_visible
ROM Reference: src/act_obj.c do_steal
"""
from __future__ import annotations

from mud.math.c_compat import c_div
from mud.models.character import Character, _object_carry_number, _object_carry_weight
from mud.models.constants import AffectFlag, ExtraFlag, MAX_LEVEL, PlayerFlag, Position
from mud.utils.act import act_format
from mud.utils.rng_mm import number_percent, number_range
from mud.world.char_find import get_char_room


def do_sneak(char: Character, args: str) -> str:
    """
    Attempt to move silently (thief skill).

    ROM Reference: src/act_move.c do_sneak (lines 1496-1522)

    Mirrors ROM exactly:
    - Always send "You attempt to move silently." (L1500), even at skill 0
    - affect_strip(ch, gsn_sneak) (L1501)
    - If already AFF_SNEAK from another source, return (L1503-1504)
    - Roll number_percent() < get_skill(ch, gsn_sneak) (L1506)
    - On success: apply AFF_SNEAK affect with level duration + check_improve TRUE
    - On failure: check_improve FALSE
    Delegates to canonical ROM-faithful implementation in mud.skills.handlers.sneak.
    """
    from mud.skills.handlers import sneak as _sneak_handler

    _sneak_handler(char)
    return "You attempt to move silently."


def do_hide(char: Character, args: str) -> str:
    """
    Attempt to hide in shadows (thief skill).

    ROM Reference: src/act_move.c do_hide (lines 1526-1542)

    Mirrors ROM exactly:
    - Always send "You attempt to hide." (L1528), even at skill 0
    - REMOVE_BIT AFF_HIDE if already hidden (L1530-1531)
    - Roll number_percent() < get_skill(ch, gsn_hide) (L1533)
    - On success: SET_BIT AFF_HIDE + check_improve TRUE
    - On failure: check_improve FALSE
    Delegates to canonical ROM-faithful implementation in mud.skills.handlers.hide.
    """
    from mud.skills.handlers import hide as _hide_handler

    return _hide_handler(char)


def do_visible(char: Character, args: str) -> str:
    """
    Remove invisibility, sneak, and hide effects.
    
    ROM Reference: src/act_move.c do_visible (lines 1549-1560)
    """
    # Strip spell-based invisibility
    _strip_affect(char, "invisibility")
    _strip_affect(char, "mass invisibility")
    _strip_affect(char, "sneak")
    
    # Remove affect flags
    affected_by = getattr(char, "affected_by", 0)
    affected_by &= ~AffectFlag.HIDE
    affected_by &= ~AffectFlag.INVISIBLE
    affected_by &= ~AffectFlag.SNEAK
    char.affected_by = affected_by
    
    return "Ok."


def do_steal(char: Character, args: str) -> str:
    """Attempt to steal items or coins from a target.

    ROM Reference: src/act_obj.c do_steal (lines 2161-2330)

    Faithful port of ROM `do_steal`. Returns the TO_CHAR string only;
    TO_VICT / TO_NOTVICT broadcasts are emitted via `broadcast_room`/
    `victim.messages`.
    """
    # ROM L2171-2172: argument = one_argument(argument, arg1); one_argument(argument, arg2)
    raw = (args or "").strip()
    parts = raw.split(None, 1)
    arg1 = parts[0] if parts else ""
    arg2 = parts[1].split(None, 1)[0] if len(parts) > 1 else ""

    # ROM L2174-2178
    if not arg1 or not arg2:
        return "Steal what from whom?\n"

    # ROM L2180-2183: get_char_room may return ch itself in ROM; QuickMUD's
    # helper excludes self, so emulate ROM by self-matching by name first.
    own_name = (getattr(char, "name", "") or "").lower()
    arg2_lower = arg2.lower()
    if arg2_lower == "self" or (own_name and arg2_lower in own_name):
        return "That's pointless.\n"

    victim = get_char_room(char, arg2)
    if victim is None:
        return "They aren't here.\n"

    # ROM L2185-2189 (defensive — get_char_room shouldn't return self here)
    if victim is char:
        return "That's pointless.\n"

    # ROM L2191-2192: is_safe (suppresses theft on safe targets, like ROM)
    from mud.combat.safety import is_safe

    if is_safe(char, victim):
        # ROM is_safe sends its own message; return empty TO_CHAR
        return ""

    # ROM L2194-2199: kill-stealing prevention
    victim_is_npc = bool(getattr(victim, "is_npc", False))
    victim_position = getattr(victim, "position", Position.STANDING)
    if victim_is_npc and victim_position == Position.FIGHTING:
        return (
            "Kill stealing is not permitted.\n"
            "You'd better not -- you might get hit.\n"
        )

    # ROM L2201: WAIT_STATE(ch, skill_table[gsn_steal].beats)
    _apply_wait_state(char, 24)

    # ROM L2202: percent = number_percent()
    percent = number_percent()

    # ROM L2204-2209: visibility / awake modifiers
    if not _is_awake(victim):
        percent -= 10
    elif not _can_see_char(victim, char):
        percent += 25
    else:
        percent += 50

    # ROM L2211-2214: failure conditions
    char_is_npc = bool(getattr(char, "is_npc", False))
    char_level = int(getattr(char, "level", 1) or 1)
    victim_level = int(getattr(victim, "level", 1) or 1)
    skill_level = _get_skill(char, "steal")

    level_gap = (
        (char_level + 7 < victim_level or char_level - 7 > victim_level)
        and not victim_is_npc
        and not char_is_npc
    )
    skill_failed = (not char_is_npc) and percent > skill_level
    no_clan = (not char_is_npc) and not _is_clan(char)

    if level_gap or skill_failed or no_clan:
        return _steal_failure(char, victim)

    # ROM L2270-2298: coin path
    arg1_lower = arg1.lower()
    if arg1_lower in ("coin", "coins", "gold", "silver"):
        return _steal_coins(char, victim)

    # ROM L2300-2329: item path
    return _steal_item(char, victim, arg1)


def _steal_failure(char: Character, victim: Character) -> str:
    """ROM L2216-2266: failure handling (yell, multi_hit, THIEF flag)."""

    # ROM L2218: send "Oops.\n\r" — return as TO_CHAR.
    # ROM L2220-2221: affect_strip(ch, gsn_sneak); REMOVE_BIT(ch->affected_by, AFF_SNEAK)
    _strip_affect(char, "sneak")
    if hasattr(char, "affected_by"):
        char.affected_by = int(getattr(char, "affected_by", 0) or 0) & ~int(AffectFlag.SNEAK)

    # ROM L2222-2223: act("$n tried to steal from you.", ..., TO_VICT)
    #                act("$n tried to steal from $N.", ..., TO_NOTVICT)
    room = getattr(char, "room", None)
    victim_msg = act_format(
        "$n tried to steal from you.\n", recipient=victim, actor=char, arg1=None, arg2=victim
    )
    notvict_msg = act_format(
        "$n tried to steal from $N.\n", recipient=None, actor=char, arg1=None, arg2=victim
    )
    if hasattr(victim, "messages"):
        victim.messages.append(victim_msg)
    if room is not None:
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is char or occupant is victim:
                continue
            if hasattr(occupant, "messages"):
                occupant.messages.append(notvict_msg)

    # ROM L2225-2240: random yell text
    char_name = getattr(char, "name", "someone") or "someone"
    sex = int(getattr(char, "sex", 0) or 0)
    possessive = "her" if sex == 2 else "his"
    yell_choice = number_range(0, 3)
    if yell_choice == 0:
        yell_buf = f"{char_name} is a lousy thief!"
    elif yell_choice == 1:
        yell_buf = f"{char_name} couldn't rob {possessive} way out of a paper bag!"
    elif yell_choice == 2:
        yell_buf = f"{char_name} tried to rob me!"
    else:
        yell_buf = f"Keep your hands out of there, {char_name}!"

    # ROM L2241-2245: wake victim if sleeping, then yell.
    if not _is_awake(victim):
        victim.position = Position.STANDING
    if _is_awake(victim):
        yell_text = f"{getattr(victim, 'name', 'Someone')} yells '{yell_buf}'\n"
        if room is not None:
            for occupant in list(getattr(room, "people", []) or []):
                if hasattr(occupant, "messages"):
                    occupant.messages.append(yell_text)

    # ROM L2247-2263: NPC victim attacks; PC victim sets THIEF flag on attacker.
    char_is_npc = bool(getattr(char, "is_npc", False))
    if not char_is_npc:
        if victim_is_npc := bool(getattr(victim, "is_npc", False)):
            from mud.combat.engine import multi_hit

            multi_hit(victim, char, None)
        else:
            current_act = int(getattr(char, "act", 0) or 0)
            if not (current_act & int(PlayerFlag.THIEF)):
                char.act = current_act | int(PlayerFlag.THIEF)
                if hasattr(char, "messages"):
                    char.messages.append("*** You are now a THIEF!! ***\n")

    return "Oops.\n"


def _steal_coins(char: Character, victim: Character) -> str:
    """ROM L2270-2298: coin theft path."""

    char_level = int(getattr(char, "level", 1) or 1)
    victim_gold = int(getattr(victim, "gold", 0) or 0)
    victim_silver = int(getattr(victim, "silver", 0) or 0)

    # ROM L2274-2275: gold = victim->gold * number_range(1, ch->level) / MAX_LEVEL
    gold = c_div(victim_gold * number_range(1, char_level), MAX_LEVEL)
    silver = c_div(victim_silver * number_range(1, char_level), MAX_LEVEL)

    # ROM L2276-2279
    if gold <= 0 and silver <= 0:
        return "You couldn't get any coins.\n"

    # ROM L2281-2284: transfer
    char.gold = int(getattr(char, "gold", 0) or 0) + gold
    char.silver = int(getattr(char, "silver", 0) or 0) + silver
    victim.gold = victim_gold - gold
    victim.silver = victim_silver - silver

    # ROM L2286-2294
    if silver <= 0:
        return f"Bingo!  You got {gold} gold coins.\n"
    if gold <= 0:
        return f"Bingo!  You got {silver} silver coins.\n"
    return f"Bingo!  You got {silver} silver and {gold} gold coins.\n"


def _steal_item(char: Character, victim: Character, item_name: str) -> str:
    """ROM L2300-2329: object theft path."""

    obj = _get_obj_carry_visible(victim, item_name, char)
    if obj is None:
        return "You can't find it.\n"

    # ROM L2304-2306
    extra_flags = int(getattr(obj, "extra_flags", 0) or 0)
    nodrop = bool(extra_flags & int(ExtraFlag.NODROP))
    inventory_flag = bool(extra_flags & int(ExtraFlag.INVENTORY))
    obj_level = int(getattr(obj, "level", 0) or 0)
    if obj_level == 0:
        proto = getattr(obj, "prototype", None)
        if proto is not None:
            obj_level = int(getattr(proto, "level", 0) or 0)
    char_level = int(getattr(char, "level", 1) or 1)
    if nodrop or inventory_flag or obj_level > char_level:
        return "You can't pry it away.\n"

    # ROM L2310-2313
    from mud.world.movement import can_carry_n, can_carry_w

    obj_count = _object_carry_number(obj)
    if int(getattr(char, "carry_number", 0) or 0) + obj_count > can_carry_n(char):
        return "You have your hands full.\n"

    # ROM L2316-2319
    obj_weight = _object_carry_weight(obj)
    if int(getattr(char, "carry_weight", 0) or 0) + obj_weight > can_carry_w(char):
        return "You can't carry that much weight.\n"

    # ROM L2322-2326: obj_from_char + obj_to_char + act + send "Got it!"
    victim.remove_object(obj)
    char.add_object(obj)
    obj.carried_by = char

    char_msg = act_format("You pocket $p.\n", recipient=char, actor=char, arg1=obj)
    return char_msg + "Got it!\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Helper functions

def _get_skill(char: Character, skill_name: str) -> int:
    """Get character's skill level (canonical: char.skills, ROM `get_skill`)."""

    skills = getattr(char, "skills", None)
    if isinstance(skills, dict):
        try:
            return int(skills.get(skill_name, 0) or 0)
        except (TypeError, ValueError):
            pass
    pcdata = getattr(char, "pcdata", None)
    if pcdata:
        learned = getattr(pcdata, "learned", {})
        try:
            return int(learned.get(skill_name, 0) or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def _strip_affect(char: Character, affect_name: str) -> None:
    """Remove an affect by name."""
    affects = getattr(char, "affected", [])
    char.affected = [a for a in affects if getattr(a, "type", "") != affect_name]


def _apply_sneak_affect(char: Character) -> None:
    """Apply sneak affect to character."""
    from mud.models.affect import Affect
    
    level = getattr(char, "level", 1)
    
    affect = Affect(
        type="sneak",
        level=level,
        duration=level,
        location=0,  # APPLY_NONE
        modifier=0,
        bitvector=AffectFlag.SNEAK,
    )
    
    affects = getattr(char, "affected", [])
    if not hasattr(char, "affected"):
        char.affected = []
    char.affected.append(affect)
    
    char.affected_by = getattr(char, "affected_by", 0) | AffectFlag.SNEAK


def _check_improve(char: Character, skill_name: str, success: bool) -> None:
    """Check for skill improvement (placeholder)."""

    pass


def _is_awake(victim: Character) -> bool:
    """Mirror ROM IS_AWAKE macro: position > SLEEPING."""

    pos = getattr(victim, "position", Position.STANDING)
    try:
        return int(pos) > int(Position.SLEEPING)
    except (TypeError, ValueError):
        return True


def _can_see_char(observer: Character, target: Character) -> bool:
    """Wrapper around `can_see_character` from world.vision."""

    try:
        from mud.world.vision import can_see_character

        return can_see_character(observer, target)
    except Exception:
        return True


def _is_clan(char: Character) -> bool:
    """Mirror ROM `is_clan(ch)` via `is_clan_member` helper."""

    try:
        from mud.characters import is_clan_member

        return is_clan_member(char)
    except Exception:
        return False


def _apply_wait_state(char: Character, beats: int) -> None:
    """ROM WAIT_STATE: char.wait = max(char.wait, beats)."""

    if beats <= 0 or not hasattr(char, "wait"):
        return
    current = int(getattr(char, "wait", 0) or 0)
    char.wait = max(current, int(beats))


def _get_obj_carry_visible(victim: Character, name: str, observer: Character):
    """ROM `get_obj_carry(victim, arg, ch)` with `can_see_obj` filter."""

    if not name:
        return None

    try:
        from mud.world.vision import can_see_object
    except Exception:  # pragma: no cover - defensive
        can_see_object = lambda *_args, **_kwargs: True  # noqa: E731

    target_count = 1
    needle = name
    if "." in name:
        prefix, _, rest = name.partition(".")
        try:
            target_count = int(prefix)
            needle = rest
        except ValueError:
            target_count = 1
            needle = name
    needle_lower = needle.lower()

    count = 0
    for obj in list(getattr(victim, "inventory", []) or []):
        if not can_see_object(observer, obj):
            continue
        obj_name = (getattr(obj, "name", "") or "").lower()
        obj_short = (getattr(obj, "short_descr", "") or "").lower()
        if needle_lower in obj_name or needle_lower in obj_short:
            count += 1
            if count == target_count:
                return obj
    return None
