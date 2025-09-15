from __future__ import annotations
from mud.loaders import load_all_areas
from mud.loaders.json_area_loader import load_all_areas_from_json
from mud.loaders.json_loader import load_all_areas_from_json as load_enhanced_json
from mud.registry import room_registry, area_registry, mob_registry, obj_registry
from mud.db.session import SessionLocal
from mud.db import models
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.spawning.reset_handler import apply_resets
from .linking import link_exits
from mud.security import bans

# Global skill registry for world initialization
skill_registry = None


def load_world_from_db() -> bool:
    """Populate registries from the database."""
    session = SessionLocal()

    db_rooms = session.query(models.Room).all()
    for db_room in db_rooms:
        room = models_to_room(db_room)
        room_registry[room.vnum] = room

    db_exits = session.query(models.Exit).all()
    for db_exit in db_exits:
        origin_room = session.query(models.Room).get(db_exit.room_id)
        source = room_registry.get(origin_room.vnum) if origin_room else None
        target = room_registry.get(db_exit.to_room_vnum)
        if source and target:
            if len(source.exits) <= int(db_exit.direction):
                source.exits.extend([None] * (int(db_exit.direction) - len(source.exits) + 1))
            source.exits[int(db_exit.direction)] = target

    for db_mob in session.query(models.MobPrototype).all():
        mob_registry[db_mob.vnum] = models_to_mob(db_mob)

    for db_obj in session.query(models.ObjPrototype).all():
        obj_registry[db_obj.vnum] = models_to_obj(db_obj)

    print(
        f"\u2705 Loaded {len(room_registry)} rooms, {len(mob_registry)} mobs, {len(obj_registry)} objects."
    )
    return True


def models_to_room(db_room: models.Room):
    from mud.models.room import Room

    return Room(
        vnum=db_room.vnum,
        name=db_room.name,
        description=db_room.description,
        sector_type=db_room.sector_type or 0,
        room_flags=db_room.room_flags or 0,
        exits=[None] * 10,
    )


def models_to_mob(db_mob: models.MobPrototype):
    from mud.models.mob import MobIndex

    return MobIndex(
        vnum=db_mob.vnum,
        player_name=db_mob.name,
        short_descr=db_mob.short_desc,
        long_descr=db_mob.long_desc,
        level=db_mob.level or 0,
        alignment=db_mob.alignment or 0,
    )


def models_to_obj(db_obj: models.ObjPrototype):
    from mud.models.obj import ObjIndex

    return ObjIndex(
        vnum=db_obj.vnum,
        name=db_obj.name,
        short_descr=db_obj.short_desc,
        description=db_obj.long_desc,
        item_type=db_obj.item_type or 0,
        extra_flags=db_obj.flags or 0,
        value=[db_obj.value0, db_obj.value1, db_obj.value2, db_obj.value3],
    )


def initialize_world(area_list_path: str | None = "area/area.lst", use_json: bool = True) -> None:
    """Initialize world from files or database.
    
    Args:
        area_list_path: Path to area.lst file (for legacy .are loading)
        use_json: If True, load from JSON files in data/areas/. If False, use legacy .are files.
    """
    # Tiny fix: ensure a clean ban registry at boot and between tests.
    # ROM loads bans from disk at boot; tests may add bans in-memory.
    # Clearing here avoids leakage across test modules without affecting
    # persistence tests which explicitly save/load.
    bans.clear_all_bans()
    
    # Load skills registry from JSON
    from mud.skills.registry import SkillRegistry
    from pathlib import Path
    skills_path = Path("data/skills.json")
    if skills_path.exists():
        try:
            global skill_registry
            skill_registry = SkillRegistry()
            skill_registry.load(skills_path)
            print(f"✅ Loaded {len(skill_registry.skills)} skills from {skills_path}")
        except Exception as e:
            print(f"Warning: Failed to load skills from {skills_path}: {e}")
            skill_registry = None
    
    # Load shops from JSON (needed for shopkeeper detection in resets)
    from mud.registry import shop_registry
    from mud.loaders.shop_loader import Shop
    import json
    shops_path = Path("data/shops.json")
    if shops_path.exists():
        try:
            with open(shops_path, 'r') as f:
                shops_data = json.load(f)
            shop_registry.clear()
            for shop_data in shops_data:
                # Convert string buy_types back to int list for compatibility
                buy_types = []
                for bt in shop_data.get('buy_types', []):
                    if isinstance(bt, str):
                        from mud.models.constants import ItemType
                        try:
                            buy_types.append(ItemType[bt.upper()].value)
                        except (KeyError, AttributeError):
                            buy_types.append(0)  # unknown type
                    else:
                        buy_types.append(bt)
                
                shop_registry[shop_data['keeper']] = Shop(
                    keeper=shop_data['keeper'],
                    buy_types=buy_types,
                    profit_buy=shop_data.get('profit_buy', 100),
                    profit_sell=shop_data.get('profit_sell', 100),
                    open_hour=shop_data.get('open_hour', 0),
                    close_hour=shop_data.get('close_hour', 23),
                )
            print(f"✅ Loaded {len(shop_registry)} shops from {shops_path}")
        except Exception as e:
            print(f"Warning: Failed to load shops from {shops_path}: {e}")
    
    if area_list_path:
        if use_json:
            # Load from JSON files using enhanced field mapping
            from mud.loaders.json_loader import load_all_areas_from_json
            json_areas = load_all_areas_from_json("data/areas")
            # Areas are already registered in area_registry by the JSON loader
        else:
            # Load from legacy .are files
            load_all_areas(area_list_path)
        link_exits()
        for area in area_registry.values():
            apply_resets(area)
    else:
        load_world_from_db()


def fix_all_exits() -> None:
    link_exits()


def create_test_character(name: str, room_vnum: int) -> Character:
    room = room_registry.get(room_vnum)
    char = Character(name=name)
    # ROM default: new players start standing.
    char.position = int(Position.STANDING)
    if room:
        room.add_character(char)
    character_registry.append(char)
    return char
