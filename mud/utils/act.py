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

    if viewer is not None and target is viewer:
        return "You"

    # INV-027: per-recipient PERS name-masking. Mirrors mud/world/vision.py:pers.
    if viewer is not None:
        from mud.world.vision import can_see_character

        if not can_see_character(viewer, target):
            return "someone"

    name = getattr(target, "name", None)
    if name:
        return str(name)

    short_descr = getattr(target, "short_descr", None)
    if short_descr:
        return str(short_descr)

    return "someone"


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

    return "".join(result)
