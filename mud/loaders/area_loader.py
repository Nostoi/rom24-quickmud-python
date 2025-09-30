from mud.models.area import Area
from mud.registry import area_registry

from .base_loader import BaseTokenizer
from .mob_loader import load_mobiles
from .obj_loader import load_objects
from .reset_loader import load_resets
from .room_loader import load_rooms
from .shop_loader import load_shops
from .specials_loader import load_specials

SECTION_HANDLERS = {
    "#ROOMS": load_rooms,
    "#MOBILES": load_mobiles,
    "#OBJECTS": load_objects,
    "#RESETS": load_resets,
    "#SHOPS": load_shops,
    "#SPECIALS": load_specials,
}


def load_area_file(filepath: str) -> Area:
    with open(filepath, encoding="latin-1") as f:
        lines = f.readlines()
    tokenizer = BaseTokenizer(lines)
    area = Area()
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
            area.name = name[:-1]

            credits = tokenizer.next_line()
            if credits is None or not credits.endswith("~"):
                raise ValueError("invalid #AREA header: credits must end with '~'")
            area.credits = credits[:-1]

            vnums = tokenizer.next_line()
            if not vnums:
                raise ValueError("invalid #AREA header: missing vnum range line")
            parts = vnums.split()
            if len(parts) < 2:
                raise ValueError(
                    "invalid #AREA header: expected at least two integers for vnum range"
                )
            try:
                area.min_vnum = int(parts[0])
                area.max_vnum = int(parts[1])
            except ValueError as exc:
                raise ValueError(
                    "invalid #AREA header: vnum range must contain integers"
                ) from exc
            if area.min_vnum > area.max_vnum:
                raise ValueError(
                    "invalid #AREA header: min_vnum cannot exceed max_vnum"
                )
            if len(parts) >= 4:
                try:
                    area.low_range = int(parts[2])
                    area.high_range = int(parts[3])
                except ValueError as exc:
                    raise ValueError(
                        "invalid #AREA header: optional range values must be integers"
                    ) from exc
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
                        raise ValueError(
                            "invalid #AREADATA entry: Builders value must end with '~'"
                        )
                    parts = data_line.split(None, 1)
                    if len(parts) < 2:
                        raise ValueError(
                            "invalid #AREADATA entry: Builders requires a value"
                        )
                    area.builders = parts[1][:-1]
                elif data_line.startswith("Security"):
                    parts = data_line.split()
                    if len(parts) < 2:
                        raise ValueError(
                            "invalid #AREADATA entry: Security requires an integer value"
                        )
                    try:
                        area.security = int(parts[1])
                    except ValueError as exc:
                        raise ValueError(
                            "invalid #AREADATA entry: Security must be an integer"
                        ) from exc
                elif data_line.startswith("Flags"):
                    parts = data_line.split()
                    if len(parts) < 2:
                        raise ValueError(
                            "invalid #AREADATA entry: Flags requires an integer value"
                        )
                    try:
                        area.area_flags = int(parts[1])
                    except ValueError as exc:
                        raise ValueError(
                            "invalid #AREADATA entry: Flags must be an integer"
                        ) from exc
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
