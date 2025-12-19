"""Online Creation (OLC) system for QuickMUD.

This module provides area/room/mob/object editing and persistence.
Mirroring ROM src/olc_save.c save functionality.
"""

from __future__ import annotations

from .save import save_area_list, save_area_to_json

__all__ = ["save_area_list", "save_area_to_json"]
