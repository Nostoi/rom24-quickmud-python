from __future__ import annotations

from mud.models.character import character_registry
from mud.registry import mob_registry

from .templates import MobInstance


def spawn_mob(vnum: int) -> MobInstance | None:
    """Create a MobInstance and add to character_registry.

    Mirroring ROM C src/db.c:create_mobile which prepends the new mob
    to the global char_list so violence_update can find it.
    """
    proto = mob_registry.get(vnum)
    if not proto:
        return None
    mob = MobInstance.from_prototype(proto)
    character_registry.append(mob)
    return mob
