"""ROM say_spell utility - syllable substitution for spell casting messages.

Mirroring ROM src/magic.c:132-207
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass  # Avoid import errors during type checking


# ROM src/magic.c:146-178 - Syllable substitution table
_SYL_TABLE = [
    (" ", " "),
    ("ar", "abra"),
    ("au", "kada"),
    ("bless", "fido"),
    ("blind", "nose"),
    ("bur", "mosa"),
    ("cu", "judi"),
    ("de", "oculo"),
    ("en", "unso"),
    ("light", "dies"),
    ("lo", "hi"),
    ("mor", "zak"),
    ("move", "sido"),
    ("ness", "lacri"),
    ("ning", "illa"),
    ("per", "duda"),
    ("ra", "gru"),
    ("fresh", "ima"),
    ("re", "candus"),
    ("son", "sabru"),
    ("tect", "infra"),
    ("tri", "cula"),
    ("ven", "nofo"),
    # Single character substitutions
    ("a", "a"),
    ("b", "b"),
    ("c", "q"),
    ("d", "e"),
    ("e", "z"),
    ("f", "y"),
    ("g", "o"),
    ("h", "p"),
    ("i", "u"),
    ("j", "y"),
    ("k", "t"),
    ("l", "r"),
    ("m", "w"),
    ("n", "i"),
    ("o", "a"),
    ("p", "s"),
    ("q", "d"),
    ("r", "f"),
    ("s", "g"),
    ("t", "h"),
    ("u", "j"),
    ("v", "z"),
    ("w", "x"),
    ("x", "n"),
    ("y", "l"),
    ("z", "k"),
    ("", ""),  # Terminator
]


def say_spell(caster: Any, spell_name: str) -> tuple[str, str]:
    """ROM say_spell: convert spell name to gibberish for non-class observers.

    Args:
        caster: Character casting the spell
        spell_name: Name of the spell being cast

    Returns:
        Tuple of (actual_words, garbled_words)
        - actual_words: Message shown to same-class observers
        - garbled_words: Message shown to different-class observers

    ROM C Reference: src/magic.c:132-207
    """
    if not spell_name:
        return ("", "")

    # Build garbled version using syllable substitution
    garbled = []
    name_lower = spell_name.lower()
    pos = 0

    while pos < len(name_lower):
        matched = False

        # Try each syllable in the table
        for old, new in _SYL_TABLE:
            if not old:  # Terminator
                break

            if name_lower[pos:].startswith(old):
                garbled.append(new)
                pos += len(old)
                matched = True
                break

        # If no match, advance by 1 character
        if not matched:
            pos += 1

    garbled_words = "".join(garbled)

    # Format messages
    actual_msg = f"$n utters the words, '{spell_name}'."
    garbled_msg = f"$n utters the words, '{garbled_words}'."

    return (actual_msg, garbled_msg)


def broadcast_spell_words(caster: Any, spell_name: str) -> None:
    """Broadcast spell words to room with class-based filtering.

    ROM C Reference: src/magic.c:199-204
    """
    # Import here to avoid circular dependencies
    try:
        from mud.net.protocol import broadcast_room
    except ImportError:
        # Gracefully handle if module not available
        return

    room = getattr(caster, "room", None)
    if room is None:
        return

    actual_msg, garbled_msg = say_spell(caster, spell_name)
    caster_class = getattr(caster, "ch_class", None)

    # ROM L199-203: Show actual words to same class, garbled to others
    for occupant in list(getattr(room, "people", []) or []):
        if occupant is caster:
            continue

        is_npc = getattr(occupant, "is_npc", True)
        occupant_class = getattr(occupant, "ch_class", None)

        # Non-NPCs of same class see actual words, others see garbled
        if not is_npc and caster_class == occupant_class:
            message = actual_msg.replace("$n", getattr(caster, "name", "Someone"))
        else:
            message = garbled_msg.replace("$n", getattr(caster, "name", "Someone"))

        if hasattr(occupant, "messages"):
            occupant.messages.append(message)
