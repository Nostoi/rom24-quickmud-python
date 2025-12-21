from mud.models.area import Area
from mud.models.constants import AreaFlag
from mud.registry import area_registry

from .base_loader import BaseTokenizer
from .help_loader import load_helps
from .mob_loader import load_mobiles
from .mobprog_loader import load_mobprogs
from .obj_loader import load_objects
from .reset_loader import load_resets
from .room_loader import load_rooms
from .shop_loader import load_shops
from .specials_loader import load_specials

SECTION_HANDLERS = {
    "#HELPS": load_helps,
    "#ROOMS": load_rooms,
    "#MOBILES": load_mobiles,
    "#OBJECTS": load_objects,
    "#RESETS": load_resets,
    "#SHOPS": load_shops,
    "#SPECIALS": load_specials,
    "#MOBPROGS": load_mobprogs,
}


def load_area_file(filepath: str) -> Area:
    with open(filepath, encoding="latin-1") as f:
        lines = f.readlines()
    tokenizer = BaseTokenizer(lines)
    area = Area()
    # Mirror ROM load_area defaults so freshly loaded areas age before
    # repopping and expose builder/security metadata to staff tools.
    area.age = 15
    area.nplayer = 0
    area.empty = False
    area.security = 9
    area.builders = "None"
    area.area_flags = AreaFlag.LOADING
    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line == "#AREA":
            file_name = tokenizer.next_line()
            if file_name is None or not file_name.endswith("~"):
                raise ValueError("invalid #AREA header: file name must end with '~'")
            area.file_name = file_name[:-1]

            name = tokenizer.next_line()
            if name is None or not name.endswith("~"):
                raise ValueError("invalid #AREA header: area name must end with '~'")
            if not area.name:
                area.name = name[:-1]

            credits = tokenizer.next_line()
            if credits is None or not credits.endswith("~"):
                raise ValueError("invalid #AREA header: credits must end with '~'")
            if not area.credits:
                area.credits = credits[:-1]

            vnums = tokenizer.next_line()
            if not vnums:
                raise ValueError("invalid #AREA header: missing vnum range line")
            parts = vnums.split()
            if len(parts) < 2:
                raise ValueError("invalid #AREA header: expected at least two integers for vnum range")
            try:
                parsed_min = int(parts[0])
                parsed_max = int(parts[1])
            except ValueError as exc:
                raise ValueError("invalid #AREA header: vnum range must contain integers") from exc
            if parsed_min > parsed_max:
                raise ValueError("invalid #AREA header: min_vnum cannot exceed max_vnum")
            if area.min_vnum == 0:
                area.min_vnum = parsed_min
                area.max_vnum = parsed_max
            if len(parts) >= 4 and area.low_range == 0:
                try:
                    area.low_range = int(parts[2])
                    area.high_range = int(parts[3])
                except ValueError as exc:
                    raise ValueError("invalid #AREA header: optional range values must be integers") from exc
        elif line in SECTION_HANDLERS:
            handler = SECTION_HANDLERS[line]
            handler(tokenizer, area)
        elif line == "#":
            # QuickMUD area files omit the #ROOMS header and use a bare '#'
            load_rooms(tokenizer, area)
        elif line == "#AREADATA":
            while True:
                peek = tokenizer.peek_line()
                if peek is None or peek.startswith("#"):
                    break
                data_line = tokenizer.next_line()
                if data_line.startswith("Builders"):
                    if not data_line.endswith("~"):
                        raise ValueError("invalid #AREADATA entry: Builders value must end with '~'")
                    parts = data_line.split(None, 1)
                    if len(parts) < 2:
                        raise ValueError("invalid #AREADATA entry: Builders requires a value")
                    area.builders = parts[1][:-1]
                elif data_line.startswith("Security"):
                    parts = data_line.split()
                    if len(parts) < 2:
                        raise ValueError("invalid #AREADATA entry: Security requires an integer value")
                    try:
                        area.security = int(parts[1])
                    except ValueError as exc:
                        raise ValueError("invalid #AREADATA entry: Security must be an integer") from exc
                elif data_line.startswith("Flags"):
                    parts = data_line.split()
                    if len(parts) < 2:
                        raise ValueError("invalid #AREADATA entry: Flags requires an integer value")
                    try:
                        area.area_flags = int(parts[1])
                    except ValueError as exc:
                        raise ValueError("invalid #AREADATA entry: Flags must be an integer") from exc
                elif data_line.startswith("Name"):
                    parts = data_line.split(None, 1)
                    if len(parts) < 2 or not parts[1].endswith("~"):
                        raise ValueError("invalid #AREADATA entry: Name value must end with '~'")
                    area.name = parts[1][:-1]
                elif data_line.startswith("Credits"):
                    parts = data_line.split(None, 1)
                    if len(parts) < 2 or not parts[1].endswith("~"):
                        raise ValueError("invalid #AREADATA entry: Credits value must end with '~'")
                    area.credits = parts[1][:-1]
                elif data_line.startswith("VNUMs"):
                    parts = data_line.split()
                    if len(parts) < 3:
                        raise ValueError("invalid #AREADATA entry: VNUMs requires at least two integers")
                    try:
                        min_vnum = int(parts[1])
                        max_vnum = int(parts[2])
                    except ValueError as exc:
                        raise ValueError("invalid #AREADATA entry: VNUMs values must be integers") from exc
                    if min_vnum > max_vnum:
                        raise ValueError("invalid #AREADATA entry: min_vnum cannot exceed max_vnum")
                    area.min_vnum = min_vnum
                    area.max_vnum = max_vnum
                    if len(parts) >= 5:
                        try:
                            area.low_range = int(parts[3])
                            area.high_range = int(parts[4])
                        except ValueError as exc:
                            raise ValueError("invalid #AREADATA entry: optional range values must be integers") from exc
        elif line.startswith("#$") or line == "$":
            break
    key = area.min_vnum
    area.vnum = area.min_vnum
    # START enforce unique area vnum
    if key != 0 and key in area_registry and area_registry[key].file_name != area.file_name:
        raise ValueError(f"duplicate area vnum {key}")
    # END enforce unique area vnum
    area_registry[key] = area

    return area
