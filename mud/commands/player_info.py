"""
Player info/config commands - scroll, show, play, info, and aliases.

ROM Reference: src/act_info.c, src/music.c
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import CommFlag


def do_scroll(char: Character, args: str) -> str:
    """
    Set number of lines per page for long output.

    ROM Reference: src/act_info.c do_scroll (lines 558-604)

    Usage:
    - scroll        - Show current setting
    - scroll 0      - Disable paging
    - scroll <n>    - Set to n lines (10-100)
    """
    if not args or not args.strip():
        lines = getattr(char, "lines", 0)
        if lines == 0:
            return "You do not page long messages."
        else:
            return f"You currently display {lines + 2} lines per page."

    arg = args.strip().split()[0]

    if not arg.isdigit():
        return "You must provide a number."

    lines = int(arg)

    if lines == 0:
        char.lines = 0
        return "Paging disabled."

    if lines < 10 or lines > 100:
        return "You must provide a reasonable number."

    char.lines = lines - 2
    return f"Scroll set to {lines} lines."


def do_show(char: Character, args: str) -> str:
    """
    Toggle showing affects in score display.

    ROM Reference: src/act_info.c do_show (lines 905-918)

    Usage: show
    """
    comm_flags = getattr(char, "comm", 0)

    if comm_flags & CommFlag.SHOW_AFFECTS:
        char.comm = comm_flags & ~CommFlag.SHOW_AFFECTS
        return "Affects will no longer be shown in score."
    else:
        char.comm = comm_flags | CommFlag.SHOW_AFFECTS
        return "Affects will now be shown in score."


def do_play(char: Character, args: str) -> str:
    """Play a song on a jukebox.

    ROM Reference: src/music.c:220-354 (`do_play`).
    """
    # mirroring ROM src/music.c:234-238 — empty argument → "Play what?"
    if not args or not args.strip():
        return "Play what?"

    room = getattr(char, "room", None)
    if not room:
        return "You see nothing to play."

    from mud.models.constants import ItemType
    from mud.world.vision import can_see_object

    # mirroring ROM src/music.c:229-232 — first ITEM_JUKEBOX in the room
    # that `can_see_obj(ch, juke)` accepts (skips invisible/dark-room hits).
    jukebox = None
    contents = getattr(room, "contents", [])
    for obj in contents:
        item_type = getattr(obj, "item_type", None)
        if item_type is None:
            proto = getattr(obj, "prototype", None)
            if proto:
                item_type = getattr(proto, "item_type", None)

        if (item_type == ItemType.JUKEBOX or str(item_type) == "jukebox") and can_see_object(char, obj):
            jukebox = obj
            break

    if jukebox is None:
        return "You see nothing to play."

    parts = args.strip().split()
    arg = parts[0].lower()

    from mud.music import MAX_GLOBAL, MAX_SONGS, channel_songs, song_table

    if arg == "list":
        # mirroring ROM src/music.c:263-265 — capitalize the first character of the header.
        juke_name = getattr(jukebox, "short_descr", None) or "the jukebox"
        header_raw = f"{juke_name} has the following songs available:"
        header = header_raw[:1].upper() + header_raw[1:]

        # mirroring ROM src/music.c:253-261 — `play list artist [<prefix>]`.
        rest = parts[1:]
        artist_mode = False
        if rest and rest[0].lower() == "artist":
            artist_mode = True
            rest = rest[1:]
        match_prefix = " ".join(rest).lower() if rest else ""

        out_lines: list[str] = [header]
        col = 0
        row_buf = ""
        for idx in range(MAX_SONGS):
            song = song_table[idx]
            if song is None or song.name is None:
                # mirroring ROM src/music.c:269-270 — first NULL entry stops the scan.
                break
            if artist_mode:
                # mirroring ROM src/music.c:272-275 — str_prefix(argument, song.group).
                if match_prefix and not song.group.lower().startswith(match_prefix):
                    continue
                out_lines.append(f"{song.group:<39} {song.name:<39}")
            else:
                # mirroring ROM src/music.c:276-282 — str_prefix(argument, song.name).
                if match_prefix and not song.name.lower().startswith(match_prefix):
                    continue
                if col % 2 == 0:
                    row_buf = f"{song.name:<35} "
                else:
                    row_buf += f"{song.name:<35}"
                    out_lines.append(row_buf)
                    row_buf = ""
                col += 1

        # mirroring ROM src/music.c:286-287 — flush a trailing odd column.
        if not artist_mode and col % 2 != 0:
            out_lines.append(row_buf.rstrip())

        return "\n".join(out_lines)

    # mirroring ROM src/music.c:294-298 — "loud" prefix triggers global queue.
    global_play = False
    if arg == "loud":
        global_play = True
        remainder = parts[1:]
    else:
        remainder = parts

    # mirroring ROM src/music.c:300-304 — empty after stripping "loud".
    if not remainder:
        return "Play what?"

    needle = " ".join(remainder).lower()

    # mirroring ROM src/music.c:306-311 — tail slot occupied → queue full.
    if global_play:
        if channel_songs[MAX_GLOBAL] > -1:
            return "The jukebox is full up right now."
    else:
        values = jukebox.value
        if len(values) < 5:
            values.extend([-1] * (5 - len(values)))
        if values[4] > -1:
            return "The jukebox is full up right now."

    # mirroring ROM src/music.c:313-328 — first str_prefix match wins; an empty
    # slot or end-of-table both surface as "That song isn't available."
    selected = -1
    for idx in range(MAX_SONGS):
        song = song_table[idx]
        if song is None or song.name is None:
            break
        if song.name.lower().startswith(needle):
            selected = idx
            break

    if selected < 0:
        return "That song isn't available."

    if global_play:
        # mirroring ROM src/music.c:332-341 — first free channel_songs[1..MAX_GLOBAL] slot.
        for slot in range(1, MAX_GLOBAL + 1):
            if channel_songs[slot] < 0:
                if slot == 1:
                    channel_songs[0] = -1
                channel_songs[slot] = selected
                break
    else:
        # mirroring ROM src/music.c:343-352 — first free juke->value[1..4] slot.
        values = jukebox.value
        for slot in range(1, 5):
            if values[slot] < 0:
                if slot == 1:
                    values[0] = -1
                values[slot] = selected
                break

    return "Coming right up."


def do_info(char: Character, args: str) -> str:
    """
    Alias for groups command - show group status.

    ROM Reference: ROM uses this as alias for do_groups

    Usage: info
    """
    from mud.commands.group_commands import do_group

    return do_group(char, "")


