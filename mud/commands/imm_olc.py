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

    if len(parts) >= 2 and parts[0].isdigit():
        idx = int(parts[0])
        action = parts[1].lower()

        if action == "delete":
            resets = getattr(room, "resets", [])
            if idx < 1 or idx > len(resets):
                return "Reset not found."

            resets.pop(idx - 1)
            return "Reset deleted."

        if action == "mob" and len(parts) >= 3:
            if not parts[2].isdigit():
                return "Mob vnum must be a number."

            from mud import registry
            vnum = int(parts[2])

            if vnum not in registry.mob_prototypes:
                return "No mobile has that vnum."

            # Add reset (simplified)
            resets = getattr(room, "resets", None)
            if resets is None:
                room.resets = []
                resets = room.resets

            # Create reset entry
            from types import SimpleNamespace
            reset = SimpleNamespace(command='M', arg1=vnum, arg2=1, arg3=room.vnum)
            resets.insert(idx - 1 if idx > 0 else len(resets), reset)

            return f"Mobile reset added at position {idx}."

        if action == "obj" and len(parts) >= 3:
            if not parts[2].isdigit():
                return "Object vnum must be a number."

            from mud import registry
            vnum = int(parts[2])

            if vnum not in registry.obj_prototypes:
                return "No object has that vnum."

            # Add reset
            resets = getattr(room, "resets", None)
            if resets is None:
                room.resets = []
                resets = room.resets

            from types import SimpleNamespace
            reset = SimpleNamespace(command='O', arg1=vnum, arg2=0, arg3=room.vnum)
            resets.insert(idx - 1 if idx > 0 else len(resets), reset)

            return f"Object reset added at position {idx}."

    return ("Syntax:\n"
            "  resets                       - Display resets\n"
            "  resets <num> delete          - Delete reset\n"
            "  resets <num> mob <vnum>      - Add mob reset\n"
            "  resets <num> obj <vnum>      - Add obj reset")


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
    """
    General edit command router.

    ROM Reference: src/olc.c

    Usage:
    - edit room [vnum]      - Edit a room
    - edit mob <vnum>       - Edit a mobile
    - edit obj <vnum>       - Edit an object
    - edit area [vnum]      - Edit an area
    """
    if not args or not args.strip():
        return ("Syntax:\n"
                "  edit room [vnum]      - Edit a room\n"
                "  edit mob <vnum>       - Edit a mobile\n"
                "  edit obj <vnum>       - Edit an object\n"
                "  edit area [vnum]      - Edit an area")

    parts = args.strip().split()
    edit_type = parts[0].lower()
    vnum_arg = parts[1] if len(parts) > 1 else None

    if edit_type == "room":
        if vnum_arg and vnum_arg.isdigit():
            return f"Entering room editor for vnum {vnum_arg}."
        room = getattr(char, "room", None)
        if room:
            return f"Entering room editor for vnum {getattr(room, 'vnum', 0)}."
        return "You're not in a room."

    if edit_type in ("mob", "mobile"):
        if not vnum_arg or not vnum_arg.isdigit():
            return "Syntax: edit mob <vnum>"
        return f"Entering mobile editor for vnum {vnum_arg}."

    if edit_type in ("obj", "object"):
        if not vnum_arg or not vnum_arg.isdigit():
            return "Syntax: edit obj <vnum>"
        return f"Entering object editor for vnum {vnum_arg}."

    if edit_type == "area":
        if vnum_arg and vnum_arg.isdigit():
            return f"Entering area editor for area {vnum_arg}."
        room = getattr(char, "room", None)
        if room:
            area = getattr(room, "area", None)
            if area:
                return f"Entering area editor for '{getattr(area, 'name', 'Unknown')}'."
        return "You're not in an area."

    return ("Syntax:\n"
            "  edit room [vnum]      - Edit a room\n"
            "  edit mob <vnum>       - Edit a mobile\n"
            "  edit obj <vnum>       - Edit an object\n"
            "  edit area [vnum]      - Edit an area")


def do_mpedit(char: Character, args: str) -> str:
    """
    Edit mob programs.

    ROM Reference: src/olc.c

    Usage: mpedit <vnum>
    """
    if not args or not args.strip():
        return "Syntax: mpedit <vnum>"

    vnum_arg = args.strip().split()[0]

    if not vnum_arg.isdigit():
        return "Vnum must be numeric."

    from mud import registry
    vnum = int(vnum_arg)

    if vnum not in registry.mob_prototypes:
        return "No mobile has that vnum."

    return f"Entering mobprog editor for mobile vnum {vnum}."


# Helper function

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
