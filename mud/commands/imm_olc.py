"""
OLC (Online Creation) commands - resets, alist, edit.

ROM Reference: src/olc.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.commands.imm_commands import get_trust
from mud.models.character import Character
from mud.utils.olc_tables import (
    DIR_NAMES,
    door_reset_string_for,
    wear_loc_flag_lookup,
    wear_loc_string_for,
)

if TYPE_CHECKING:
    pass


def _display_resets(room) -> str:
    """Format the reset list for a room into the 8-column OLC table.

    Returns a single string (lines joined by '\\n', each reset line ending
    with '\\n\\r' per ROM convention) suitable for sending to the builder.

    ROM Reference: src/olc.c:973-1183 display_resets
    """
    from mud.models.constants import RoomFlag, WearLocation
    from mud.registry import mob_registry, obj_registry, room_registry

    header = (
        " No.  Loads    Description       Location         Vnum   Mx Mn Description\n\r"
        "==== ======== ============= =================== ======== ===== ===========\n\r"
    )

    resets = getattr(room, "resets", [])
    if not resets:
        return header.rstrip("\n\r")

    lines = [header.rstrip("\n\r")]
    i_reset = 0
    pMob = None  # mirroring ROM src/olc.c:977 MOB_INDEX_DATA *pMob = NULL

    for pReset in resets:
        cmd = getattr(pReset, "command", "?")
        arg1 = getattr(pReset, "arg1", 0) or 0
        arg2 = getattr(pReset, "arg2", 0) or 0
        arg3 = getattr(pReset, "arg3", 0) or 0
        arg4 = getattr(pReset, "arg4", 0) or 0

        i_reset += 1
        prefix = f"[{i_reset:2d}] "  # mirroring ROM src/olc.c:1000 sprintf(final,"[%2d] ",++iReset)

        if cmd == "M":
            # mirroring ROM src/olc.c:1009-1046
            pMobIndex = mob_registry.get(arg1)
            if not pMobIndex:
                # ROM src/olc.c:1012-1015: strcat(final, buf); continue;
                # The 'continue' jumps past send_to_char, so nothing is emitted.
                # mirroring ROM src/olc.c:1015 continue — skip send_to_char
                pMob = None
                continue

            pRoomIndex = room_registry.get(arg3)
            if not pRoomIndex:
                # mirroring ROM src/olc.c:1019-1023 continue — skip send_to_char
                pMob = None
                continue

            pMob = pMobIndex  # mirroring ROM src/olc.c:1026 pMob = pMobIndex

            short_descr = (pMobIndex.short_descr or "")
            room_name = (pRoomIndex.name or "")

            # mirroring ROM src/olc.c:1027-1030
            # "M[%5d] %-13.13s in room             R[%5d] %2d-%2d %-15.15s\n\r"
            reset_line = (
                f"M[{arg1:5d}] {short_descr:<13.13s} in room             "
                f"R[{arg3:5d}] {arg2:2d}-{arg4:2d} {room_name:<15.15s}\n\r"
            )
            final = prefix + reset_line

            # Pet-shop check: mirroring ROM src/olc.c:1037-1044
            # get_room_index(pRoomIndex->vnum - 1); if ROOM_PET_SHOP: final[5] = 'P'
            prev_room = room_registry.get(pRoomIndex.vnum - 1)
            if prev_room:
                prev_flags = getattr(prev_room, "room_flags", 0) or 0
                if prev_flags & int(RoomFlag.ROOM_PET_SHOP):
                    # index 5 is the 'M' character in "[NN] M[..."
                    final = final[:5] + "P" + final[6:]

            lines.append(final.rstrip("\n\r"))

        elif cmd == "O":
            # mirroring ROM src/olc.c:1048-1073
            pObjIndex = obj_registry.get(arg1)
            if not pObjIndex:
                # ROM src/olc.c:1051-1054 continue — skip send_to_char
                continue

            pRoomIndex = room_registry.get(arg3)
            if not pRoomIndex:
                # ROM src/olc.c:1059-1064 continue — skip send_to_char
                continue

            short_descr = (pObjIndex.short_descr or "")
            room_name = (pRoomIndex.name or "")

            # mirroring ROM src/olc.c:1067-1070
            # "O[%5d] %-13.13s in room             R[%5d]       %-15.15s\n\r"
            reset_line = (
                f"O[{arg1:5d}] {short_descr:<13.13s} in room             "
                f"R[{arg3:5d}]       {room_name:<15.15s}\n\r"
            )
            lines.append((prefix + reset_line).rstrip("\n\r"))

        elif cmd == "P":
            # mirroring ROM src/olc.c:1075-1103
            pObjIndex = obj_registry.get(arg1)
            if not pObjIndex:
                # ROM src/olc.c:1078-1081 continue — skip send_to_char
                continue

            pObjToIndex = obj_registry.get(arg3)
            if not pObjToIndex:
                # ROM src/olc.c:1086-1090 continue — skip send_to_char
                continue

            short_descr = (pObjIndex.short_descr or "")
            to_short_descr = (pObjToIndex.short_descr or "")

            # mirroring ROM src/olc.c:1094-1100
            # "O[%5d] %-13.13s inside              O[%5d] %2d-%2d %-15.15s\n\r"
            reset_line = (
                f"O[{arg1:5d}] {short_descr:<13.13s} inside              "
                f"O[{arg3:5d}] {arg2:2d}-{arg4:2d} {to_short_descr:<15.15s}\n\r"
            )
            lines.append((prefix + reset_line).rstrip("\n\r"))

        elif cmd in ("G", "E"):
            # mirroring ROM src/olc.c:1105-1143
            pObjIndex = obj_registry.get(arg1)
            if not pObjIndex:
                # ROM src/olc.c:1108-1112 continue — skip send_to_char
                continue

            if not pMob:
                # ROM src/olc.c:1117-1123 — break (not continue), so send_to_char IS called
                err_line = "Give/Equip Object - No Previous Mobile\n\r"
                lines.append((prefix + err_line).rstrip("\n\r"))
                break

            short_descr = (pObjIndex.short_descr or "")

            if pMob.pShop:
                # mirroring ROM src/olc.c:1125-1131
                # "O[%5d] %-13.13s in the inventory of S[%5d]       %-15.15s\n\r"
                mob_short = (pMob.short_descr or "")
                reset_line = (
                    f"O[{arg1:5d}] {short_descr:<13.13s} in the inventory of "
                    f"S[{pMob.vnum:5d}]       {mob_short:<15.15s}\n\r"
                )
            else:
                # mirroring ROM src/olc.c:1133-1141
                # "O[%5d] %-13.13s %-19.19s M[%5d]       %-15.15s\n\r"
                if cmd == "G":
                    # flag_string(wear_loc_strings, WEAR_NONE)
                    wear_str = wear_loc_string_for(int(WearLocation.NONE))
                else:
                    # flag_string(wear_loc_strings, pReset->arg3)
                    wear_str = wear_loc_string_for(arg3)
                mob_short = (pMob.short_descr or "")
                reset_line = (
                    f"O[{arg1:5d}] {short_descr:<13.13s} {wear_str:<19.19s} "
                    f"M[{pMob.vnum:5d}]       {mob_short:<15.15s}\n\r"
                )
            lines.append((prefix + reset_line).rstrip("\n\r"))

        elif cmd == "D":
            # mirroring ROM src/olc.c:1151-1160
            # No bad-room check in ROM for D — it calls get_room_index but doesn't guard
            pRoomIndex = room_registry.get(arg1)
            room_name = (pRoomIndex.name if pRoomIndex else "") or ""

            # capitalize(dir_name[pReset->arg2])
            dir_idx = arg2 if 0 <= arg2 < len(DIR_NAMES) else 0
            dir_cap = DIR_NAMES[dir_idx].capitalize()

            # flag_string(door_resets, pReset->arg3)
            door_str = door_reset_string_for(arg3)

            # "R[%5d] %s door of %-19.19s reset to %s\n\r"
            reset_line = (
                f"R[{arg1:5d}] {dir_cap} door of {room_name:<19.19s} reset to {door_str}\n\r"
            )
            lines.append((prefix + reset_line).rstrip("\n\r"))

        elif cmd == "R":
            # mirroring ROM src/olc.c:1164-1177
            pRoomIndex = room_registry.get(arg1)
            if not pRoomIndex:
                # ROM src/olc.c:1166-1170 continue — skip send_to_char
                continue

            room_name = (pRoomIndex.name or "")
            # "R[%5d] Exits are randomized in %s\n\r"
            reset_line = f"R[{arg1:5d}] Exits are randomized in {room_name}\n\r"
            lines.append((prefix + reset_line).rstrip("\n\r"))

        else:
            # mirroring ROM src/olc.c:1004-1007 default case
            reset_line = f"Bad reset command: {cmd}.\n\r"
            lines.append((prefix + reset_line).rstrip("\n\r"))

    return "\n".join(lines)


def _add_reset(room, pReset, insert_loc: int) -> None:
    """Insert pReset at 1-indexed position insert_loc in room.resets.

    Negative / zero insert_loc -> tail insertion; idx=1 -> head.
    Mirrors ROM src/olc.c:add_reset linked-list insert semantics
    (Python list approximation — see OLC-021 for edge-case gap).

    ROM Reference: src/olc.c:1192-1228
    """
    if not hasattr(room, "resets") or room.resets is None:
        room.resets = []
    if insert_loc <= 0:
        room.resets.append(pReset)
    else:
        room.resets.insert(insert_loc - 1, pReset)


def do_resets(char: Character, args: str) -> str:
    """
    View or modify room resets.

    ROM Reference: src/olc.c do_resets (lines 1232-1476)

    Usage:
    - resets                       - Display resets in current room
    - resets <num> delete          - Delete reset
    - resets <num> mob <vnum>      - Add mob reset
    - resets <num> obj <vnum>      - Add obj reset
    """
    room = getattr(char, "room", None)
    if not room:
        return "You're not in a room."

    # Check builder security
    area = getattr(room, "area", None)
    if area:
        if not _is_builder(char, area):
            return "Resets: Invalid security for editing this area."

    if not args or not args.strip():
        # mirroring ROM src/olc.c:1262-1271 display branch
        resets = getattr(room, "resets", [])
        if not resets:
            return "No resets in this room.\n\r"

        # ROM src/olc.c:1266 — lead line + display_resets
        lead = "Resets: M = mobile, R = room, O = object, P = pet, S = shopkeeper\n\r"
        return lead + _display_resets(room)

    parts = args.strip().split()

    # mirroring ROM src/olc.c:1279-1465 — take index number and search for commands
    if len(parts) >= 2 and parts[0].isdigit():
        from types import SimpleNamespace

        from mud.models.constants import ItemType, WearLocation
        from mud.registry import mob_registry, obj_registry

        insert_loc = int(parts[0])
        arg2 = parts[1].lower()
        # Extract remaining args (mirrors ROM one_argument peeling of arg3..arg7)
        arg3 = parts[2] if len(parts) > 2 else ""
        arg4 = parts[3] if len(parts) > 3 else ""
        arg5 = parts[4] if len(parts) > 4 else ""
        arg6 = parts[5] if len(parts) > 5 else ""
        arg7 = parts[6] if len(parts) > 6 else ""

        # --- Delete a reset --- mirroring ROM src/olc.c:1287-1334
        if arg2 == "delete":
            resets = getattr(room, "resets", [])
            if not resets:
                return "No resets in this area.\n\r"
            if insert_loc < 1 or insert_loc > len(resets):
                return "Reset not found.\n\r"
            resets.pop(insert_loc - 1)
            return "Reset deleted.\n\r"

        # --- Mobile reset --- mirroring ROM src/olc.c:1341-1362
        if arg2 == "mob" and arg3.lstrip("-").isdigit():
            mob_vnum = int(arg3)
            mob_idx = mob_registry.get(mob_vnum)
            if mob_idx is None:
                return "Mob doesn't exist.\n\r"

            # arg4 = max # in area (default 1), arg5 = max # in room (default 1)
            # mirroring ROM src/olc.c:1359,1361
            max_area = int(arg4) if arg4.lstrip("-").isdigit() else 1
            max_room = int(arg5) if arg5.lstrip("-").isdigit() else 1

            pReset = SimpleNamespace(
                command="M",
                arg1=mob_vnum,
                arg2=max_area,  # max # in area
                arg3=room.vnum,
                arg4=max_room,  # max # in room
            )
            _add_reset(room, pReset, insert_loc)
            return "Reset added.\n\r"

        # --- Object reset --- mirroring ROM src/olc.c:1363-1432
        if arg2 == "obj" and arg3.lstrip("-").isdigit():
            obj_vnum = int(arg3)

            # --- Inside another object (P-reset) --- ROM src/olc.c:1376-1391
            if arg4.lower().startswith("inside"):
                # mirroring ROM src/olc.c:1376: !str_prefix(arg4, "inside")
                container_vnum = int(arg5) if arg5.lstrip("-").isdigit() else 1
                temp = obj_registry.get(container_vnum)
                if temp is None:
                    return "Vnum doesn't exist.\n\r"
                # ROM src/olc.c:1381-1385 — must be ITEM_CONTAINER or ITEM_CORPSE_NPC
                temp_type = int(getattr(temp, "item_type", 0))
                if temp_type not in (int(ItemType.CONTAINER), int(ItemType.CORPSE_NPC)):
                    return "Object 2 is not a container.\n\r"
                # arg6=limit (default 1), arg7=count (default 1)
                # mirroring ROM src/olc.c:1388-1390
                limit = int(arg6) if arg6.lstrip("-").isdigit() else 1
                count = int(arg7) if arg7.lstrip("-").isdigit() else 1
                pReset = SimpleNamespace(
                    command="P",
                    arg1=obj_vnum,
                    arg2=limit,
                    arg3=container_vnum,
                    arg4=count,
                )
                _add_reset(room, pReset, insert_loc)
                return "Reset added.\n\r"

            # --- Inside the room (O-reset) --- ROM src/olc.c:1397-1408
            if arg4.lower() == "room":
                # mirroring ROM src/olc.c:1399-1403 — validate obj vnum exists
                if obj_registry.get(obj_vnum) is None:
                    return "Vnum doesn't exist.\n\r"
                pReset = SimpleNamespace(
                    command="O",
                    arg1=obj_vnum,
                    arg2=0,
                    arg3=room.vnum,
                    arg4=0,
                )
                _add_reset(room, pReset, insert_loc)
                return "Reset added.\n\r"

            # --- Into a mobile's inventory (G or E reset) --- ROM src/olc.c:1409-1431
            wear_val = wear_loc_flag_lookup(arg4)
            if wear_val is None:
                # mirroring ROM src/olc.c:1415-1417
                return "Resets: '? wear-loc'\n\r"
            # ROM src/olc.c:1420-1423 — validate obj vnum
            if obj_registry.get(obj_vnum) is None:
                return "Vnum doesn't exist.\n\r"
            # ROM src/olc.c:1427-1430 — WEAR_NONE -> G, else E
            if wear_val == int(WearLocation.NONE):
                cmd = "G"
            else:
                cmd = "E"
            pReset = SimpleNamespace(
                command=cmd,
                arg1=obj_vnum,
                arg2=0,
                arg3=wear_val,
                arg4=0,
            )
            _add_reset(room, pReset, insert_loc)
            return "Reset added.\n\r"

        # --- Random exits reset (R-reset) --- ROM src/olc.c:1437-1451
        if arg2 == "random" and arg3.lstrip("-").isdigit():
            n_exits = int(arg3)
            if n_exits < 1 or n_exits > 6:
                return "Invalid argument.\n\r"
            pReset = SimpleNamespace(
                command="R",
                arg1=room.vnum,
                arg2=n_exits,
                arg3=0,
                arg4=0,
            )
            _add_reset(room, pReset, insert_loc)
            return "Random exits reset added.\n\r"

        # --- Syntax help for unrecognized subcommand --- ROM src/olc.c:1452-1465
        return (
            "Syntax: RESET <number> OBJ <vnum> <wear_loc>\n\r"
            "        RESET <number> OBJ <vnum> inside <vnum> [limit] [count]\n\r"
            "        RESET <number> OBJ <vnum> room\n\r"
            "        RESET <number> MOB <vnum> [max #x area] [max #x room]\n\r"
            "        RESET <number> DELETE\n\r"
            "        RESET <number> RANDOM [#x exits]\n\r"
        )

    return (
        "Syntax: RESET <number> OBJ <vnum> <wear_loc>\n\r"
        "        RESET <number> OBJ <vnum> inside <vnum> [limit] [count]\n\r"
        "        RESET <number> OBJ <vnum> room\n\r"
        "        RESET <number> MOB <vnum> [max #x area] [max #x room]\n\r"
        "        RESET <number> DELETE\n\r"
        "        RESET <number> RANDOM [#x exits]\n\r"
    )


def do_alist(char: Character, args: str) -> str:
    """
    List all areas with their details.

    ROM Reference: src/olc.c do_alist (lines 1478-1510)

    Usage: alist
    """
    if getattr(char, "is_npc", False):
        return ""

    # mirrors ROM src/olc.c:1487-1498 — iterate area_registry (was: bogus
    # `registry.areas` attribute), use `area.vnum` for the first column
    # (was: 1-indexed enumerate counter), and `file_name` not `filename`.
    from mud.registry import area_registry

    lines = [f"[{'Num':>3s}] [{'Area Name':<27s}] ({'lvnum':>5s}-{'uvnum':>5s}) [{'Filename':<10s}] {'Sec':>3s} [{'Builders':<10s}]"]

    for area in area_registry.values():
        name = (getattr(area, "name", None) or "Unknown")[:29]
        min_vnum = getattr(area, "min_vnum", 0)
        max_vnum = getattr(area, "max_vnum", 0)
        file_name = (getattr(area, "file_name", None) or "")[:12]
        security = getattr(area, "security", 0)
        builders = (getattr(area, "builders", None) or "")[:10]
        vnum = getattr(area, "vnum", 0)

        lines.append(
            f"[{vnum:3d}] {name:<29s} ({min_vnum:>5d}-{max_vnum:>5d}) {file_name:<12s} [{security}] [{builders:<10s}]"
        )

    return "\n".join(lines)


def do_edit(char: Character, args: str) -> str:
    """Top-level ``olc`` / ``edit`` dispatcher — ROM ``do_olc`` (src/olc.c:661-690).

    Routes ``olc <subcmd> [args]`` through the six-entry ``editor_table[]``
    (src/olc.c:646-657) using prefix matching identical to ROM ``str_prefix``:

        area    → do_aedit  (cmd_aedit in build.py)
        room    → do_redit  (cmd_redit in build.py)
        object  → do_oedit  (cmd_oedit in build.py)
        mobile  → do_medit  (cmd_medit in build.py)
        mpcode  → do_mpedit (do_mpedit below)
        hedit   → do_hedit  (cmd_hedit in build.py)

    Missing or unrecognised subcmd → help text (mirrors ROM ``do_help(ch,"olc")``).
    NPCs are rejected immediately, matching ROM ``IS_NPC`` guard.
    """
    # ROM: if (IS_NPC(ch)) return;
    if getattr(char, "is_npc", False):
        return ""

    # mirroring ROM src/olc.c:661-690 — editor_table[] + str_prefix dispatch
    from mud.commands.build import cmd_aedit, cmd_hedit, cmd_medit, cmd_oedit, cmd_redit

    _OLC_HELP = (
        "Syntax:  olc <area|room|object|mobile|mpcode|hedit> [args]\r\n"
        "         olc area     [vnum]        - edit / create an area\r\n"
        "         olc room     [vnum]        - edit / create a room\r\n"
        "         olc object   <vnum>        - edit / create an object prototype\r\n"
        "         olc mobile   <vnum>        - edit / create a mobile prototype\r\n"
        "         olc mpcode   <vnum>        - edit a mob program\r\n"
        "         olc hedit    [keyword]     - edit a help entry\r\n"
    )

    # editor_table[] — ROM src/olc.c:646-657
    _EDITOR_TABLE: list[tuple[str, object]] = [
        ("area",   cmd_aedit),
        ("room",   cmd_redit),
        ("object", cmd_oedit),
        ("mobile", cmd_medit),
        ("mpcode", do_mpedit),
        ("hedit",  cmd_hedit),
    ]

    arg = (args or "").strip()
    if not arg:
        return _OLC_HELP

    # one_argument: peel first token, rest becomes argument for the sub-handler
    parts = arg.split(None, 1)
    command = parts[0].lower()
    remainder = parts[1] if len(parts) > 1 else ""

    # str_prefix matching (command is a prefix of table entry name)
    for name, fn in _EDITOR_TABLE:
        if name.startswith(command):
            return fn(char, remainder)  # type: ignore[arg-type]

    # invalid subcmd → help, mirroring ROM do_help(ch,"olc")
    return _OLC_HELP


def do_mpedit(char: Character, args: str) -> str:
    """Edit standalone mob-program code blocks.

    # mirroring ROM src/olc_mpcode.c:96-151 do_mpedit()

    Usage:
        mpedit <vnum>          - open existing code block for editing
        mpedit create <vnum>   - create a new code block
    """
    from mud.commands.build import _get_area_for_vnum
    from mud.models.mob import get_mprog_index
    from mud.olc.editor_state import EditorMode

    arg = (args or "").strip()
    if not arg:
        # ROM src/olc_mpcode.c:147-150 — syntax on no args
        return "Sintaxis : mpedit [vnum]\n\r           mpedit create [vnum]\n\r"

    parts = arg.split(None, 1)
    command = parts[0]
    remainder = parts[1] if len(parts) > 1 else ""

    # --- numeric vnum: open existing code block ---
    if command.isdigit():
        vnum = int(command)
        pMcode = get_mprog_index(vnum)
        if pMcode is None:
            # ROM src/olc_mpcode.c:110 — "MPEdit : That vnum does not exist.\n\r"
            return "MPEdit : That vnum does not exist.\n\r"

        ad = _get_area_for_vnum(vnum)
        if ad is None:
            # ROM src/olc_mpcode.c:118 — "MPEdit : VNUM no asignado a ningun area.\n\r"
            return "MPEdit : VNUM no asignado a ningun area.\n\r"

        if not _is_builder(char, ad):
            # ROM src/olc_mpcode.c:124-127
            return "MPEdit : Insuficiente seguridad para editar area.\n\r"

        # ROM src/olc_mpcode.c:129-131 — set pEdit + editor = ED_MPCODE, silent return
        session = getattr(char, "desc", None)
        if session is not None:
            session.editor = "mpedit"
            session.editor_mode = EditorMode.MPCODE
            session.editor_state = {"mpcode": pMcode}
        return ""

    # --- "create" subcommand ---
    if command.lower() == "create":
        if not remainder:
            # ROM src/olc_mpcode.c:139 — "Sintaxis : mpedit create [vnum]\n\r"
            return "Sintaxis : mpedit create [vnum]\n\r"
        return _mpedit_create(char, remainder)

    # --- anything else → double syntax lines ---
    # ROM src/olc_mpcode.c:147-150
    return "Sintaxis : mpedit [vnum]\n\r           mpedit create [vnum]\n\r"


# Helper function


def _mpedit_create(char: Character, argument: str) -> str:
    """Create a new standalone mob-program code block.

    # mirroring ROM src/olc_mpcode.c:153-196 mpedit_create()
    """
    from mud.commands.build import _get_area_for_vnum
    from mud.models.mob import MprogCode, get_mprog_index, mprog_code_registry
    from mud.olc.editor_state import EditorMode

    arg = argument.strip()
    if not arg or not arg.split()[0].isdigit():
        # ROM src/olc_mpcode.c:161 — "Sintaxis : mpedit create [vnum]\n\r"
        return "Sintaxis : mpedit create [vnum]\n\r"

    value = int(arg.split()[0])
    if value < 1:
        return "Sintaxis : mpedit create [vnum]\n\r"

    ad = _get_area_for_vnum(value)
    if ad is None:
        # ROM src/olc_mpcode.c:169 — "MPEdit : VNUM no asignado a ningun area.\n\r"
        return "MPEdit : VNUM no asignado a ningun area.\n\r"

    if not _is_builder(char, ad):
        # ROM src/olc_mpcode.c:175-178
        return "MPEdit : Insuficiente seguridad para crear MobProgs.\n\r"

    if get_mprog_index(value) is not None:
        # ROM src/olc_mpcode.c:182-184 — "MPEdit: Code vnum already exists.\n\r"
        return "MPEdit: Code vnum already exists.\n\r"

    # ROM src/olc_mpcode.c:186-194 — new_mpcode(), set vnum, prepend to mprog_list
    pMcode = MprogCode(vnum=value, code="")
    mprog_code_registry[value] = pMcode

    session = getattr(char, "desc", None)
    if session is not None:
        session.editor = "mpedit"
        session.editor_mode = EditorMode.MPCODE
        session.editor_state = {"mpcode": pMcode}

    # ROM src/olc_mpcode.c:193 — "MobProgram Code Created.\n\r"
    return "MobProgram Code Created.\n\r"

def _is_builder(char: Character, area) -> bool:
    """Check if character can build in an area."""
    # Implementers can build anywhere
    if get_trust(char) >= 60:
        return True

    # Check builder list
    builders = getattr(area, "builders", "")
    char_name = getattr(char, "name", "")

    if char_name.lower() in builders.lower():
        return True

    # Check security
    pcdata = getattr(char, "pcdata", None)
    if pcdata:
        char_security = getattr(pcdata, "security", 0)
        area_security = getattr(area, "security", 9)
        return char_security >= area_security

    return False
