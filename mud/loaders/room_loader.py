from mud.models.constants import EX_ISDOOR, EX_NOPASS, EX_PICKPROOF, RoomFlag, convert_flags_from_letters
from mud.models.room import Exit, ExtraDescr, Room
from mud.registry import room_registry

from .base_loader import BaseTokenizer


def _parse_room_flag_field(token: str) -> int:
    """Decode a ROM room-flag token (letters or number) into a bitmask.

    Mirrors ROM ``src/db.c:2743 fread_flag``: a bitvector may be a plain
    integer (``0``), a letter bitvector (``ADR``), or a mixed/``|``-joined
    form. ``int()`` cannot decode letters, so try numeric first then fall
    back to letter decoding.
    """
    normalized = token.replace("|", " ").strip()
    if not normalized:
        return 0
    try:
        return int(normalized, 0)
    except ValueError:
        pass
    letters = "".join(normalized.split())
    return int(convert_flags_from_letters(letters, RoomFlag))


def _locks_to_exit_bits(locks: int) -> int:
    """Translate ROM room-loader ``locks`` encoding into exit bitflags.

    ROM Reference: ``src/db.c:1218-1236``.
    """
    match locks:
        case 1:
            return EX_ISDOOR
        case 2:
            return EX_ISDOOR | EX_PICKPROOF
        case 3:
            return EX_ISDOOR | EX_NOPASS
        case 4:
            return EX_ISDOOR | EX_NOPASS | EX_PICKPROOF
        case _:
            return 0


def load_rooms(tokenizer: BaseTokenizer, area):
    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line.startswith("#"):
            if line == "#0":
                break
            vnum = int(line[1:])
            name = tokenizer.next_line().rstrip("~")
            desc = tokenizer.read_string_tilde()
            flags_line = tokenizer.next_line()
            while flags_line is not None and flags_line == "~":
                flags_line = tokenizer.next_line()
            tokens = flags_line.split() if flags_line else []
            # ROM src/db.c:1158-1163 load_rooms: the room header line is
            # `<area-number(discard)> <room_flags via fread_flag> <sector_type>`
            # (always 3 fields). DB-001: the loader previously read
            # int(tokens[0]) (the discarded area-number, always 0) and could not
            # letter-decode ROM bitvectors, dropping every room flag game-wide.
            assert len(tokens) == 3, f"room {vnum}: expected 3 header tokens, got {tokens!r}"
            # /* Area number */ tokens[0] discarded
            room_flags = _parse_room_flag_field(tokens[1])
            sector_type = int(tokens[2])
            # NB: ROM's "horrible hack" SET_BIT(ROOM_LAW) for vnum 3000-3399
            # (src/db.c:1161-1162) is a *load-time* semantic applied at runtime
            # by json_loader.py (the live path), not baked into the serialized
            # .are flags here — the converter's job is to serialize the file's
            # declared flags faithfully.
            room = Room(
                vnum=vnum, name=name, description=desc, room_flags=room_flags, sector_type=sector_type, area=area
            )
            room_registry[vnum] = room
            # parse additional blocks until 'S'
            while True:
                peek = tokenizer.peek_line()
                if peek is None:
                    break
                if peek.startswith("H") or peek.startswith("M"):
                    line = tokenizer.next_line()
                    tokens = line.split()
                    idx = 0
                    while idx < len(tokens):
                        code = tokens[idx]
                        if code == "H" and idx + 1 < len(tokens):
                            try:
                                room.heal_rate = int(tokens[idx + 1])
                            except ValueError:
                                pass
                            idx += 2
                            continue
                        if code == "M" and idx + 1 < len(tokens):
                            try:
                                room.mana_rate = int(tokens[idx + 1])
                            except ValueError:
                                pass
                            idx += 2
                            continue
                        idx += 1
                    continue
                if peek.startswith("C"):
                    line = tokenizer.next_line()
                    clan_value = line[1:].strip()
                    if clan_value.endswith("~"):
                        clan_value = clan_value[:-1]
                    if clan_value:
                        try:
                            room.clan = int(clan_value)
                        except ValueError:
                            room.clan = clan_value
                    continue
                if peek.startswith("O"):
                    line = tokenizer.next_line()
                    owner_value = line[1:].strip()
                    if owner_value.endswith("~"):
                        owner_value = owner_value[:-1]
                    room.owner = owner_value
                    continue
                if peek.startswith("D"):
                    dir_line = tokenizer.next_line()
                    exit_desc = tokenizer.read_string_tilde()
                    exit_keywords = tokenizer.read_string_tilde()
                    info_line = tokenizer.next_line()
                    if info_line is None:
                        break
                    info_parts = info_line.split()
                    exit_flags = info_parts[0] if len(info_parts) >= 1 else "0"
                    try:
                        exit_bits = _locks_to_exit_bits(int(exit_flags))
                    except ValueError:
                        exit_bits = 0
                    if len(info_parts) >= 3:
                        key = int(info_parts[1])
                        to_vnum = int(info_parts[2])
                    else:
                        key = 0
                        to_vnum = 0
                    exit_obj = Exit(
                        vnum=to_vnum,
                        key=key,
                        description=exit_desc,
                        keyword=exit_keywords,
                        flags=exit_bits,
                        exit_info=exit_bits,
                        rs_flags=exit_bits,
                    )
                    # direction char at Dn
                    idx = int(dir_line[1])
                    if idx < len(room.exits):
                        room.exits[idx] = exit_obj
                    continue
                if peek.startswith("E"):
                    tokenizer.next_line()
                    keyword = tokenizer.next_line().rstrip("~")
                    descr = tokenizer.read_string_tilde()
                    room.extra_descr.append(ExtraDescr(keyword=keyword, description=descr))
                    continue
                if peek == "S":
                    tokenizer.next_line()
                    break
                if peek.startswith("#"):
                    break
                # consume unknown line
                tokenizer.next_line()
        elif line == "$":
            break
