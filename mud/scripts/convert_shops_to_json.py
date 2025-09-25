import argparse
import json
from pathlib import Path

from mud.loaders.area_loader import load_area_file
from mud.models.constants import ItemType
from mud.registry import area_registry, mob_registry, obj_registry, room_registry, shop_registry


def clear_registries() -> None:
    """Reset all global registries."""
    shop_registry.clear()
    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()


def shop_to_dict(shop) -> dict:
    buy_types = []
    for t in shop.buy_types:
        if t == 0:
            continue
        try:
            buy_types.append(ItemType(t).name.lower())
        except ValueError:
            buy_types.append(str(t))
    return {
        "keeper": shop.keeper,
        "buy_types": buy_types,
        "profit_buy": shop.profit_buy,
        "profit_sell": shop.profit_sell,
        "open_hour": shop.open_hour,
        "close_hour": shop.close_hour,
    }


def convert_shops(area_list: str) -> list[dict]:
    """Load areas listed in ``area_list`` and return shop dicts."""
    clear_registries()
    area_dir = Path(area_list).parent
    with open(area_list, encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("$"):
                continue
            load_area_file(str(area_dir / line))
    return [shop_to_dict(s) for s in shop_registry.values()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert #SHOPS to JSON")
    parser.add_argument("area_list", help="Path to area.lst")
    parser.add_argument("--out", default=Path("data/shops.json"), type=Path, help="Output JSON file")
    args = parser.parse_args()
    data = convert_shops(args.area_list)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()
