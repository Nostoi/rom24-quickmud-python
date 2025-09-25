from __future__ import annotations

from mud.db.models import Character as DBCharacter
from mud.db.models import ObjectInstance as DBObjectInstance
from mud.models.object import Object
from mud.registry import obj_registry


def load_objects_for_character(db_char: DBCharacter) -> tuple[list[Object], dict[str, Object]]:
    inventory: list[Object] = []
    equipment: dict[str, Object] = {}

    for inst in db_char.objects:
        proto = obj_registry.get(inst.prototype_vnum)
        if not proto:
            continue
        obj = Object(instance_id=inst.id, prototype=proto)
        if inst.location and inst.location.startswith("equipment:"):
            slot = inst.location.split(":", 1)[1]
            equipment[slot] = obj
        else:
            inventory.append(obj)

    return inventory, equipment


def save_objects_for_character(session, char, db_char: DBCharacter):
    session.query(DBObjectInstance).filter_by(character_id=db_char.id).delete()

    for obj in char.inventory:
        inst = DBObjectInstance(
            prototype_vnum=obj.prototype.vnum,
            location="inventory",
            character_id=db_char.id,
        )
        session.add(inst)

    for slot, obj in char.equipment.items():
        inst = DBObjectInstance(
            prototype_vnum=obj.prototype.vnum,
            location=f"equipment:{slot}",
            character_id=db_char.id,
        )
        session.add(inst)
