from mud.models.room import Room, Exit, ExtraDescr
from mud.registry import room_registry
from .base_loader import BaseTokenizer


def load_rooms(tokenizer: BaseTokenizer, area):
    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line.startswith('#'):
            if line == '#0':
                break
            vnum = int(line[1:])
            name = tokenizer.next_line().rstrip('~')
            desc = tokenizer.read_string_tilde()
            flags_line = tokenizer.next_line()
            tokens = flags_line.split()
            room_flags = int(tokens[0]) if tokens else 0
            sector_type = int(tokens[-1]) if tokens else 0
            room = Room(vnum=vnum, name=name, description=desc, room_flags=room_flags, sector_type=sector_type, area=area)
            room_registry[vnum] = room
            # parse additional blocks until 'S'
            while True:
                peek = tokenizer.peek_line()
                if peek is None:
                    break
                if peek.startswith('D'):
                    dir_line = tokenizer.next_line()
                    exit_desc = tokenizer.read_string_tilde()
                    exit_keywords = tokenizer.read_string_tilde()
                    info_line = tokenizer.next_line()
                    if info_line is None:
                        break
                    info_parts = info_line.split()
                    exit_flags = info_parts[0] if len(info_parts) >= 1 else '0'
                    if len(info_parts) >= 3:
                        key = int(info_parts[1])
                        to_vnum = int(info_parts[2])
                    else:
                        key = 0
                        to_vnum = 0
                    exit_obj = Exit(vnum=to_vnum, key=key, description=exit_desc, keyword=exit_keywords, flags=exit_flags)
                    # direction char at Dn
                    idx = int(dir_line[1])
                    if idx < len(room.exits):
                        room.exits[idx] = exit_obj
                    continue
                if peek.startswith('E'):
                    tokenizer.next_line()
                    keyword = tokenizer.next_line().rstrip('~')
                    descr = tokenizer.read_string_tilde()
                    room.extra_descr.append(ExtraDescr(keyword=keyword, description=descr))
                    continue
                if peek == 'S':
                    tokenizer.next_line()
                    break
                if peek.startswith('#'):
                    break
                # consume unknown line
                tokenizer.next_line()
        elif line == '$':
            break
