from enum import IntEnum, IntFlag


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


class Sex(IntEnum):
    """Biological sex of a character"""

    NONE = 0
    MALE = 1
    FEMALE = 2
    EITHER = 3


class Size(IntEnum):
    """Character sizes"""

    TINY = 0
    SMALL = 1
    MEDIUM = 2
    LARGE = 3
    HUGE = 4
    GIANT = 5


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


# START affects_saves
class AffectFlag(IntFlag):
    BLIND = 1 << 0
    INVISIBLE = 1 << 1
    DETECT_EVIL = 1 << 2
    DETECT_INVIS = 1 << 3
    DETECT_MAGIC = 1 << 4
    DETECT_HIDDEN = 1 << 5
    SANCTUARY = 1 << 6
    FAERIE_FIRE = 1 << 7
    INFRARED = 1 << 8
    CURSE = 1 << 9
    UNUSED1 = 1 << 10
    POISON = 1 << 11
    PROTECT_EVIL = 1 << 12
    PROTECT_GOOD = 1 << 13
    SNEAK = 1 << 14
    HIDE = 1 << 15
    SLEEP = 1 << 16
    CHARM = 1 << 17
    FLYING = 1 << 18
    PASS_DOOR = 1 << 19
    UNUSED2 = 1 << 20
    BERSERK = 1 << 21
    CALM = 1 << 22
    HASTE = 1 << 23
    SLOW = 1 << 24
    PLAGUE = 1 << 25
    DARK_VISION = 1 << 26
    UNUSED3 = 1 << 27
    SWIM = 1 << 28
    REGENERATION = 1 << 29
    UNUSED4 = 1 << 30
    UNUSED5 = 1 << 31


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

# START extra_flags
class ExtraFlag(IntFlag):
    """ITEM_* extra flags mapped to ROM bit letters (A..Z)."""
    
    GLOW = 1 << 0        # A
    HUM = 1 << 1         # B
    DARK = 1 << 2        # C
    LOCK = 1 << 3        # D
    EVIL = 1 << 4        # E
    INVIS = 1 << 5       # F
    MAGIC = 1 << 6       # G
    NODROP = 1 << 7      # H
    BLESS = 1 << 8       # I
    ANTI_GOOD = 1 << 9   # J
    ANTI_EVIL = 1 << 10  # K
    ANTI_NEUTRAL = 1 << 11  # L
    NOREMOVE = 1 << 12   # M
    INVENTORY = 1 << 13  # N
    NOPURGE = 1 << 14    # O
    ROT_DEATH = 1 << 15  # P
    VIS_DEATH = 1 << 16  # Q
    # R unused in ROM
    NONMETAL = 1 << 18   # S
    NOLOCATE = 1 << 19   # T
    MELT_DROP = 1 << 20  # U
    HAD_TIMER = 1 << 21  # V
    SELL_EXTRACT = 1 << 22  # W
    # X unused in ROM
    BURN_PROOF = 1 << 24  # Y
    NOUNCURSE = 1 << 25   # Z

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


def convert_flags_from_letters(flag_letters: str, flag_enum_class) -> int:
    """Convert ROM letter-based flags (e.g., "ABCD") to integer bitmask.
    
    Args:
        flag_letters: String of flag letters from ROM .are file (e.g., "ABCD")  
        flag_enum_class: The IntFlag enum class (e.g., ExtraFlag)
        
    Returns:
        Integer bitmask combining all flags
    """
    bits = 0
    for ch in flag_letters.strip():
        if 'A' <= ch <= 'Z':
            bits |= 1 << (ord(ch) - ord('A'))
        elif 'a' <= ch <= 'z':
            # Handle lowercase letters as well (some ROM variants use them)
            bits |= 1 << (ord(ch) - ord('a') + 26)
    return flag_enum_class(bits)
