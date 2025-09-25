from __future__ import annotations

from mud.models.object import Object
from mud.registry import obj_registry


def spawn_object(vnum: int) -> Object | None:
    proto = obj_registry.get(vnum)
    if not proto:
        return None
    inst = Object(instance_id=None, prototype=proto)
    # Copy prototype values for runtime mutation compatibility
    try:
        inst.value = list(getattr(proto, "value", [0, 0, 0, 0, 0]))
    except Exception:
        inst.value = [0, 0, 0, 0, 0]
    if hasattr(proto, "count"):
        try:
            proto.count = int(getattr(proto, "count", 0)) + 1
        except Exception:
            proto.count = 1
    return inst
