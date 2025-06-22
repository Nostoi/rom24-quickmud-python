from enum import IntEnum

class Direction(IntEnum):
    """Mapping of direction constants from merc.h"""
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3
    UP = 4
    DOWN = 5

class Sector(IntEnum):
    """Sector types from merc.h"""
    INSIDE = 0
    CITY = 1
    FIELD = 2
    FOREST = 3
    HILLS = 4
    MOUNTAIN = 5
    WATER_SWIM = 6
    WATER_NOSWIM = 7
    UNUSED = 8
    AIR = 9
    DESERT = 10
    MAX = 11

class Position(IntEnum):
    """Character positions from merc.h"""
    DEAD = 0
    MORTAL = 1
    INCAP = 2
    STUNNED = 3
    SLEEPING = 4
    RESTING = 5
    SITTING = 6
    FIGHTING = 7
    STANDING = 8

class WearLocation(IntEnum):
    """Equipment wear locations from merc.h"""
    NONE = -1
    LIGHT = 0
    FINGER_L = 1
    FINGER_R = 2
    NECK_1 = 3
    NECK_2 = 4
    BODY = 5
    HEAD = 6
    LEGS = 7
    FEET = 8
    HANDS = 9
    ARMS = 10
    SHIELD = 11
    ABOUT = 12
    WAIST = 13
    WRIST_L = 14
    WRIST_R = 15
    WIELD = 16
    HOLD = 17
    FLOAT = 18
