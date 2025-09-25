from __future__ import annotations

import logging

from mud.models.constants import Direction
from mud.registry import room_registry


def link_exits() -> None:
    """Replace exit vnum references with actual Room objects."""
    for room in room_registry.values():
        for idx, exit in enumerate(room.exits):
            if exit is None:
                continue
            if exit.to_room is not None:
                continue
            if exit.vnum <= 0:
                # Negative or zero vnums denote an intentionally unset exit.
                # These should be ignored rather than reported as errors.
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
