from __future__ import annotations

from mud.models.constants import ExtraFlag, WearLocation, convert_flags_from_letters
from mud.models.object import Object
from mud.models.obj import Affect
from mud.registry import obj_registry


def _clone_affect(affect: Affect | dict) -> Affect:
    if isinstance(affect, Affect):
        return Affect(
            where=int(getattr(affect, "where", 1)),
            type=int(getattr(affect, "type", -1)),
            level=int(getattr(affect, "level", 0)),
            duration=int(getattr(affect, "duration", 0)),
            location=int(getattr(affect, "location", 0)),
            modifier=int(getattr(affect, "modifier", 0)),
            bitvector=int(getattr(affect, "bitvector", 0)),
        )
    return Affect(
        where=int(affect.get("where", 1)),
        type=int(affect.get("type", -1)),
        level=int(affect.get("level", 0)),
        duration=int(affect.get("duration", 0)),
        location=int(affect.get("location", 0)),
        modifier=int(affect.get("modifier", 0)),
        bitvector=int(affect.get("bitvector", 0)),
    )


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
    inst.level = int(getattr(proto, "level", 0) or 0)
    inst.cost = int(getattr(proto, "cost", 0) or 0)
    extra_flags = getattr(proto, "extra_flags", 0)
    if isinstance(extra_flags, str):
        try:
            inst.extra_flags = int(convert_flags_from_letters(extra_flags, ExtraFlag))
        except Exception:
            inst.extra_flags = 0
    else:
        try:
            inst.extra_flags = int(extra_flags)
        except (TypeError, ValueError):
            inst.extra_flags = 0
    wear_flags = getattr(proto, "wear_flags", 0)
    try:
        inst.wear_flags = int(wear_flags)
    except (TypeError, ValueError):
        inst.wear_flags = 0
    condition = getattr(proto, "condition", 0)
    try:
        inst.condition = int(condition)
    except (TypeError, ValueError):
        inst.condition = condition or 0
    inst.item_type = getattr(proto, "item_type", None)
    proto_affects = list(getattr(proto, "affected", []) or [])
    inst.affected = [_clone_affect(affect) for affect in proto_affects]
    inst.wear_loc = int(WearLocation.NONE)
    if hasattr(proto, "count"):
        try:
            proto.count = int(getattr(proto, "count", 0)) + 1
        except Exception:
            proto.count = 1
    return inst
