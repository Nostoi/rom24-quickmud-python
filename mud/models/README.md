# Python Data Models for QuickMUD

This package provides JSON-schema-aligned dataclasses for rooms, objects, characters, and areas
alongside a few runtime helpers. These classes replace the early `merc.h` clones used during the
initial porting experiments.

## Overview

- `constants.py` defines enums for directions, sector types, character positions,
  wear locations and object item types.
- `room_json.py`, `object_json.py`, `character_json.py`, `area_json.py`,
  `player_json.py`, `skill_json.py`, `shop_json.py`, `help_json.py`, and
  `social_json.py` contain the schema dataclasses used for serialized game data.
- All schema dataclasses subclass `JsonDataclass` providing `to_dict` and
  `from_dict` helpers for round-trip serialization.
- `json_io.py` offers generic helpers for loading and dumping these dataclasses to and from JSON.
- Runtime dataclasses `shop.py`, `skill.py`, `help.py`, and `social.py`
  mirror their schema counterparts for use inside the game engine.

Legacy `area.py`, `room.py`, `mob.py`, and `obj.py` structures have been superseded and should not
be used in new code.
