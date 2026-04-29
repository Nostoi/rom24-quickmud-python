from enum import IntEnum, IntFlag
from typing import NamedTuple, TypeVar


F = TypeVar("F", bound=IntFlag)


class Direction(IntEnum):
    """Mapping of direction constants from merc.h"""

    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3
    UP = 4
    DOWN = 5


# Canonical room/object vnums (merc.h)
ROOM_VNUM_LIMBO = 2
ROOM_VNUM_TEMPLE = 3001
ROOM_VNUM_CHAT = 1200  # ROM src/merc.h:1250 — immortal default login room
ROOM_VNUM_ALTAR = 3054
ROOM_VNUM_SCHOOL = 3700

# Money objects (ROM C merc.h:1020-1024)
OBJ_VNUM_SILVER_ONE = 1
OBJ_VNUM_GOLD_ONE = 2
OBJ_VNUM_SILVER_SOME = 3
OBJ_VNUM_GOLD_SOME = 4
OBJ_VNUM_COINS = 5

# Utility conjuration targets
OBJ_VNUM_CORPSE_NPC = 10
OBJ_VNUM_CORPSE_PC = 11
OBJ_VNUM_SEVERED_HEAD = 12
OBJ_VNUM_TORN_HEART = 13
OBJ_VNUM_SLICED_ARM = 14
OBJ_VNUM_SLICED_LEG = 15
OBJ_VNUM_GUTS = 16
OBJ_VNUM_BRAINS = 17
OBJ_VNUM_MUSHROOM = 20
OBJ_VNUM_LIGHT_BALL = 21
OBJ_VNUM_SPRING = 22
OBJ_VNUM_DISC = 23
OBJ_VNUM_PORTAL = 25
OBJ_VNUM_ROSE = 1001

# School equipment (OBJ_VNUM_SCHOOL_*) used during character creation (merc.h)
OBJ_VNUM_SCHOOL_MACE = 3700
OBJ_VNUM_SCHOOL_DAGGER = 3701
OBJ_VNUM_SCHOOL_SWORD = 3702
OBJ_VNUM_SCHOOL_VEST = 3703
OBJ_VNUM_SCHOOL_SHIELD = 3704
OBJ_VNUM_SCHOOL_BANNER = 3716
OBJ_VNUM_SCHOOL_SPEAR = 3717
OBJ_VNUM_SCHOOL_STAFF = 3718
OBJ_VNUM_SCHOOL_AXE = 3719
OBJ_VNUM_SCHOOL_FLAIL = 3720
OBJ_VNUM_SCHOOL_WHIP = 3721
OBJ_VNUM_SCHOOL_POLEARM = 3722
# Midgaard resources handed to new players
OBJ_VNUM_MAP = 3162
# Justice system utility items (merc.h)
OBJ_VNUM_WHISTLE = 2116

# Clan rival group vnums and patrol utilities (merc.h)
GROUP_VNUM_TROLLS = 2100
GROUP_VNUM_OGRES = 2101
MOB_VNUM_PATROLMAN = 2106

# Donation pit (merc.h:1043)
OBJ_VNUM_PIT = 3010

# Command/append-file limits (merc.h)
MAX_CMD_LEN = 50
OHELPS_FILE = "orphaned_helps.txt"

# Telnet pagination defaults (merc.h PAGELEN)
DEFAULT_PAGE_LINES = 22


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


class Condition(IntEnum):
    """Character condition slots (COND_* indexes in merc.h)."""

    DRUNK = 0
    FULL = 1
    THIRST = 2
    HUNGER = 3


class Stat(IntEnum):
    """Primary character statistics (STAT_* indexes in merc.h)."""

    STR = 0
    INT = 1
    WIS = 2
    DEX = 3
    CON = 4


# --- Armor Class indices (merc.h) ---
# AC is better when more negative; indices map to damage types.
AC_PIERCE = 0
AC_BASH = 1
AC_SLASH = 2
AC_EXOTIC = 3


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


class WearFlag(IntFlag):
    """Object wear flags mirroring ROM ITEM_* bitmasks."""

    TAKE = 1 << 0
    WEAR_FINGER = 1 << 1
    WEAR_NECK = 1 << 2
    WEAR_BODY = 1 << 3
    WEAR_HEAD = 1 << 4
    WEAR_LEGS = 1 << 5
    WEAR_FEET = 1 << 6
    WEAR_HANDS = 1 << 7
    WEAR_ARMS = 1 << 8
    WEAR_SHIELD = 1 << 9
    WEAR_ABOUT = 1 << 10
    WEAR_WAIST = 1 << 11
    WEAR_WRIST = 1 << 12
    WIELD = 1 << 13
    HOLD = 1 << 14
    NO_SAC = 1 << 15
    WEAR_FLOAT = 1 << 16


class Sex(IntEnum):
    """Biological sex of a character"""

    NONE = 0
    MALE = 1
    FEMALE = 2
    EITHER = 3


class WeaponType(IntEnum):
    """Weapon classes from merc.h WEAPON_* constants."""

    EXOTIC = 0
    SWORD = 1
    DAGGER = 2
    SPEAR = 3
    MACE = 4
    AXE = 5
    FLAIL = 6
    WHIP = 7
    POLEARM = 8


class Size(IntEnum):
    """Character sizes"""

    TINY = 0
    SMALL = 1
    MEDIUM = 2
    LARGE = 3
    HUGE = 4
    GIANT = 5


# --- Primary stats (merc.h STAT_*) ---
MAX_STATS = 5
STAT_STR = 0
STAT_INT = 1
STAT_WIS = 2
STAT_DEX = 3
STAT_CON = 4


# Intelligence learn-rate table (const.c:int_app)
INT_APP_LEARN = [
    3,
    5,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    15,
    17,
    19,
    22,
    25,
    28,
    31,
    34,
    37,
    40,
    44,
    49,
    55,
    60,
    70,
    80,
    85,
]


# Class practice caps pulled from const.c:class_table.skill_adept
CLASS_SKILL_ADEPT = {
    0: 75,  # mage
    1: 75,  # cleric
    2: 75,  # thief
    3: 75,  # warrior
}


# --- Level Constants (merc.h) ---
MAX_LEVEL = 60
LEVEL_HERO = MAX_LEVEL - 9  # 51
LEVEL_IMMORTAL = MAX_LEVEL - 8  # 52
LEVEL_ANGEL = MAX_LEVEL - 7  # 53

# Class guild entry rooms (ROM const.c: class_table)
CLASS_GUILD_ROOMS: dict[int, tuple[int, int]] = {
    0: (3018, 9618),  # mage
    1: (3003, 9619),  # cleric
    2: (3028, 9639),  # thief
    3: (3022, 9633),  # warrior
}


class ItemType(IntEnum):
    """Common object types"""

    LIGHT = 1
    SCROLL = 2
    WAND = 3
    STAFF = 4
    WEAPON = 5
    TREASURE = 8
    ARMOR = 9
    POTION = 10
    CLOTHING = 11
    FURNITURE = 12
    TRASH = 13
    CONTAINER = 15
    DRINK_CON = 17
    KEY = 18
    FOOD = 19
    MONEY = 20
    BOAT = 22
    CORPSE_NPC = 23
    CORPSE_PC = 24
    FOUNTAIN = 25
    PILL = 26
    PROTECT = 27
    MAP = 28
    PORTAL = 29
    WARP_STONE = 30
    ROOM_KEY = 31
    GEM = 32
    JEWELRY = 33
    JUKEBOX = 34


class ContainerFlag(IntFlag):
    """Container flags stored in value[1] for ITEM_CONTAINER."""

    CLOSEABLE = 1 << 0
    PICKPROOF = 1 << 1
    CLOSED = 1 << 2
    LOCKED = 1 << 3
    PUT_ON = 1 << 4


class FurnitureFlag(IntFlag):
    """Furniture flags stored in value[2] for ITEM_FURNITURE.

    ROM Reference: src/merc.h:1180-1196 (STAND_AT..PUT_INSIDE bits A..P)
    Capacity is value[0]; max weight is value[1]; heal/mana mods are value[3]/value[4].
    """

    STAND_AT = 1 << 0   # A
    STAND_ON = 1 << 1   # B
    STAND_IN = 1 << 2   # C
    SIT_AT = 1 << 3     # D
    SIT_ON = 1 << 4     # E
    SIT_IN = 1 << 5     # F
    REST_AT = 1 << 6    # G
    REST_ON = 1 << 7    # H
    REST_IN = 1 << 8    # I
    SLEEP_AT = 1 << 9   # J
    SLEEP_ON = 1 << 10  # K
    SLEEP_IN = 1 << 11  # L
    PUT_AT = 1 << 12    # M
    PUT_ON_FURN = 1 << 13   # N
    PUT_IN = 1 << 14    # O
    PUT_INSIDE = 1 << 15    # P


LIQ_WATER = 0


class Liquid(NamedTuple):
    """Entry from ROM's ``liq_table`` containing name, color, and affect values.

    ROM Reference: src/const.c liq_table (lines 886-931)
    liq_affect[0] = proof/drunk, [1] = full, [2] = thirst, [3] = food/hunger, [4] = ssize
    """

    name: str
    color: str
    proof: int   # liq_affect[0] — drunk gain per unit
    full: int    # liq_affect[1] — full gain per unit
    thirst: int  # liq_affect[2] — thirst gain per unit
    food: int    # liq_affect[3] — hunger gain per unit
    ssize: int   # liq_affect[4] — serving size (units per sip)


LIQUID_TABLE: tuple[Liquid, ...] = (
    # name,                color,           proof, full, thirst, food, ssize
    Liquid("water",              "clear",        0,   1,  10,  0, 16),
    Liquid("beer",               "amber",       12,   1,   8,  1, 12),
    Liquid("red wine",           "burgundy",    30,   1,   8,  1,  5),
    Liquid("ale",                "brown",       15,   1,   8,  1, 12),
    Liquid("dark ale",           "dark",        16,   1,   8,  1, 12),
    Liquid("whisky",             "golden",     120,   1,   5,  0,  2),
    Liquid("lemonade",           "pink",         0,   1,   9,  2, 12),
    Liquid("firebreather",       "boiling",    190,   0,   4,  0,  2),
    Liquid("local specialty",    "clear",      151,   1,   3,  0,  2),
    Liquid("slime mold juice",   "green",        0,   2,  -8,  1,  2),
    Liquid("milk",               "white",        0,   2,   9,  3, 12),
    Liquid("tea",                "tan",          0,   1,   8,  0,  6),
    Liquid("coffee",             "black",        0,   1,   8,  0,  6),
    Liquid("blood",              "red",          0,   2,  -1,  2,  6),
    Liquid("salt water",         "clear",        0,   1,  -2,  0,  1),
    Liquid("coke",               "brown",        0,   2,   9,  2, 12),
    Liquid("root beer",          "brown",        0,   2,   9,  2, 12),
    Liquid("elvish wine",        "green",       35,   2,   8,  1,  5),
    Liquid("white wine",         "golden",      28,   1,   8,  1,  5),
    Liquid("champagne",          "golden",      32,   1,   8,  1,  5),
    Liquid("mead",               "honey-colored", 34, 2,   8,  2, 12),
    Liquid("rose wine",          "pink",        26,   1,   8,  1,  5),
    Liquid("benedictine wine",   "burgundy",    40,   1,   8,  1,  5),
    Liquid("vodka",              "clear",      130,   1,   5,  0,  2),
    Liquid("cranberry juice",    "red",          0,   1,   9,  2, 12),
    Liquid("orange juice",       "orange",       0,   2,   9,  3, 12),
    Liquid("absinthe",           "green",      200,   1,   4,  0,  2),
    Liquid("brandy",             "golden",      80,   1,   5,  0,  4),
    Liquid("aquavit",            "clear",      140,   1,   5,  0,  2),
    Liquid("schnapps",           "clear",       90,   1,   5,  0,  2),
    Liquid("icewine",            "purple",      50,   2,   6,  1,  5),
    Liquid("amontillado",        "burgundy",    35,   2,   8,  1,  5),
    Liquid("sherry",             "red",         38,   2,   7,  1,  5),
    Liquid("framboise",          "red",         50,   1,   7,  1,  5),
    Liquid("rum",                "amber",      151,   1,   4,  0,  2),
    Liquid("cordial",            "clear",      100,   1,   5,  0,  2),
)


class ActFlag(IntFlag):
    """NPC act flags from ROM merc.h (letters A..Z, aa..dd)."""

    IS_NPC = 1 << 0  # (A)
    SENTINEL = 1 << 1  # (B)
    SCAVENGER = 1 << 2  # (C)
    AGGRESSIVE = 1 << 5  # (F)
    STAY_AREA = 1 << 6  # (G)
    WIMPY = 1 << 7  # (H)
    PET = 1 << 8  # (I)
    TRAIN = 1 << 9  # (J)
    PRACTICE = 1 << 10  # (K)
    UNDEAD = 1 << 14  # (O)
    CLERIC = 1 << 16  # (Q)
    MAGE = 1 << 17  # (R)
    THIEF = 1 << 18  # (S)
    WARRIOR = 1 << 19  # (T)
    NOALIGN = 1 << 20  # (U)
    NOPURGE = 1 << 21  # (V)
    OUTDOORS = 1 << 22  # (W)
    INDOORS = 1 << 24  # (Y)
    IS_HEALER = 1 << 26  # (aa)
    GAIN = 1 << 27  # (bb)
    UPDATE_ALWAYS = 1 << 28  # (cc)
    IS_CHANGER = 1 << 29  # (dd)


class PlayerFlag(IntFlag):
    """Player-specific act flags (merc.h PLR_* bitmasks)."""

    IS_NPC = 1 << 0  # (A)
    AUTOASSIST = 1 << 2  # (C)
    AUTOEXIT = 1 << 3  # (D)
    AUTOLOOT = 1 << 4  # (E)
    AUTOSAC = 1 << 5  # (F)
    AUTOGOLD = 1 << 6  # (G)
    AUTOSPLIT = 1 << 7  # (H)
    HOLYLIGHT = 1 << 13  # (N)
    CANLOOT = 1 << 15  # (P)
    NOSUMMON = 1 << 16  # (Q)
    NOFOLLOW = 1 << 17  # (R)
    COLOUR = 1 << 19  # (T)
    PERMIT = 1 << 20  # (U)
    LOG = 1 << 22  # (W)
    DENY = 1 << 23  # (X)
    FREEZE = 1 << 24  # (Y)
    THIEF = 1 << 25  # (Z)
    KILLER = 1 << 26  # (aa)


class CommFlag(IntFlag):
    """Communication toggles (merc.h COMM_* defines)."""

    QUIET = 1 << 0  # (A)
    DEAF = 1 << 1  # (B)
    NOWIZ = 1 << 2  # (C)
    NOAUCTION = 1 << 3  # (D)
    NOGOSSIP = 1 << 4  # (E)
    NOQUESTION = 1 << 5  # (F)
    NOMUSIC = 1 << 6  # (G)
    NOCLAN = 1 << 7  # (H)
    NOQUOTE = 1 << 8  # (I)
    SHOUTSOFF = 1 << 9  # (J)
    COMPACT = 1 << 11  # (L)
    BRIEF = 1 << 12  # (M)
    PROMPT = 1 << 13  # (N)
    COMBINE = 1 << 14  # (O)
    TELNET_GA = 1 << 15  # (P)
    SHOW_AFFECTS = 1 << 16  # (Q)
    NOGRATS = 1 << 17  # (R)
    NOEMOTE = 1 << 19  # (T)
    NOSHOUT = 1 << 20  # (U)
    NOTELL = 1 << 21  # (V)
    NOCHANNELS = 1 << 22  # (W)
    SNOOP_PROOF = 1 << 24  # (Y)
    AFK = 1 << 25  # (Z)


class OffFlag(IntFlag):
    """Mobile offensive flags from ROM merc.h OFF_* defines."""

    AREA_ATTACK = 1 << 0  # (A)
    BACKSTAB = 1 << 1  # (B)
    BASH = 1 << 2  # (C)
    BERSERK = 1 << 3  # (D)
    DISARM = 1 << 4  # (E)
    DODGE = 1 << 5  # (F)
    FADE = 1 << 6  # (G)
    FAST = 1 << 7  # (H)
    KICK = 1 << 8  # (I)
    KICK_DIRT = 1 << 9  # (J)
    PARRY = 1 << 10  # (K)
    RESCUE = 1 << 11  # (L)
    TAIL = 1 << 12  # (M)
    TRIP = 1 << 13  # (N)
    CRUSH = 1 << 14  # (O)
    ASSIST_ALL = 1 << 15  # (P)
    ASSIST_ALIGN = 1 << 16  # (Q)
    ASSIST_RACE = 1 << 17  # (R)
    ASSIST_PLAYERS = 1 << 18  # (S)
    ASSIST_GUARD = 1 << 19  # (T)
    ASSIST_VNUM = 1 << 20  # (U)


class AreaFlag(IntFlag):
    """Area flags from ROM merc.h AREA_* defines."""

    NONE = 0
    CHANGED = 1 << 0  # AREA_CHANGED
    ADDED = 1 << 1  # AREA_ADDED
    LOADING = 1 << 2  # AREA_LOADING


class RoomFlag(IntFlag):
    """Room flags from ROM merc.h ROOM_* defines"""

    ROOM_DARK = 1  # (A)
    ROOM_NO_MOB = 4  # (C)
    ROOM_INDOORS = 8  # (D)
    ROOM_PRIVATE = 512  # (J)
    ROOM_SAFE = 1024  # (K)
    ROOM_SOLITARY = 2048  # (L)
    ROOM_PET_SHOP = 4096  # (M)
    ROOM_NO_RECALL = 8192  # (N)
    ROOM_IMP_ONLY = 16384  # (O)
    ROOM_GODS_ONLY = 32768  # (P)
    ROOM_HEROES_ONLY = 65536  # (Q)
    ROOM_NEWBIES_ONLY = 131072  # (R)
    ROOM_LAW = 262144  # (S)
    ROOM_NOWHERE = 524288  # (T)


# START affects_saves
class AffectFlag(IntFlag):
    # ROM merc.h:953-982 — letter macros A..dd map to bits 0..29.
    # TABLES-001: bit positions match ROM exactly so letter-form area data
    # decoded via convert_flags_from_letters agrees with these enum members.
    BLIND = 1 << 0  # (A)
    INVISIBLE = 1 << 1  # (B)
    DETECT_EVIL = 1 << 2  # (C)
    DETECT_INVIS = 1 << 3  # (D)
    DETECT_MAGIC = 1 << 4  # (E)
    DETECT_HIDDEN = 1 << 5  # (F)
    DETECT_GOOD = 1 << 6  # (G)
    SANCTUARY = 1 << 7  # (H)
    FAERIE_FIRE = 1 << 8  # (I)
    INFRARED = 1 << 9  # (J)
    CURSE = 1 << 10  # (K)
    # bit 11 (L) is AFF_UNUSED_FLAG in ROM; reserved.
    POISON = 1 << 12  # (M)
    PROTECT_EVIL = 1 << 13  # (N)
    PROTECT_GOOD = 1 << 14  # (O)
    SNEAK = 1 << 15  # (P)
    HIDE = 1 << 16  # (Q)
    SLEEP = 1 << 17  # (R)
    CHARM = 1 << 18  # (S)
    FLYING = 1 << 19  # (T)
    PASS_DOOR = 1 << 20  # (U)
    HASTE = 1 << 21  # (V)
    CALM = 1 << 22  # (W)
    PLAGUE = 1 << 23  # (X)
    WEAKEN = 1 << 24  # (Y)
    DARK_VISION = 1 << 25  # (Z)
    BERSERK = 1 << 26  # (aa)
    SWIM = 1 << 27  # (bb)
    REGENERATION = 1 << 28  # (cc)
    SLOW = 1 << 29  # (dd)
    UNUSED5 = 1 << 30
    UNUSED6 = 1 << 31


# END affects_saves


# START damage_types_and_defense_bits
class DamageType(IntEnum):
    """Damage types mirroring merc.h DAM_* values."""

    NONE = 0
    BASH = 1
    PIERCE = 2
    SLASH = 3
    FIRE = 4
    COLD = 5
    LIGHTNING = 6
    ACID = 7
    POISON = 8
    NEGATIVE = 9
    HOLY = 10
    ENERGY = 11
    MENTAL = 12
    DISEASE = 13
    DROWNING = 14
    LIGHT = 15
    OTHER = 16
    HARM = 17
    CHARM = 18
    SOUND = 19


# ROM-style DAM_* constants for parity
DAM_NONE = DamageType.NONE
DAM_BASH = DamageType.BASH
DAM_PIERCE = DamageType.PIERCE
DAM_SLASH = DamageType.SLASH
DAM_FIRE = DamageType.FIRE
DAM_COLD = DamageType.COLD
DAM_LIGHTNING = DamageType.LIGHTNING
DAM_ACID = DamageType.ACID
DAM_POISON = DamageType.POISON
DAM_NEGATIVE = DamageType.NEGATIVE
DAM_HOLY = DamageType.HOLY
DAM_ENERGY = DamageType.ENERGY
DAM_MENTAL = DamageType.MENTAL
DAM_DISEASE = DamageType.DISEASE
DAM_DROWNING = DamageType.DROWNING
DAM_LIGHT = DamageType.LIGHT
DAM_OTHER = DamageType.OTHER
DAM_HARM = DamageType.HARM
DAM_CHARM = DamageType.CHARM
DAM_SOUND = DamageType.SOUND


class AttackType(NamedTuple):
    """Entry from ROM's attack_table (src/const.c)."""

    name: str | None
    noun: str | None
    damage: int


ATTACK_TABLE: tuple[AttackType, ...] = (
    AttackType("none", "hit", -1),
    AttackType("slice", "slice", int(DamageType.SLASH)),
    AttackType("stab", "stab", int(DamageType.PIERCE)),
    AttackType("slash", "slash", int(DamageType.SLASH)),
    AttackType("whip", "whip", int(DamageType.SLASH)),
    AttackType("claw", "claw", int(DamageType.SLASH)),
    AttackType("blast", "blast", int(DamageType.BASH)),
    AttackType("pound", "pound", int(DamageType.BASH)),
    AttackType("crush", "crush", int(DamageType.BASH)),
    AttackType("grep", "grep", int(DamageType.SLASH)),
    AttackType("bite", "bite", int(DamageType.PIERCE)),
    AttackType("pierce", "pierce", int(DamageType.PIERCE)),
    AttackType("suction", "suction", int(DamageType.BASH)),
    AttackType("beating", "beating", int(DamageType.BASH)),
    AttackType("digestion", "digestion", int(DamageType.ACID)),
    AttackType("charge", "charge", int(DamageType.BASH)),
    AttackType("slap", "slap", int(DamageType.BASH)),
    AttackType("punch", "punch", int(DamageType.BASH)),
    AttackType("wrath", "wrath", int(DamageType.ENERGY)),
    AttackType("magic", "magic", int(DamageType.ENERGY)),
    AttackType("divine", "divine power", int(DamageType.HOLY)),
    AttackType("cleave", "cleave", int(DamageType.SLASH)),
    AttackType("scratch", "scratch", int(DamageType.PIERCE)),
    AttackType("peck", "peck", int(DamageType.PIERCE)),
    AttackType("peckb", "peck", int(DamageType.BASH)),
    AttackType("chop", "chop", int(DamageType.SLASH)),
    AttackType("sting", "sting", int(DamageType.PIERCE)),
    AttackType("smash", "smash", int(DamageType.BASH)),
    AttackType("shbite", "shocking bite", int(DamageType.LIGHTNING)),
    AttackType("flbite", "flaming bite", int(DamageType.FIRE)),
    AttackType("frbite", "freezing bite", int(DamageType.COLD)),
    AttackType("acbite", "acidic bite", int(DamageType.ACID)),
    AttackType("chomp", "chomp", int(DamageType.PIERCE)),
    AttackType("drain", "life drain", int(DamageType.NEGATIVE)),
    AttackType("thrust", "thrust", int(DamageType.PIERCE)),
    AttackType("slime", "slime", int(DamageType.ACID)),
    AttackType("shock", "shock", int(DamageType.LIGHTNING)),
    AttackType("thwack", "thwack", int(DamageType.BASH)),
    AttackType("flame", "flame", int(DamageType.FIRE)),
    AttackType("chill", "chill", int(DamageType.COLD)),
    AttackType(None, None, int(DamageType.BASH)),
)


def attack_lookup(name: str) -> int:
    """Case-insensitive prefix lookup mirroring ROM attack_lookup."""

    if not name:
        return 0
    lowered = name.strip().lower()
    if not lowered:
        return 0
    for idx, attack in enumerate(ATTACK_TABLE):
        attack_name = attack.name
        if attack_name is None:
            break
        if lowered[0] == attack_name[0] and attack_name.startswith(lowered):
            return idx
    return 0


def attack_damage_type(index: int) -> DamageType | None:
    """Return the DamageType associated with an attack_table index."""

    if not isinstance(index, int) or index < 0:
        return None
    try:
        entry = ATTACK_TABLE[index]
    except IndexError:
        return None
    damage = entry.damage
    if damage == -1:
        return DamageType.BASH
    try:
        return DamageType(damage)
    except ValueError:
        return None


class WeaponFlag(IntFlag):
    """Weapon special properties mirroring merc.h WEAPON_* values.

    These correspond to ROM weapon flags:
    A = FLAMING, B = FROST, C = VAMPIRIC, D = SHARP, E = VORPAL,
    F = TWO_HANDS, G = SHOCKING, H = POISON
    """

    FLAMING = 1 << 0  # (A) - fire damage
    FROST = 1 << 1  # (B) - cold damage
    VAMPIRIC = 1 << 2  # (C) - life drain
    SHARP = 1 << 3  # (D) - critical hits
    VORPAL = 1 << 4  # (E) - prevents envenoming (no combat effect in ROM 2.4b6)
    TWO_HANDS = 1 << 5  # (F) - two-handed weapon
    SHOCKING = 1 << 6  # (G) - lightning damage
    POISON = 1 << 7  # (H) - poison effects


# ROM-style WEAPON_* constants for parity
WEAPON_FLAMING = WeaponFlag.FLAMING
WEAPON_FROST = WeaponFlag.FROST
WEAPON_VAMPIRIC = WeaponFlag.VAMPIRIC
WEAPON_SHARP = WeaponFlag.SHARP
WEAPON_VORPAL = WeaponFlag.VORPAL
WEAPON_TWO_HANDS = WeaponFlag.TWO_HANDS
WEAPON_SHOCKING = WeaponFlag.SHOCKING
WEAPON_POISON = WeaponFlag.POISON


class DefenseBit(IntFlag):
    """IMM/RES/VULN bit positions (letters A..Z) mapped to explicit bits.

    These names are shared across IMM_*, RES_*, VULN_* in ROM.
    """

    # A..Z → 1<<0 .. 1<<25 (skip U/V/W per merc.h usage here)
    SUMMON = 1 << 0  # A
    CHARM = 1 << 1  # B
    MAGIC = 1 << 2  # C
    WEAPON = 1 << 3  # D
    BASH = 1 << 4  # E
    PIERCE = 1 << 5  # F
    SLASH = 1 << 6  # G
    FIRE = 1 << 7  # H
    COLD = 1 << 8  # I
    LIGHTNING = 1 << 9  # J
    ACID = 1 << 10  # K
    POISON = 1 << 11  # L
    NEGATIVE = 1 << 12  # M
    HOLY = 1 << 13  # N
    ENERGY = 1 << 14  # O
    MENTAL = 1 << 15  # P
    DISEASE = 1 << 16  # Q
    DROWNING = 1 << 17  # R
    LIGHT = 1 << 18  # S
    SOUND = 1 << 19  # T
    # U, V, W unused for these tables in ROM
    WOOD = 1 << 23  # X
    SILVER = 1 << 24  # Y
    IRON = 1 << 25  # Z


# END damage_types_and_defense_bits


# START imm_res_vuln_flags
class ImmFlag(IntFlag):
    """IMM_* flags mapped to ROM bit letters (A..Z).

    Values mirror DefenseBit so code may interchangeably use either.
    """

    SUMMON = int(DefenseBit.SUMMON)
    CHARM = int(DefenseBit.CHARM)
    MAGIC = int(DefenseBit.MAGIC)
    WEAPON = int(DefenseBit.WEAPON)
    BASH = int(DefenseBit.BASH)
    PIERCE = int(DefenseBit.PIERCE)
    SLASH = int(DefenseBit.SLASH)
    FIRE = int(DefenseBit.FIRE)
    COLD = int(DefenseBit.COLD)
    LIGHTNING = int(DefenseBit.LIGHTNING)
    ACID = int(DefenseBit.ACID)
    POISON = int(DefenseBit.POISON)
    NEGATIVE = int(DefenseBit.NEGATIVE)
    HOLY = int(DefenseBit.HOLY)
    ENERGY = int(DefenseBit.ENERGY)
    MENTAL = int(DefenseBit.MENTAL)
    DISEASE = int(DefenseBit.DISEASE)
    DROWNING = int(DefenseBit.DROWNING)
    LIGHT = int(DefenseBit.LIGHT)
    SOUND = int(DefenseBit.SOUND)
    WOOD = int(DefenseBit.WOOD)
    SILVER = int(DefenseBit.SILVER)
    IRON = int(DefenseBit.IRON)


class ResFlag(IntFlag):
    """RES_* flags mapped to ROM bit letters (A..Z)."""

    SUMMON = int(DefenseBit.SUMMON)
    CHARM = int(DefenseBit.CHARM)
    MAGIC = int(DefenseBit.MAGIC)
    WEAPON = int(DefenseBit.WEAPON)
    BASH = int(DefenseBit.BASH)
    PIERCE = int(DefenseBit.PIERCE)
    SLASH = int(DefenseBit.SLASH)
    FIRE = int(DefenseBit.FIRE)
    COLD = int(DefenseBit.COLD)
    LIGHTNING = int(DefenseBit.LIGHTNING)
    ACID = int(DefenseBit.ACID)
    POISON = int(DefenseBit.POISON)
    NEGATIVE = int(DefenseBit.NEGATIVE)
    HOLY = int(DefenseBit.HOLY)
    ENERGY = int(DefenseBit.ENERGY)
    MENTAL = int(DefenseBit.MENTAL)
    DISEASE = int(DefenseBit.DISEASE)
    DROWNING = int(DefenseBit.DROWNING)
    LIGHT = int(DefenseBit.LIGHT)
    SOUND = int(DefenseBit.SOUND)
    WOOD = int(DefenseBit.WOOD)
    SILVER = int(DefenseBit.SILVER)
    IRON = int(DefenseBit.IRON)


class VulnFlag(IntFlag):
    """VULN_* flags mapped to ROM bit letters (A..Z)."""

    SUMMON = int(DefenseBit.SUMMON)
    CHARM = int(DefenseBit.CHARM)
    MAGIC = int(DefenseBit.MAGIC)
    WEAPON = int(DefenseBit.WEAPON)
    BASH = int(DefenseBit.BASH)
    PIERCE = int(DefenseBit.PIERCE)
    SLASH = int(DefenseBit.SLASH)
    FIRE = int(DefenseBit.FIRE)
    COLD = int(DefenseBit.COLD)
    LIGHTNING = int(DefenseBit.LIGHTNING)
    ACID = int(DefenseBit.ACID)
    POISON = int(DefenseBit.POISON)
    NEGATIVE = int(DefenseBit.NEGATIVE)
    HOLY = int(DefenseBit.HOLY)
    ENERGY = int(DefenseBit.ENERGY)
    MENTAL = int(DefenseBit.MENTAL)
    DISEASE = int(DefenseBit.DISEASE)
    DROWNING = int(DefenseBit.DROWNING)
    LIGHT = int(DefenseBit.LIGHT)
    SOUND = int(DefenseBit.SOUND)
    WOOD = int(DefenseBit.WOOD)
    SILVER = int(DefenseBit.SILVER)
    IRON = int(DefenseBit.IRON)


# END imm_res_vuln_flags


class FormFlag(IntFlag):
    """FORM_* flags (merc.h) describing anatomical archetypes."""

    EDIBLE = 1 << 0  # A
    POISON = 1 << 1  # B
    MAGICAL = 1 << 2  # C
    INSTANT_DECAY = 1 << 3  # D
    OTHER = 1 << 4  # E
    ANIMAL = 1 << 6  # G
    SENTIENT = 1 << 7  # H
    UNDEAD = 1 << 8  # I
    CONSTRUCT = 1 << 9  # J
    MIST = 1 << 10  # K
    INTANGIBLE = 1 << 11  # L
    BIPED = 1 << 12  # M
    CENTAUR = 1 << 13  # N
    INSECT = 1 << 14  # O
    SPIDER = 1 << 15  # P
    CRUSTACEAN = 1 << 16  # Q
    WORM = 1 << 17  # R
    BLOB = 1 << 18  # S
    MAMMAL = 1 << 21  # V
    BIRD = 1 << 22  # W
    REPTILE = 1 << 23  # X
    SNAKE = 1 << 24  # Y
    DRAGON = 1 << 25  # Z
    AMPHIBIAN = 1 << 26  # aa
    FISH = 1 << 27  # bb
    COLD_BLOOD = 1 << 28  # cc


class PartFlag(IntFlag):
    """PART_* flags (merc.h) describing body parts present."""

    HEAD = 1 << 0  # A
    ARMS = 1 << 1  # B
    LEGS = 1 << 2  # C
    HEART = 1 << 3  # D
    BRAINS = 1 << 4  # E
    GUTS = 1 << 5  # F
    HANDS = 1 << 6  # G
    FEET = 1 << 7  # H
    FINGERS = 1 << 8  # I
    EARS = 1 << 9  # J
    EYES = 1 << 10  # K
    LONG_TONGUE = 1 << 11  # L
    EYESTALKS = 1 << 12  # M
    TENTACLES = 1 << 13  # N
    FINS = 1 << 14  # O
    WINGS = 1 << 15  # P
    TAIL = 1 << 16  # Q
    CLAWS = 1 << 20  # U
    FANGS = 1 << 21  # V
    HORNS = 1 << 22  # W
    SCALES = 1 << 23  # X
    TUSKS = 1 << 24  # Y


# START extra_flags
class ExtraFlag(IntFlag):
    """ITEM_* extra flags mapped to ROM bit letters (A..Z)."""

    GLOW = 1 << 0  # A
    HUM = 1 << 1  # B
    DARK = 1 << 2  # C
    LOCK = 1 << 3  # D
    EVIL = 1 << 4  # E
    INVIS = 1 << 5  # F
    MAGIC = 1 << 6  # G
    NODROP = 1 << 7  # H
    BLESS = 1 << 8  # I
    ANTI_GOOD = 1 << 9  # J
    ANTI_EVIL = 1 << 10  # K
    ANTI_NEUTRAL = 1 << 11  # L
    NOREMOVE = 1 << 12  # M
    INVENTORY = 1 << 13  # N
    NOPURGE = 1 << 14  # O
    ROT_DEATH = 1 << 15  # P
    VIS_DEATH = 1 << 16  # Q
    # R unused in ROM
    NONMETAL = 1 << 18  # S
    NOLOCATE = 1 << 19  # T
    MELT_DROP = 1 << 20  # U
    HAD_TIMER = 1 << 21  # V
    SELL_EXTRACT = 1 << 22  # W
    # X unused in ROM
    BURN_PROOF = 1 << 24  # Y
    NOUNCURSE = 1 << 25  # Z


# Legacy constants for compatibility
ITEM_GLOW = ExtraFlag.GLOW
ITEM_HUM = ExtraFlag.HUM
ITEM_DARK = ExtraFlag.DARK
ITEM_LOCK = ExtraFlag.LOCK
ITEM_EVIL = ExtraFlag.EVIL
ITEM_INVIS = ExtraFlag.INVIS
ITEM_MAGIC = ExtraFlag.MAGIC
ITEM_NODROP = ExtraFlag.NODROP
ITEM_BLESS = ExtraFlag.BLESS
ITEM_ANTI_GOOD = ExtraFlag.ANTI_GOOD
ITEM_ANTI_EVIL = ExtraFlag.ANTI_EVIL
ITEM_ANTI_NEUTRAL = ExtraFlag.ANTI_NEUTRAL
ITEM_NOREMOVE = ExtraFlag.NOREMOVE
ITEM_INVENTORY = ExtraFlag.INVENTORY
ITEM_NOPURGE = ExtraFlag.NOPURGE
ITEM_ROT_DEATH = ExtraFlag.ROT_DEATH
ITEM_VIS_DEATH = ExtraFlag.VIS_DEATH
ITEM_NONMETAL = ExtraFlag.NONMETAL
ITEM_NOLOCATE = ExtraFlag.NOLOCATE
ITEM_MELT_DROP = ExtraFlag.MELT_DROP
ITEM_HAD_TIMER = ExtraFlag.HAD_TIMER
ITEM_SELL_EXTRACT = ExtraFlag.SELL_EXTRACT
ITEM_BURN_PROOF = ExtraFlag.BURN_PROOF
ITEM_NOUNCURSE = ExtraFlag.NOUNCURSE
# END extra_flags

# --- Exit/portal flags (merc.h) ---
# Bits map to letters A..Z; EX_ISDOOR=A (1<<0), EX_CLOSED=B (1<<1)
EX_ISDOOR = 1 << 0
EX_CLOSED = 1 << 1
EX_LOCKED = 1 << 2
EX_PICKPROOF = 1 << 5
EX_NOPASS = 1 << 6
EX_EASY = 1 << 7
EX_HARD = 1 << 8
EX_INFURIATING = 1 << 9
EX_NOCLOSE = 1 << 10
EX_NOLOCK = 1 << 11


class PortalFlag(IntFlag):
    """Portal gate flags mirroring ROM GATE_* bitmasks."""

    NORMAL_EXIT = 1 << 0  # (A)
    NOCURSE = 1 << 1  # (B)
    GOWITH = 1 << 2  # (C)
    BUGGY = 1 << 3  # (D)
    RANDOM = 1 << 4  # (E)


GATE_NORMAL_EXIT = PortalFlag.NORMAL_EXIT
GATE_NOCURSE = PortalFlag.NOCURSE
GATE_GOWITH = PortalFlag.GOWITH
GATE_BUGGY = PortalFlag.BUGGY
GATE_RANDOM = PortalFlag.RANDOM


def convert_flags_from_letters(flag_letters: str, flag_enum_class: type[F]) -> F:
    """Convert ROM letter-based flags (e.g., "ABCD") to integer bitmask.

    Args:
        flag_letters: String of flag letters from ROM .are file (e.g., "ABCD")
        flag_enum_class: The IntFlag enum class (e.g., ExtraFlag)

    Returns:
        Integer bitmask combining all flags
    """
    bits = 0
    for ch in flag_letters.strip():
        if "A" <= ch <= "Z":
            bits |= 1 << (ord(ch) - ord("A"))
        elif "a" <= ch <= "z":
            # Handle lowercase letters as well (some ROM variants use them)
            bits |= 1 << (ord(ch) - ord("a") + 26)
    return flag_enum_class(bits)
