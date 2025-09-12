from .base_loader import BaseTokenizer
from .room_loader import load_rooms
from .mob_loader import load_mobiles
from .obj_loader import load_objects
from .reset_loader import load_resets
from .shop_loader import load_shops
from .specials_loader import load_specials
from mud.models.area import Area
from mud.registry import area_registry

SECTION_HANDLERS = {
    "#ROOMS": load_rooms,
    "#MOBILES": load_mobiles,
    "#OBJECTS": load_objects,
    "#RESETS": load_resets,
    "#SHOPS": load_shops,
    "#SPECIALS": load_specials,
}


def load_area_file(filepath: str) -> Area:
    with open(filepath, 'r', encoding='latin-1') as f:
        lines = f.readlines()
    tokenizer = BaseTokenizer(lines)
    area = Area()
    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line == '#AREA':
            area.file_name = tokenizer.next_line().rstrip('~')
            area.name = tokenizer.next_line().rstrip('~')
            area.credits = tokenizer.next_line().rstrip('~')
            vnums = tokenizer.next_line()
            if vnums:
                parts = vnums.split()
                if len(parts) >= 2:
                    area.min_vnum = int(parts[0])
                    area.max_vnum = int(parts[1])
        elif line in SECTION_HANDLERS:
            handler = SECTION_HANDLERS[line]
            handler(tokenizer, area)
        elif line == "#AREADATA":
            while True:
                peek = tokenizer.peek_line()
                if peek is None or peek.startswith('#'):
                    break
                data_line = tokenizer.next_line()
                if data_line.startswith('Builders'):
                    area.builders = data_line.split(None, 1)[1].rstrip('~')
                elif data_line.startswith('Security'):
                    parts = data_line.split()
                    if len(parts) > 1:
                        area.security = int(parts[1])
                elif data_line.startswith('Flags'):
                    parts = data_line.split()
                    if len(parts) > 1:
                        area.area_flags = int(parts[1])
        elif line.startswith('#$') or line == '$':
            break
    key = area.min_vnum
    area.vnum = area.min_vnum
    # START enforce unique area vnum
    if (
        key != 0
        and key in area_registry
        and area_registry[key].file_name != area.file_name
    ):
        raise ValueError(f"duplicate area vnum {key}")
    # END enforce unique area vnum
    area_registry[key] = area

    return area
