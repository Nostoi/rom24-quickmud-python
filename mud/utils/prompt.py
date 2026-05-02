"""ROM ``bust_a_prompt`` port — render a player prompt against character state.

mirroring ROM src/comm.c:1420-1595
"""

from __future__ import annotations

from typing import Any

from mud.models.constants import CommFlag
from mud.olc.editor_state import EditorMode


def _is_npc(char: Any) -> bool:
    return bool(getattr(char, "is_npc", False))


def _alignment_word(alignment: int) -> str:
    # mirroring ROM src/comm.c:1537 (IS_GOOD/IS_EVIL/neutral thresholds)
    if alignment >= 350:
        return "good"
    if alignment <= -350:
        return "evil"
    return "neutral"


def _exits_token(char: Any) -> str:
    # mirroring ROM src/comm.c:1465-1483 — visible exit letters or "none"
    room = getattr(char, "room", None)
    if room is None:
        return "none"
    exits = getattr(room, "exits", None) or []
    letters = ["N", "E", "S", "W", "U", "D"]
    found: list[str] = []
    for door, exit_obj in enumerate(exits[:6]):
        if exit_obj is None:
            continue
        to_room = getattr(exit_obj, "to_room", None)
        if to_room is None:
            continue
        # ROM also gates on can_see_room + EX_CLOSED. Best-effort here:
        # treat any non-None destination as visible. Closed-door / blind
        # filtering can be tightened in a follow-up gap.
        found.append(letters[door])
    return "".join(found) if found else "none"


def _next_level_exp(char: Any) -> int:
    # mirroring ROM src/comm.c:1517-1522 — exp to next level for PCs.
    # Without a full exp_per_level port, fall back to 0 and let a
    # follow-up gap improve precision.
    return 0


def _bust_default_prompt(char: Any) -> str:
    """Render ROM's hard-coded default ``"{p<%dhp %dm %dmv>{x %s"``.

    mirroring ROM src/comm.c:1437-1443
    """

    hit = int(getattr(char, "hit", 0))
    mana = int(getattr(char, "mana", 0))
    move = int(getattr(char, "move", 0))
    prefix = getattr(char, "prefix", None) or ""
    return f"{{p<{hit}hp {mana}m {move}mv>{{x {prefix}"


def _olc_editor_mode(char: Any) -> EditorMode:
    """Return the active OLC editor mode for ``char``.

    mirroring ROM `src/olc.c:67-144` via the descriptor `editor` field,
    while tolerating the Python port's legacy `session.editor` string.
    """

    session = getattr(char, "desc", None)
    if session is None:
        return EditorMode.NONE

    mode = getattr(session, "editor_mode", EditorMode.NONE)
    if isinstance(mode, EditorMode):
        return mode

    legacy = getattr(session, "editor", None)
    legacy_map = {
        "aedit": EditorMode.AREA,
        "redit": EditorMode.ROOM,
        "oedit": EditorMode.OBJECT,
        "medit": EditorMode.MOBILE,
        "mpedit": EditorMode.MPCODE,
        "hedit": EditorMode.HELP,
    }
    return legacy_map.get(str(legacy or "").lower(), EditorMode.NONE)


def _olc_ed_name(char: Any) -> str:
    """Render ROM `olc_ed_name(ch)` for prompt token ``%o``."""

    mode = _olc_editor_mode(char)
    if mode == EditorMode.AREA:
        return "AEdit"
    if mode == EditorMode.ROOM:
        return "REdit"
    if mode == EditorMode.OBJECT:
        return "OEdit"
    if mode == EditorMode.MOBILE:
        return "MEdit"
    if mode == EditorMode.MPCODE:
        return "MPEdit"
    if mode == EditorMode.HELP:
        return "HEdit"
    return " "


def _olc_ed_vnum(char: Any) -> str:
    """Render ROM `olc_ed_vnum(ch)` for prompt token ``%O``."""

    mode = _olc_editor_mode(char)
    session = getattr(char, "desc", None)
    editor_state = getattr(session, "editor_state", {}) if session is not None else {}

    if mode == EditorMode.AREA:
        area = editor_state.get("area") if isinstance(editor_state, dict) else None
        return str(int(getattr(area, "vnum", 0) or 0))
    if mode == EditorMode.ROOM:
        room = getattr(char, "room", None)
        return str(int(getattr(room, "vnum", 0) or 0))
    if mode == EditorMode.OBJECT:
        obj_proto = editor_state.get("obj_proto") if isinstance(editor_state, dict) else None
        return str(int(getattr(obj_proto, "vnum", 0) or 0))
    if mode == EditorMode.MOBILE:
        mob_proto = editor_state.get("mob_proto") if isinstance(editor_state, dict) else None
        return str(int(getattr(mob_proto, "vnum", 0) or 0))
    if mode == EditorMode.MPCODE:
        mprog = None
        if isinstance(editor_state, dict):
            mprog = editor_state.get("mpcode") or editor_state.get("mprog") or editor_state.get("mob_prog")
        return str(int(getattr(mprog, "vnum", 0) or 0))
    if mode == EditorMode.HELP:
        help_entry = editor_state.get("help") if isinstance(editor_state, dict) else None
        keyword = getattr(help_entry, "keyword", None)
        if keyword:
            return str(keyword)
        keywords = getattr(help_entry, "keywords", None) or []
        if isinstance(keywords, str):
            return keywords
        return " ".join(str(part) for part in keywords)
    return " "


def bust_a_prompt(char: Any) -> str:
    """Return the prompt string ROM would emit for ``char``.

    mirroring ROM src/comm.c:1420-1595. Networking-side ANSI rendering and
    descriptor write-out happen at the call site (``send_prompt``); this
    function returns the unrendered ROM token output.
    """

    # mirroring ROM src/comm.c:1445-1449 — AFK indicator overrides everything
    comm_flags = int(getattr(char, "comm", 0) or 0)
    if comm_flags & int(CommFlag.AFK):
        return "{p<AFK>{x "

    template = getattr(char, "prompt", None)
    if not template:
        return _bust_default_prompt(char)

    out: list[str] = []
    i = 0
    n = len(template)
    while i < n:
        ch = template[i]
        if ch != "%":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= n:
            # trailing lone % — ROM writes nothing for it (default branch)
            out.append(" ")
            break
        token = template[i]
        i += 1

        # mirroring ROM src/comm.c:1459-1580 token table
        if token == "%":
            out.append("%")
        elif token == "c":
            out.append("\n\r")
        elif token == "h":
            out.append(str(int(getattr(char, "hit", 0))))
        elif token == "H":
            out.append(str(int(getattr(char, "max_hit", 0))))
        elif token == "m":
            out.append(str(int(getattr(char, "mana", 0))))
        elif token == "M":
            out.append(str(int(getattr(char, "max_mana", 0))))
        elif token == "v":
            out.append(str(int(getattr(char, "move", 0))))
        elif token == "V":
            out.append(str(int(getattr(char, "max_move", 0))))
        elif token == "x":
            out.append(str(int(getattr(char, "exp", 0))))
        elif token == "X":
            out.append("0" if _is_npc(char) else str(_next_level_exp(char)))
        elif token == "g":
            out.append(str(int(getattr(char, "gold", 0))))
        elif token == "s":
            out.append(str(int(getattr(char, "silver", 0))))
        elif token == "a":
            level = int(getattr(char, "level", 0))
            alignment = int(getattr(char, "alignment", 0))
            if level > 9:
                out.append(str(alignment))
            else:
                out.append(_alignment_word(alignment))
        elif token == "r":
            room = getattr(char, "room", None)
            out.append(getattr(room, "name", " ") if room is not None else " ")
        elif token == "R":
            from mud.models.constants import LEVEL_IMMORTAL

            level = int(getattr(char, "level", 0))
            room = getattr(char, "room", None)
            if level >= LEVEL_IMMORTAL and room is not None:
                out.append(str(int(getattr(room, "vnum", 0) or 0)))
            else:
                out.append(" ")
        elif token == "z":
            from mud.models.constants import LEVEL_IMMORTAL

            level = int(getattr(char, "level", 0))
            room = getattr(char, "room", None)
            area = getattr(room, "area", None) if room is not None else None
            if level >= LEVEL_IMMORTAL and area is not None:
                out.append(str(getattr(area, "name", "") or ""))
            else:
                out.append(" ")
        elif token == "e":
            out.append(_exits_token(char))
        elif token == "o":
            # mirroring ROM src/olc.c:67-97 — prompt token `%o`
            out.append(_olc_ed_name(char))
        elif token == "O":
            # mirroring ROM src/olc.c:101-144 — prompt token `%O`
            out.append(_olc_ed_vnum(char))
        else:
            # mirroring ROM src/comm.c:1461-1463 — unknown tokens render a space
            out.append(" ")

    rendered = "".join(out)
    prefix = getattr(char, "prefix", None) or ""
    if prefix:
        rendered = f"{{p{rendered}{{x{prefix}"
    return rendered
