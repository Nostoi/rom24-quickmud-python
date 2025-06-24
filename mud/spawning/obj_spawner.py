from __future__ import annotations
from typing import Optional

from mud.registry import obj_registry
from .templates import ObjectInstance


def spawn_object(vnum: int) -> Optional[ObjectInstance]:
    proto = obj_registry.get(vnum)
    if not proto:
        return None
    obj = ObjectInstance(
        name=proto.name,
        short_descr=proto.short_descr,
        item_type=proto.item_type,
        prototype=proto,
    )
    return obj
