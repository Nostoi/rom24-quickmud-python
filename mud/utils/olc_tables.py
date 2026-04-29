"""OLC lookup tables ported from ROM src/tables.c.

Used by display_resets (OLC-020) and do_resets (OLC-022).

ROM Reference: src/tables.c:355-572
"""

from __future__ import annotations

from mud.models.constants import WearLocation

# ---------------------------------------------------------------------------
# wear_loc_strings — maps WearLocation integer value → display phrase
# ROM src/tables.c:525-547
# ---------------------------------------------------------------------------

WEAR_LOC_STRINGS: dict[int, str] = {
    int(WearLocation.NONE): "in the inventory",
    int(WearLocation.LIGHT): "as a light",
    int(WearLocation.FINGER_L): "on the left finger",
    int(WearLocation.FINGER_R): "on the right finger",
    int(WearLocation.NECK_1): "around the neck (1)",
    int(WearLocation.NECK_2): "around the neck (2)",
    int(WearLocation.BODY): "on the body",
    int(WearLocation.HEAD): "over the head",
    int(WearLocation.LEGS): "on the legs",
    int(WearLocation.FEET): "on the feet",
    int(WearLocation.HANDS): "on the hands",
    int(WearLocation.ARMS): "on the arms",
    int(WearLocation.SHIELD): "as a shield",
    int(WearLocation.ABOUT): "about the shoulders",
    int(WearLocation.WAIST): "around the waist",
    int(WearLocation.WRIST_L): "on the left wrist",
    int(WearLocation.WRIST_R): "on the right wrist",
    int(WearLocation.WIELD): "wielded",
    int(WearLocation.HOLD): "held in the hands",
    int(WearLocation.FLOAT): "floating nearby",
}

# ---------------------------------------------------------------------------
# wear_loc_flags — maps name → WearLocation integer value (for flag_value)
# ROM src/tables.c:550-572
# ---------------------------------------------------------------------------

WEAR_LOC_FLAGS: dict[str, int] = {
    "none": int(WearLocation.NONE),
    "light": int(WearLocation.LIGHT),
    "lfinger": int(WearLocation.FINGER_L),
    "rfinger": int(WearLocation.FINGER_R),
    "neck1": int(WearLocation.NECK_1),
    "neck2": int(WearLocation.NECK_2),
    "body": int(WearLocation.BODY),
    "head": int(WearLocation.HEAD),
    "legs": int(WearLocation.LEGS),
    "feet": int(WearLocation.FEET),
    "hands": int(WearLocation.HANDS),
    "arms": int(WearLocation.ARMS),
    "shield": int(WearLocation.SHIELD),
    "about": int(WearLocation.ABOUT),
    "waist": int(WearLocation.WAIST),
    "lwrist": int(WearLocation.WRIST_L),
    "rwrist": int(WearLocation.WRIST_R),
    "wielded": int(WearLocation.WIELD),
    "hold": int(WearLocation.HOLD),
    "floating": int(WearLocation.FLOAT),
}

# ---------------------------------------------------------------------------
# door_resets — maps door state integer → display phrase
# ROM src/tables.c:355-360
# ---------------------------------------------------------------------------

DOOR_RESETS: dict[int, str] = {
    0: "open and unlocked",
    1: "closed and unlocked",
    2: "closed and locked",
}

# ---------------------------------------------------------------------------
# dir_name — direction names in ROM order (mirroring ROM src/const.c dir_name[])
# ROM Direction enum: NORTH=0, EAST=1, SOUTH=2, WEST=3, UP=4, DOWN=5
# ---------------------------------------------------------------------------

DIR_NAMES: list[str] = ["north", "east", "south", "west", "up", "down"]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def wear_loc_string_for(value: int) -> str:
    """Return the wear-loc display phrase for a WearLocation integer value.

    Mirrors ROM flag_string(wear_loc_strings, bits) for single-value (stat)
    lookups — returns "none" on miss, matching ROM's NO_FLAG sentinel path.

    ROM Reference: src/tables.c:525-547, src/bit.c flag_string
    """
    return WEAR_LOC_STRINGS.get(value, "none")


def wear_loc_flag_lookup(name: str) -> int | None:
    """Prefix-lookup of a wear-loc name in WEAR_LOC_FLAGS.

    Mirrors ROM flag_value(wear_loc_flags, argument) stat-table behavior:
    src/bit.c:118-119 — iterates table entries, returns value of first entry
    whose name starts with ``name`` (str_prefix match).  Returns None on miss
    (ROM returns NO_FLAG = -1, Python convention is None).

    ROM Reference: src/bit.c:100-125
    """
    name_lower = name.lower()
    for key, val in WEAR_LOC_FLAGS.items():
        if key.startswith(name_lower):
            return val
    return None


def door_reset_string_for(value: int) -> str:
    """Return the door-reset display phrase for a door state integer.

    Mirrors ROM flag_string(door_resets, bits) — returns "none" on miss.

    ROM Reference: src/tables.c:355-360, src/bit.c flag_string
    """
    return DOOR_RESETS.get(value, "none")
