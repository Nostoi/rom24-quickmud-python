"""Global registries mirroring ROM's prototype lookup tables."""

from __future__ import annotations

from typing import Any

room_registry: dict[int, Any] = {}
mob_registry: dict[int, Any] = {}
obj_registry: dict[int, Any] = {}
area_registry: dict[int, Any] = {}
shop_registry: dict[int, Any] = {}

# Mirrors ROM's static `int max_on` in src/act_info.c do_count — the high-water
# mark of players online "today". Stamped by do_count; reset on a new game day.
max_on_today: int = 0
