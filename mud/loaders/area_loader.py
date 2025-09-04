from pathlib import Path
from .base_loader import BaseTokenizer
from .room_loader import load_rooms
from .mob_loader import load_mobiles
from .obj_loader import load_objects
from .reset_loader import load_resets
from .shop_loader import load_shops
from mud.models.area import Area
from mud.registry import area_registry

SECTION_HANDLERS = {
    "#ROOMS": load_rooms,
    "#MOBILES": load_mobiles,
    "#OBJECTS": load_objects,
    "#RESETS": load_resets,
    "#SHOPS": load_shops,
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
        if line.startswith('#AREA'):
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
        elif line.startswith('#$') or line == '$':
            break
    key = area.file_name or filepath
    area_registry[key] = area

    return area
