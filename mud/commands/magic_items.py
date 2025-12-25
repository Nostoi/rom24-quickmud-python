"""
Magic item commands (recite, brandish, zap).

ROM Reference: src/act_obj.c lines 1915-2157
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.math.c_compat import c_div
from mud.models.constants import ItemType
from mud.utils import rng_mm
from mud.skills.registry import check_improve


def _skill_percent(character, name: str) -> int:
    """Get skill percentage for character (0-100)."""
    from mud.models.character import Character

    if not isinstance(character, Character):
        return 0

    pcdata = getattr(character, "pcdata", None)
    if not pcdata:
        return 0

    learned = getattr(pcdata, "learned", {})
    return learned.get(name, 0)


if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.object import Object


def obj_cast_spell(
    skill_name: str, level: int, caster: Character, victim: Character | None, obj: Object | None
) -> None:
    """
    Cast a spell from a magic item (scroll, staff, wand).

    ROM Reference: src/magic.c:594-720 (obj_cast_spell)

    Args:
        skill_name: Name of the spell to cast
        level: Caster level for the spell
        caster: Character using the magic item
        victim: Target character (or None)
        obj: Target object (or None)
    """
    from mud.models.constants import SKILL_TARGET_MAP
    from mud.skills.registry import get_skill_by_name
    from mud.skills.handlers import skill_handlers

    # Get skill data
    skill = get_skill_by_name(skill_name)
    if not skill:
        return

    # Check if spell handler exists
    handler = skill_handlers.get(skill_name)
    if not handler:
        return

    # Determine target based on skill target type
    target_type = SKILL_TARGET_MAP.get(skill.target, SkillTarget.TAR_IGNORE)

    # Handle different target types
    if target_type == SkillTarget.TAR_IGNORE:
        # No target needed
        pass

    elif target_type == SkillTarget.TAR_CHAR_OFFENSIVE:
        # Offensive spell - target enemy
        if victim is None:
            victim = caster.fighting
        if victim is None:
            caster.messages.append("You can't do that.")
            return
        # TODO: Add is_safe check
        # if is_safe(caster, victim) and caster != victim:
        #     caster.messages.append("Something isn't right...")
        #     return

    elif target_type in (SkillTarget.TAR_CHAR_DEFENSIVE, SkillTarget.TAR_CHAR_SELF):
        # Defensive/self spell - default to self
        if victim is None:
            victim = caster

    elif target_type == SkillTarget.TAR_OBJ_INV:
        # Object spell
        if obj is None:
            caster.messages.append("You can't do that.")
            return

    elif target_type == SkillTarget.TAR_OBJ_CHAR_OFF:
        # Offensive - char or object
        if victim is None and obj is None:
            if caster.fighting:
                victim = caster.fighting
            else:
                caster.messages.append("You can't do that.")
                return
        # TODO: Add is_safe_spell check for victim

    elif target_type == SkillTarget.TAR_OBJ_CHAR_DEF:
        # Defensive - char or object
        if victim is None and obj is None:
            victim = caster

    # Cast the spell
    try:
        handler(caster, victim if victim else obj)
    except Exception:
        # Spell failed - handler will have set appropriate messages
        pass

    # TODO: Check for offensive spells initiating combat
    # if (skill.target == TAR_CHAR_OFFENSIVE or TAR_OBJ_CHAR_OFF) and victim != caster:
    #     multi_hit(caster, victim, TYPE_UNDEFINED)


def do_recite(ch: Character, args: str) -> str:
    """
    Recite a scroll to cast its spells.

    ROM Reference: src/act_obj.c:1915-1974 (do_recite)

    Usage: recite <scroll> [target]

    Attempts to cast the spells stored in a scroll. Success depends on the
    'scrolls' skill and character level. On failure, the scroll is still consumed.
    """
    # Imports removed - function needs registry access for full implementation

    # Parse arguments: recite <scroll> [target]
    parts = args.split(None, 1)
    if not parts:
        return "Recite what?"

    scroll_name = parts[0]
    target_name = parts[1] if len(parts) > 1 else ""

    # Find the scroll in inventory
    scroll = None
    for obj in ch.inventory:
        if obj.name and scroll_name.lower() in obj.name.lower():
            scroll = obj
            break

    if not scroll:
        return "You do not have that scroll."

    # Check if it's actually a scroll
    if scroll.item_type != ItemType.ITEM_SCROLL:
        return "You can recite only scrolls."

    # Check level requirement
    if ch.level < scroll.level:
        return "This scroll is too complex for you to comprehend."

    # Find target (character or object)
    victim: Character | None = None
    target_obj: Object | None = None

    if not target_name:
        # No target specified - default to self
        victim = ch
    else:
        # Look for character in room
        victim = find_char_in_room(ch.room, target_name, ch)
        if not victim:
            # Look for object in room
            target_obj = find_obj_in_room(ch.room, target_name)

        if not victim and not target_obj:
            return "You can't find it."

    # Room messages
    if ch.room:
        for other in ch.room.characters:
            if other != ch:
                other.messages.append(f"{ch.name} recites {scroll.short_descr}.")

    ch.messages.append(f"You recite {scroll.short_descr}.")

    # Skill check: ROM formula is number_percent() >= 20 + skill*4/5
    skill_level = _skill_percent(ch, "scrolls")
    skill_chance = 20 + c_div(skill_level * 4, 5)
    roll = rng_mm.number_percent()

    if roll >= skill_chance:
        # Failed
        ch.messages.append("You mispronounce a syllable.")
        check_improve(ch, "scrolls", False, 2)
    else:
        # Success - cast all three spell slots
        # Scroll value[0] = level, value[1-3] = spell names/IDs
        spell_level = scroll.value[0] if scroll.value and len(scroll.value) > 0 else ch.level

        # Cast spell from value[1]
        if scroll.value and len(scroll.value) > 1 and scroll.value[1]:
            spell_name = str(scroll.value[1])
            obj_cast_spell(spell_name, spell_level, ch, victim, target_obj)

        # Cast spell from value[2]
        if scroll.value and len(scroll.value) > 2 and scroll.value[2]:
            spell_name = str(scroll.value[2])
            obj_cast_spell(spell_name, spell_level, ch, victim, target_obj)

        # Cast spell from value[3]
        if scroll.value and len(scroll.value) > 3 and scroll.value[3]:
            spell_name = str(scroll.value[3])
            obj_cast_spell(spell_name, spell_level, ch, victim, target_obj)

        check_improve(ch, "scrolls", True, 2)

    # Destroy the scroll
    if scroll in ch.inventory:
        ch.inventory.remove(scroll)

    return ""


def do_brandish(ch: Character, args: str) -> str:
    """
    Brandish a staff to cast its spell on all valid targets in the room.

    ROM Reference: src/act_obj.c:1978-2064 (do_brandish)

    Usage: brandish

    Brandishes the staff held in hand, casting its spell on all appropriate targets
    based on the spell's target type (offensive vs defensive). Consumes one charge.
    """
    # Check if holding something
    staff = getattr(ch, "equipment", {}).get("held")
    if not staff:
        return "You hold nothing in your hand."

    # Check if it's a staff
    if staff.item_type != ItemType.ITEM_STAFF:
        return "You can brandish only with a staff."

    # Get spell from staff value[3]
    if not staff.value or len(staff.value) < 4 or not staff.value[3]:
        # Invalid staff - no spell
        return "Nothing happens."

    spell_name = str(staff.value[3])

    # Apply wait state (2 * PULSE_VIOLENCE = 2 rounds)
    ch.wait = max(ch.wait, 2 * 3)  # PULSE_VIOLENCE is typically 3

    # Check if staff has charges
    charges = staff.value[2] if staff.value and len(staff.value) > 2 else 0
    if charges <= 0:
        return "The staff has no charges left."

    # Room messages
    if ch.room:
        for other in ch.room.characters:
            if other != ch:
                other.messages.append(f"{ch.name} brandishes {staff.short_descr}.")

    ch.messages.append(f"You brandish {staff.short_descr}.")

    # Check level and skill
    skill_level = _skill_percent(ch, "staves")
    skill_chance = 20 + c_div(skill_level * 4, 5)
    roll = rng_mm.number_percent()

    if ch.level < staff.level or roll >= skill_chance:
        # Failed
        ch.messages.append(f"You fail to invoke {staff.short_descr}.")
        if ch.room:
            for other in ch.room.characters:
                if other != ch:
                    other.messages.append("...and nothing happens.")
        check_improve(ch, "staves", False, 2)
    else:
        # Success - cast on all appropriate targets
        from mud.models.constants import SKILL_TARGET_MAP
        from mud.skills.registry import get_skill_by_name

        skill = get_skill_by_name(spell_name)
        spell_level = staff.value[0] if staff.value and len(staff.value) > 0 else ch.level

        if skill and ch.room:
            target_type = SKILL_TARGET_MAP.get(skill.target, SkillTarget.TAR_IGNORE)

            # Cast on all valid targets in room
            for vch in list(ch.room.characters):
                # Determine if this character is a valid target
                should_target = False

                if target_type == SkillTarget.TAR_IGNORE:
                    # Only self
                    should_target = vch == ch

                elif target_type == SkillTarget.TAR_CHAR_OFFENSIVE:
                    # Enemies only (NPC vs PC or PC vs NPC)
                    if ch.is_npc:
                        should_target = not vch.is_npc
                    else:
                        should_target = vch.is_npc

                elif target_type == SkillTarget.TAR_CHAR_DEFENSIVE:
                    # Allies only (same type)
                    if ch.is_npc:
                        should_target = vch.is_npc
                    else:
                        should_target = not vch.is_npc

                elif target_type == SkillTarget.TAR_CHAR_SELF:
                    # Only self
                    should_target = vch == ch

                if should_target:
                    obj_cast_spell(spell_name, spell_level, ch, vch, None)

        check_improve(ch, "staves", True, 2)

    # Decrement charges
    if staff.value and len(staff.value) > 2:
        staff.value[2] = charges - 1

        # If no charges left, destroy staff
        if staff.value[2] <= 0:
            if ch.room:
                for other in ch.room.characters:
                    if other != ch:
                        other.messages.append(f"{ch.name}'s {staff.short_descr} blazes bright and is gone.")
            ch.messages.append(f"Your {staff.short_descr} blazes bright and is gone.")

            # Remove from equipment
            if "held" in ch.equipment:
                del ch.equipment["held"]

    return ""


def do_zap(ch: Character, args: str) -> str:
    """
    Zap a target with a wand to cast its spell.

    ROM Reference: src/act_obj.c:2068-2157 (do_zap)

    Usage: zap [target]

    Zaps a character or object with the wand held in hand. If no target is specified
    and you're fighting, zaps your current opponent. Consumes one charge.
    """
    # Check if holding something
    wand = getattr(ch, "equipment", {}).get("held")
    if not wand:
        return "You hold nothing in your hand."

    # Check if it's a wand
    if wand.item_type != ItemType.ITEM_WAND:
        return "You can zap only with a wand."

    # Parse target
    target_name = args.strip()
    victim: Character | None = None
    target_obj: Object | None = None

    if not target_name:
        # No argument - use fighting target
        if ch.fighting:
            victim = ch.fighting
        else:
            return "Zap whom or what?"
    else:
        # Look for character in room
        if ch.room:
            victim = find_char_in_room(ch.room, target_name, ch)
            if not victim:
                # Look for object in room
                target_obj = find_obj_in_room(ch.room, target_name)

        if not victim and not target_obj:
            return "You can't find it."

    # Apply wait state (2 * PULSE_VIOLENCE = 2 rounds)
    ch.wait = max(ch.wait, 2 * 3)  # PULSE_VIOLENCE is typically 3

    # Check if wand has charges
    charges = wand.value[2] if wand.value and len(wand.value) > 2 else 0
    if charges <= 0:
        return "The wand has no charges left."

    # Room messages
    if victim:
        if ch.room:
            for other in ch.room.characters:
                if other != ch and other != victim:
                    other.messages.append(f"{ch.name} zaps {victim.name} with {wand.short_descr}.")
        ch.messages.append(f"You zap {victim.name} with {wand.short_descr}.")
        if victim != ch:
            victim.messages.append(f"{ch.name} zaps you with {wand.short_descr}.")
    else:
        # Zapping object
        if ch.room:
            for other in ch.room.characters:
                if other != ch:
                    obj_name = target_obj.short_descr if target_obj else "something"
                    other.messages.append(f"{ch.name} zaps {obj_name} with {wand.short_descr}.")
        obj_name = target_obj.short_descr if target_obj else "it"
        ch.messages.append(f"You zap {obj_name} with {wand.short_descr}.")

    # Check level and skill
    skill_level = _skill_percent(ch, "wands")
    skill_chance = 20 + c_div(skill_level * 4, 5)
    roll = rng_mm.number_percent()

    if ch.level < wand.level or roll >= skill_chance:
        # Failed
        ch.messages.append(f"Your efforts with {wand.short_descr} produce only smoke and sparks.")
        if ch.room:
            for other in ch.room.characters:
                if other != ch:
                    other.messages.append(f"{ch.name}'s efforts with {wand.short_descr} produce only smoke and sparks.")
        check_improve(ch, "wands", False, 2)
    else:
        # Success - cast spell
        if wand.value and len(wand.value) > 3 and wand.value[3]:
            spell_name = str(wand.value[3])
            spell_level = wand.value[0] if wand.value and len(wand.value) > 0 else ch.level
            obj_cast_spell(spell_name, spell_level, ch, victim, target_obj)

        check_improve(ch, "wands", True, 2)

    # Decrement charges
    if wand.value and len(wand.value) > 2:
        wand.value[2] = charges - 1

        # If no charges left, destroy wand
        if wand.value[2] <= 0:
            if ch.room:
                for other in ch.room.characters:
                    if other != ch:
                        other.messages.append(f"{ch.name}'s {wand.short_descr} explodes into fragments.")
            ch.messages.append(f"Your {wand.short_descr} explodes into fragments.")

            # Remove from equipment
            if "held" in ch.equipment:
                del ch.equipment["held"]

    return ""
