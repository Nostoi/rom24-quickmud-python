"""
Character finding utilities - find characters by name.

ROM Reference: src/handler.c get_char_room, get_char_world, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


def get_char_room(char: Character, name: str) -> Character | None:
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


def get_char_world(char: Character, name: str) -> Character | None:
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

    # mirroring ROM src/handler.c:2234 — the world scan walks ``char_list``,
    # which is head-inserted (src/db.c:2256-2257 create_mobile,
    # src/nanny.c:757-758 PC login), so the first is_name match is the NEWEST
    # matching char and `2.name` counts newest→oldest. ``character_registry``
    # is append-order, so iterate it reversed (INV-045 class (b)). HANDLER-006.
    for ch in reversed(character_registry):
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
    Check if ``name`` matches ``name_list`` per ROM's whole-word prefix rule.

    ROM Reference: src/handler.c:932-969 (`is_name`). Each space-separated part of
    ``name`` must be a ``str_prefix`` (whole-word *prefix*, not substring) of some
    word in ``name_list``, and **all** parts must match. Mirrors ROM's
    ``one_argument`` tokenization + ``str_prefix`` all-parts conjunction
    (HANDLER-004). `is_name("uard", "guard")` is False (ROM `str_prefix` is
    prefix-only); `is_name("big guard", "guard big")` is True (every part prefixes
    a namelist word).
    """
    if not name or not name_list:
        return False

    full = name.lower()
    parts = full.split()
    if not parts:
        return False

    list_words = name_list.lower().split()

    # mirroring ROM src/handler.c:946-967 — for each part of the arg, scan the
    # namelist; the part must be a prefix of some namelist word, else FALSE. The
    # full-arg prefix check (ROM `!str_prefix(string, name)`) short-circuits to
    # TRUE; it is redundant once the namelist is split on whitespace (a multi-word
    # `full` can never prefix a single space-free word) but is kept for fidelity.
    for part in parts:
        matched = False
        for word in list_words:
            if word.startswith(full):
                return True
            if word.startswith(part):
                matched = True
                break
        if not matched:
            return False

    return True
