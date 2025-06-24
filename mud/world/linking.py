from __future__ import annotations
import logging
from mud.registry import room_registry
from mud.models.constants import Direction


def link_exits() -> None:
    """Replace exit vnum references with actual Room objects."""
    for room in room_registry.values():
        for idx, exit in enumerate(room.exits):
            if exit is None:
                continue
            if exit.to_room is not None:
                continue
            target = room_registry.get(exit.vnum)
            if target:
                exit.to_room = target
            else:
                logging.warning(
                    "Unlinked exit in room %s -> %s (target %s not found)",
                    room.vnum,
                    Direction(idx).name.lower(),
                    exit.vnum,
                )
                if not hasattr(room, "unlinked_exits"):
                    room.unlinked_exits = set()
                room.unlinked_exits.add(Direction(idx))
