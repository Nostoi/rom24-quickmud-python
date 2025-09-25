"""One-time migration script to populate the database from .are files."""

from mud.db import models
from mud.db.session import SessionLocal, engine
from mud.loaders import load_all_areas
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world.linking import link_exits


def migrate(area_list_path: str = "area/area.lst") -> None:
    load_all_areas(area_list_path)
    link_exits()
    models.Base.metadata.create_all(engine)
    session = SessionLocal()

    area_map = {}
    for area in area_registry.values():
        db_area = models.Area(
            vnum=area.vnum,
            name=area.name,
            min_vnum=area.min_vnum,
            max_vnum=area.max_vnum,
        )
        session.add(db_area)
        session.flush()
        area_map[area] = db_area

    room_map = {}
    for room in room_registry.values():
        db_room = models.Room(
            vnum=room.vnum,
            name=room.name,
            description=room.description,
            sector_type=room.sector_type,
            room_flags=room.room_flags,
            area=area_map.get(room.area),
        )
        session.add(db_room)
        session.flush()
        room_map[room] = db_room

    for room in room_registry.values():
        db_room = room_map[room]
        for direction, exit_obj in enumerate(room.exits):
            if exit_obj and exit_obj.vnum:
                session.add(
                    models.Exit(
                        room=db_room,
                        direction=str(direction),
                        to_room_vnum=exit_obj.vnum,
                    )
                )

    for mob in mob_registry.values():
        session.add(
            models.MobPrototype(
                vnum=mob.vnum,
                name=mob.player_name,
                short_desc=mob.short_descr,
                long_desc=mob.long_descr,
                level=mob.level,
                alignment=mob.alignment,
            )
        )

    for obj in obj_registry.values():
        session.add(
            models.ObjPrototype(
                vnum=obj.vnum,
                name=obj.name,
                short_desc=obj.short_descr,
                long_desc=obj.description,
                item_type=obj.item_type,
                flags=obj.extra_flags,
                value0=obj.value[0] if len(obj.value) > 0 else None,
                value1=obj.value[1] if len(obj.value) > 1 else None,
                value2=obj.value[2] if len(obj.value) > 2 else None,
                value3=obj.value[3] if len(obj.value) > 3 else None,
            )
        )

    session.commit()
    session.close()
    print("✅ Migration complete")


if __name__ == "__main__":
    migrate()
