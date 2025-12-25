from pathlib import Path

from mud.registry import area_registry, mob_registry, obj_registry, room_registry, shop_registry

from .area_loader import load_area_file
from .json_loader import load_all_areas_from_json  # Use the FULL loader with resets

__all__ = ["load_area_file", "load_all_areas_from_json", "load_all_areas"]


def load_all_areas(list_path: str = "area/area.lst", use_json: bool = True):
    """Load all areas from either JSON or .are files.
    
    Args:
        list_path: Path to area.lst file (only used if use_json=False)
        use_json: If True, load from data/areas/*.json; if False, load from .are files
    """
    # Clear all registries before loading to prevent conflicts
    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    shop_registry.clear()
    
    if use_json:
        # Load from JSON files (modern, with resets)
        load_all_areas_from_json("data/areas")
        return
    
    # Legacy: Load from .are files
    sentinel_found = False
    with open(list_path, encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line == "$":
                sentinel_found = True
                break
            path = Path("area") / line
            load_area_file(str(path))
    if not sentinel_found:
        raise ValueError("area.lst missing '$' sentinel")
