# Python Data Models for QuickMUD

This module contains Python dataclasses mirroring the most common C structs found in QuickMUD.
It allows tools to interact with game data using a native Python representation without relying on
pointers or memory management.

## Overview

- `constants.py` defines enums for directions, sector types, character positions and wear locations.
- `area.py` provides the `Area` dataclass, corresponding to `AREA_DATA`.
- `room.py` defines `Room` along with helper classes such as `ExtraDescr`, `Exit` and `Reset`.
- `mob.py` contains `MobIndex` and `MobProgram` representing NPC templates and mobile programs.
- `obj.py` implements `ObjIndex`, `ObjectData`, and `Affect` to model items.
- `character.py` holds the `Character` dataclass and related `PCData` information.

Each dataclass includes default values and typing hints that closely follow the original structure
from `merc.h` while adopting Python conventions.
