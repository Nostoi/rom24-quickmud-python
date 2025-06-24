from __future__ import annotations
from typing import Optional

from mud.registry import mob_registry
from .templates import MobInstance


def spawn_mob(vnum: int) -> Optional[MobInstance]:
    proto = mob_registry.get(vnum)
    if not proto:
        return None
    mob = MobInstance.from_prototype(proto)
    return mob
