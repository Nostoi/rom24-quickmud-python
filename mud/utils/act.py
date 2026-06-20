"""Helpers for ROM-style act() placeholder formatting and list display."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mud.models.constants import Sex

if TYPE_CHECKING:
    from mud.models.character import Character

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

    # INV-052 (ACT-EMPTY-DISCARD): ROM act_new (src/comm.c:2240-2244) discards
    # NULL/zero-length format strings as its *first* action, before the
    # per-recipient loop — so it suppresses both delivery and the per-NPC
    # TRIG_ACT dispatch. ROM-NULL social fields arrive here as "" (see INV-052).
    if not format_str:
        return

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


_OBJ_AURA_FLAGS: list[tuple[str, str]] = []


def _ensure_aura_table() -> list[tuple[str, str]]:
    global _OBJ_AURA_FLAGS
    if _OBJ_AURA_FLAGS:
        return _OBJ_AURA_FLAGS
    from mud.models.constants import ExtraFlag

    _OBJ_AURA_FLAGS = [
        ("(Invis) ", ExtraFlag.INVIS),
        ("(Red Aura) ", None),
        ("(Blue Aura) ", None),
        ("(Magical) ", ExtraFlag.MAGIC),
        ("(Glowing) ", ExtraFlag.GLOW),
        ("(Humming) ", ExtraFlag.HUM),
    ]
    return _OBJ_AURA_FLAGS


def format_obj_to_char(obj: Any, char: Any, f_short: bool) -> str:
    """Format an object for display to *char*.

    ROM ``src/act_info.c:87-126``.  When *f_short* is True the
    ``short_descr`` is used; when False the long ``description``.
    Aura prefixes (Invis, Red Aura, Blue Aura, Magical, Glowing, Humming)
    are prepend when the viewer can see them — matching ROM C lines
    93-103, which check ``IS_OBJ_STAT``, ``IS_AFFECTED(ch, AFF_DETECT_EVIL)``,
    etc.
    """
    from mud.models.constants import ExtraFlag

    buf = ""

    if f_short:
        if not getattr(obj, "short_descr", None):
            return ""
    else:
        if not getattr(obj, "description", None):
            return ""

    if _obj_flag(obj, ExtraFlag.INVIS):
        buf += "(Invis) "
    if _char_affected(char, "detect_evil") and _obj_flag(obj, ExtraFlag.EVIL):
        buf += "(Red Aura) "
    if _char_affected(char, "detect_good") and _obj_flag(obj, ExtraFlag.BLESS):
        buf += "(Blue Aura) "
    if _char_affected(char, "detect_magic") and _obj_flag(obj, ExtraFlag.MAGIC):
        buf += "(Magical) "
    if _obj_flag(obj, ExtraFlag.GLOW):
        buf += "(Glowing) "
    if _obj_flag(obj, ExtraFlag.HUM):
        buf += "(Humming) "

    if f_short:
        buf += getattr(obj, "short_descr", "") or ""
    else:
        buf += getattr(obj, "description", "") or ""

    return buf


def _obj_flag(obj: Any, flag: Any) -> bool:
    extra = getattr(obj, "extra_flags", 0)
    if extra is None:
        extra = 0
    return bool(int(extra) & int(flag))


def _char_affected(char: Any, name: str) -> bool:
    for aff in getattr(char, "affected", []) or []:
        if getattr(aff, "name", None) == name or getattr(aff, "spell_name", None) == name:
            return True
        sn = getattr(aff, "type", None)
        if sn is not None:
            from mud.skills.registry import skill_lookup

            sk = skill_lookup(sn) if isinstance(sn, str) else None
            if sk and getattr(sk, "name", None) == name:
                return True
    aff_flags = getattr(char, "affected_by", 0)
    if aff_flags is None:
        aff_flags = 0
    flag_map = {
        "detect_evil": "DETECT_EVIL",
        "detect_good": "DETECT_GOOD",
        "detect_magic": "DETECT_MAGIC",
    }
    flag_name = flag_map.get(name)
    if flag_name:
        from mud.models.constants import AffectFlag

        if hasattr(AffectFlag, flag_name):
            if int(aff_flags) & int(getattr(AffectFlag, flag_name)):
                return True
    return False


def show_list_to_char(
    obj_list: list[Any],
    char: Character,
    f_short: bool,
    f_show_nothing: bool,
) -> str:
    """Format a list of objects for *char*, mirroring ROM
    ``src/act_info.c:130-243 show_list_to_char``.

    * ``f_short=True``  → use ``short_descr`` (for inventory,
      container contents, examine victim).
    * ``f_short=False`` → use ``description`` (for room contents).
    * ``f_show_nothing=True`` → print ``Nothing.`` (with padding
      for COMBINE) when no visible objects exist.
    * ``f_show_nothing=False`` → print nothing when list is empty.

    NPC / COMM_COMBINE viewers get duplicate-coalesced output with
    ``(N)`` counts or 5-space padding; PC non-COMBINE viewers get
    plain one-per-line with no indent — this is the FINDING-022 fix.
    """
    from mud.models.constants import CommFlag, WearLocation
    from mud.world.vision import can_see_object

    is_npc = getattr(char, "is_npc", False)
    comm_flags = int(getattr(char, "comm", 0) or 0)
    combine = is_npc or bool(comm_flags & int(CommFlag.COMBINE))

    visible: list[Any] = []
    for obj in obj_list:
        wear_loc = getattr(obj, "wear_loc", None)
        if wear_loc is not None and wear_loc != int(WearLocation.NONE):
            continue
        if not can_see_object(char, obj):
            continue
        visible.append(obj)

    if not visible:
        if not f_show_nothing:
            return ""
        if combine:
            return "     Nothing.\n"
        return "Nothing.\n"

    if combine:
        counts: dict[str, int] = {}
        order: list[str] = []
        for obj in visible:
            desc = format_obj_to_char(obj, char, f_short)
            if not desc:
                continue
            if desc in counts:
                counts[desc] += 1
            else:
                counts[desc] = 1
                order.append(desc)

        lines: list[str] = []
        for desc in order:
            n = counts[desc]
            if n > 1:
                lines.append(f"({n:2d}) {desc}")
            else:
                lines.append(f"     {desc}")

        if not lines and f_show_nothing:
            return "     Nothing.\n"
        if not lines:
            return ""
        return "\n".join(lines) + "\n"
    else:
        lines: list[str] = []
        for obj in visible:
            desc = format_obj_to_char(obj, char, f_short)
            if not desc:
                continue
            lines.append(desc)
        return "\n".join(lines) + "\n"
