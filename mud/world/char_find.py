"""
Character finding utilities - find characters by name.

ROM Reference: src/handler.c get_char_room, get_char_world, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


def get_char_room(char: "Character", name: str) -> "Character | None":
    """
    Find a character in the same room by name.

    ROM Reference: src/handler.c get_char_room

    Supports:
    - "self" keyword returns the character themselves
    - Direct name match
    - N.name format (e.g., "2.guard" for second guard)
    - Partial name matching
    """
    if not name:
        return None

    room = getattr(char, "room", None)
    if not room:
        return None

    count = 0
    target_count = 1

    if "." in name:
        parts = name.split(".", 1)
        try:
            target_count = int(parts[0])
            name = parts[1]
        except ValueError:
            pass

    name_lower = name.lower()

    if name_lower == "self":
        return char

    # mirroring ROM src/handler.c:2205-2211 — the in_room->people loop has NO
    # self-skip; only can_see + is_name gate it. can_see (src/handler.c) returns
    # TRUE for ch == victim, so the actor's own name resolves to the actor (even
    # when blind / in the dark). HANDLER-001.
    for occupant in getattr(room, "people", []):
        from mud.world.vision import can_see_character

        if not can_see_character(char, occupant):
            continue

        occupant_name = getattr(occupant, "name", None) or ""

        # mirroring ROM src/handler.c:2207-2210 — `if (!is_name(arg, rch->name))
        # continue; if (++count == number)`. ROM gates SOLELY on the keyword
        # `name` list (whole-word is_name), NOT the short_descr — `look city`
        # must not resolve "a city guard" whose keyword name is just "guard"
        # (HANDLER-003). The single predicate also keeps count advancing once
        # per occupant (HANDLER-002).
        if is_name(name, occupant_name):
            count += 1
            if count == target_count:
                return occupant

    return None


def get_char_world(char: "Character", name: str) -> "Character | None":
    """
    Find a character anywhere in the world by name.

    ROM Reference: src/handler.c get_char_world
    """
    from mud.models.character import character_registry

    if not name:
        return None

    victim = get_char_room(char, name)
    if victim is not None:
        return victim

    # Parse N.name format
    count = 0
    target_count = 1

    if "." in name:
        parts = name.split(".", 1)
        try:
            target_count = int(parts[0])
            name = parts[1]
        except ValueError:
            pass

    for ch in character_registry:
        from mud.world.vision import can_see_character

        # mirroring ROM src/handler.c:2236 — `if (wch->in_room == NULL || ...)
        # continue;` skips roomless chars BEFORE can_see/is_name, so a roomless
        # registry char (e.g. the CON_GET_NEW_CLASS wiznet subject) is never
        # resolved world-wide (HANDLER-005). Live since VISION-001 made roomless
        # targets visible to can_see_character.
        if getattr(ch, "room", None) is None:
            continue

        if not can_see_character(char, ch):
            continue

        ch_name = getattr(ch, "name", None) or ""

        # mirroring ROM src/handler.c:2237 — get_char_world gates on
        # is_name(arg, wch->name) only (keyword name, whole-word), not short_descr
        # (HANDLER-003).
        if is_name(name, ch_name):
            count += 1
            if count == target_count:
                return ch

    return None


def is_name(name: str, name_list: str) -> bool:
    """
    Check if name matches any word in name_list.

    ROM Reference: src/handler.c is_name
    """
    if not name or not name_list:
        return False

    name_lower = name.lower()
    for word in name_list.lower().split():
        if name_lower in word or word.startswith(name_lower):
            return True

    return False
