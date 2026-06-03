"""Helpers for ROM-style act() placeholder formatting."""

from __future__ import annotations

from typing import Any

from mud.models.constants import Sex

_SUBJECT_PRONOUNS: dict[Sex, str] = {
    Sex.MALE: "he",
    Sex.FEMALE: "she",
    Sex.NONE: "it",
}
_OBJECT_PRONOUNS: dict[Sex, str] = {
    Sex.MALE: "him",
    Sex.FEMALE: "her",
    Sex.NONE: "it",
}
_POSSESSIVE_PRONOUNS: dict[Sex, str] = {
    Sex.MALE: "his",
    Sex.FEMALE: "her",
    Sex.NONE: "its",
}


def _sex_of(target: Any) -> Sex | None:
    sex = getattr(target, "sex", None)
    if isinstance(sex, Sex):
        return sex
    if isinstance(sex, int):
        try:
            # Some callers may store the numeric enum value instead of Sex.
            return Sex(sex)
        except ValueError:
            return None
    return None


def _subject_pronoun(sex: Sex | None) -> str:
    if isinstance(sex, Sex):
        return _SUBJECT_PRONOUNS.get(sex, "they")
    return "they"


def _object_pronoun(sex: Sex | None) -> str:
    if isinstance(sex, Sex):
        return _OBJECT_PRONOUNS.get(sex, "them")
    return "them"


def _possessive_pronoun(sex: Sex | None) -> str:
    if isinstance(sex, Sex):
        return _POSSESSIVE_PRONOUNS.get(sex, "their")
    return "their"


def _pers(target: Any | None, viewer: Any | None) -> str:
    """Return ROM-style perspective aware names.

    INV-027 (ACT-PERS-NAME-MASKING): ROM ``PERS(ch, looker)``
    (``src/merc.h:2145``) renders an ``act()`` ``$n``/``$N`` substitution as
    ``"someone"`` when ``can_see(looker, ch)`` is false. This gate fires only
    when there is a concrete ``viewer`` (recipient): the broadcast-once
    ``recipient=None`` path (the ``docs/divergences/MESSAGE_DELIVERY.md``
    architectural divergence) has no viewer to evaluate visibility against and
    must keep the name, or every room broadcast would render ``"someone"``.

    The prerequisite that unblocked this (VISION-001) aligned
    ``can_see_character`` with ROM ``can_see`` so a roomless synthetic wiznet
    subject (the ``announce_wiznet_new_player`` newbie alert) is no longer
    over-masked — see ``docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`` INV-027.
    """

    if target is None:
        return "someone"

    # INV-027: per-recipient PERS name-masking. Mirrors mud/world/vision.py:pers.
    if viewer is not None:
        from mud.world.vision import can_see_character

        if not can_see_character(viewer, target):
            return "someone"

    # ROM PERS (src/merc.h:2145): NPC → short_descr, PC → name. ROM has no
    # "$n"/"$N" self-case ("You"): the TO_CHAR templates address the subject
    # with literal "You ..." text instead. Mirrors mud/world/vision.py:pers.
    if getattr(target, "is_npc", False):
        name = getattr(target, "short_descr", None) or getattr(target, "name", None)
    else:
        name = getattr(target, "name", None) or getattr(target, "short_descr", None)

    return str(name) if name else "someone"


def _object_name(obj: Any | None, viewer: Any | None = None) -> str:
    if obj is None:
        return "something"

    if viewer is not None:
        from mud.world.vision import can_see_object

        if not can_see_object(viewer, obj):
            return "something"

    short_descr = getattr(obj, "short_descr", None)
    if short_descr:
        return str(short_descr)

    name = getattr(obj, "name", None)
    if name:
        return str(name)

    return str(obj)


def capitalize_act_line(text: str) -> str:
    """Capitalize the first visible letter of a rendered ``act()`` line.

    INV-029 (ACT-FIRST-LETTER-CAP). Mirrors ROM ``act_new``
    (``src/comm.c:2376-2379``): after the per-recipient buffer is formatted,
    ROM upper-cases ``buf[0]`` — with a kludge for a leading ``{`` colour code,
    where it caps ``buf[2]`` (the char after the 2-char ``{X`` code) instead.
    ``UPPER`` (``src/merc.h``) flips ASCII ``a``–``z`` only; digits, punctuation,
    and non-ASCII characters are left untouched.
    """

    if not text:
        return text

    def _upper(c: str) -> str:
        return chr(ord(c) - 32) if "a" <= c <= "z" else c

    if text[0] == "{":
        # ROM caps buf[2]; a bare 2-char colour code has nothing to cap.
        if len(text) >= 3:
            return text[:2] + _upper(text[2]) + text[3:]
        return text
    return _upper(text[0]) + text[1:]


def act_format(
    format_str: str,
    *,
    recipient: Any,
    actor: Any | None = None,
    arg1: Any | None = None,
    arg2: Any | None = None,
) -> str:
    """Expand a subset of ROM ``act_new`` tokens for wiznet broadcasts."""

    if not format_str:
        return ""

    result: list[str] = []
    length = len(format_str)
    index = 0

    while index < length:
        ch = format_str[index]
        if ch != "$":
            result.append(ch)
            index += 1
            continue

        index += 1
        if index >= length:
            break

        token = format_str[index]
        index += 1

        if token == "n":
            result.append(_pers(actor, recipient))
        elif token == "N":
            result.append(_pers(arg2, recipient))
        elif token == "e":
            sex = _sex_of(actor)
            result.append(_subject_pronoun(sex))
        elif token == "E":
            sex = _sex_of(arg2)
            result.append(_subject_pronoun(sex))
        elif token == "m":
            sex = _sex_of(actor)
            result.append(_object_pronoun(sex))
        elif token == "M":
            sex = _sex_of(arg2)
            result.append(_object_pronoun(sex))
        elif token == "s":
            sex = _sex_of(actor)
            result.append(_possessive_pronoun(sex))
        elif token == "S":
            sex = _sex_of(arg2)
            result.append(_possessive_pronoun(sex))
        elif token == "t":
            result.append("" if arg1 is None else str(arg1))
        elif token == "T":
            result.append("" if arg2 is None else str(arg2))
        elif token == "p":
            result.append(_object_name(arg1, recipient))
        elif token == "P":
            result.append(_object_name(arg2, recipient))
        elif token == "d":
            if arg2 is None:
                result.append("door")
            else:
                result.append(str(arg2).split()[0])
        elif token == "$":
            result.append("$")
        elif token == "B":
            # `$B` is unused in wiznet contexts; ignore.
            continue
        else:
            # Preserve unknown tokens verbatim for easier debugging.
            result.append(f"${token}")

    # INV-029 (ACT-FIRST-LETTER-CAP): ROM act_new caps the first visible letter
    # of the formatted buffer before delivery (src/comm.c:2376-2379).
    return capitalize_act_line("".join(result))


def act_to_room(
    room: Any,
    format_str: str,
    actor: Any,
    *,
    arg1: Any | None = None,
    arg2: Any | None = None,
    exclude: Any | None = None,
) -> None:
    """Render and deliver a ROM ``act(..., TO_ROOM)`` line per recipient.

    Mirrors ROM ``src/comm.c:2230-2385``: for each room occupant (excluding
    *actor* and *exclude*), format *format_str* through ``act_format``
    (which applies per-recipient PERS masking via INV-027), deliver the
    result, and dispatch ``TRIG_ACT`` to NPC recipients when the global
    ``MOBtrigger`` flag is enabled.

    This is the canonical shared helper for every ``act(TO_ROOM)`` site
    that needs per-recipient visibility masking.  Callers that previously
    baked ``char.name`` into a string and passed it to ``broadcast_room``
    should use this instead.
    """
    import mud.mobprog as mobprog
    from mud.utils.messaging import push_message

    people = getattr(room, "people", None)
    if not people:
        return

    dispatch_mobprog = bool(getattr(mobprog, "MOBtrigger", True))

    for recipient in list(people):
        if recipient is actor or recipient is exclude:
            continue

        message = act_format(format_str, recipient=recipient, actor=actor, arg1=arg1, arg2=arg2)
        push_message(recipient, message)

        if dispatch_mobprog and getattr(recipient, "is_npc", False):
            mobprog.mp_act_trigger(message, recipient, actor, arg1, arg2, mobprog.Trigger.ACT)
