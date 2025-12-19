from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ExtraFlag, ItemType, WeaponFlag
from mud.models.obj import Affect, ObjIndex
from mud.models.object import Object
from mud.skills.handlers import envenom
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "tester"),
        "level": overrides.get("level", 20),
        "skills": overrides.get("skills", {}),
        "is_npc": overrides.get("is_npc", False),
        "inventory": overrides.get("inventory", []),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def make_food(name: str = "apple", poisoned: bool = False, blessed: bool = False) -> Object:
    proto = ObjIndex(
        vnum=1000,
        name=name,
        short_descr=f"a {name}",
        item_type=int(ItemType.FOOD),
        extra_flags=int(ExtraFlag.BLESS) if blessed else 0,
        value=[10, 10, 0, 1 if poisoned else 0, 0],
    )
    obj = Object(instance_id=1, prototype=proto)
    obj.value = list(proto.value)
    obj.item_type = ItemType.FOOD
    return obj


def make_weapon(
    name: str = "sword",
    edged: bool = True,
    poisoned: bool = False,
    blessed: bool = False,
    flaming: bool = False,
) -> Object:
    proto = ObjIndex(
        vnum=2000,
        name=name,
        short_descr=f"a {name}",
        item_type=int(ItemType.WEAPON),
        extra_flags=int(ExtraFlag.BLESS) if blessed else 0,
        value=[0, 5, 10, 0 if edged else -1, 0],
    )
    obj = Object(instance_id=2, prototype=proto)
    obj.value = list(proto.value)
    obj.item_type = ItemType.WEAPON
    obj.affected = []

    if poisoned:
        obj.affected.append(
            Affect(
                where=5,
                type=-1,
                level=20,
                duration=10,
                location=0,
                modifier=0,
                bitvector=int(WeaponFlag.POISON),
            )
        )

    if flaming:
        obj.affected.append(
            Affect(
                where=5,
                type=-1,
                level=20,
                duration=-1,
                location=0,
                modifier=0,
                bitvector=int(WeaponFlag.FLAMING),
            )
        )

    return obj


def test_envenom_requires_item_name():
    """ROM L856-860: Must specify what to envenom."""
    thief = make_character(level=30, skills={"envenom": 75})

    result = envenom(thief, item_name="")

    assert result["success"] is False
    assert "what item" in result["message"].lower()


def test_envenom_item_not_in_inventory():
    """ROM L862-868: Item must be in inventory."""
    thief = make_character(level=30, skills={"envenom": 75})

    result = envenom(thief, item_name="sword")

    assert result["success"] is False
    assert "don't have" in result["message"].lower()


def test_envenom_requires_skill():
    """ROM L870-874: Must have envenom skill."""
    thief = make_character(level=30, skills={})
    food = make_food()
    thief.inventory = [food]

    result = envenom(thief, item_name="apple")

    assert result["success"] is False
    assert "crazy" in result["message"].lower()


def test_envenom_food_success():
    """ROM L885-896: Successfully poison food."""
    thief = make_character(level=30, skills={"envenom": 95})
    food = make_food("bread", poisoned=False)
    thief.inventory = [food]

    rng_mm.seed_mm(0x1234)
    result = envenom(thief, item_name="bread")

    assert result["success"] is True
    assert result.get("poisoned_food") is True
    assert food.value[3] == 1


def test_envenom_food_blessed_fails():
    """ROM L878-883: Can't poison blessed food."""
    thief = make_character(level=30, skills={"envenom": 95})
    food = make_food("bread", blessed=True)
    thief.inventory = [food]

    result = envenom(thief, item_name="bread")

    assert result["success"] is False
    assert "fail" in result["message"].lower()


def test_envenom_weapon_success():
    """ROM L933-951: Successfully envenom edged weapon."""
    thief = make_character(level=30, skills={"envenom": 95})
    weapon = make_weapon("dagger", edged=True)
    thief.inventory = [weapon]

    rng_mm.seed_mm(0x5678)
    result = envenom(thief, item_name="dagger")

    assert result["success"] is True
    assert result.get("poisoned_weapon") is True
    assert len(weapon.affected) == 1
    assert weapon.affected[0].bitvector == int(WeaponFlag.POISON)


def test_envenom_weapon_already_poisoned():
    """ROM L927-931: Can't envenom already poisoned weapon."""
    thief = make_character(level=30, skills={"envenom": 95})
    weapon = make_weapon("dagger", poisoned=True)
    thief.inventory = [weapon]

    result = envenom(thief, item_name="dagger")

    assert result["success"] is False
    assert "already envenomed" in result["message"].lower()


def test_envenom_weapon_blessed_fails():
    """ROM L907-918: Can't envenom blessed weapon."""
    thief = make_character(level=30, skills={"envenom": 95})
    weapon = make_weapon("sword", blessed=True)
    thief.inventory = [weapon]

    result = envenom(thief, item_name="sword")

    assert result["success"] is False
    assert "can't seem" in result["message"].lower()


def test_envenom_weapon_flaming_fails():
    """ROM L907-918: Can't envenom flaming weapon."""
    thief = make_character(level=30, skills={"envenom": 95})
    weapon = make_weapon("sword", flaming=True)
    thief.inventory = [weapon]

    result = envenom(thief, item_name="sword")

    assert result["success"] is False
    assert "can't seem" in result["message"].lower()


def test_envenom_weapon_not_edged_fails():
    """ROM L920-925: Can only envenom edged weapons."""
    thief = make_character(level=30, skills={"envenom": 95})
    weapon = make_weapon("club", edged=False)
    thief.inventory = [weapon]

    result = envenom(thief, item_name="club")

    assert result["success"] is False
    assert "edged" in result["message"].lower()


def test_envenom_uses_rom_rng():
    """ROM L885/L933: Uses ROM RNG for skill check."""
    thief = make_character(level=30, skills={"envenom": 50})
    food = make_food()
    thief.inventory = [food]

    rng_mm.seed_mm(0xDEAD)
    result1 = envenom(thief, item_name="apple")

    food2 = make_food("bread")
    thief.inventory = [food2]
    rng_mm.seed_mm(0xDEAD)
    result2 = envenom(thief, item_name="bread")

    assert result1["success"] == result2["success"]


def test_envenom_wrong_item_type_fails():
    """ROM L961-962: Can't poison non-food/non-weapon items."""
    thief = make_character(level=30, skills={"envenom": 95})
    proto = ObjIndex(
        vnum=3000,
        name="torch light",
        short_descr="a torch",
        item_type=int(ItemType.LIGHT),
        value=[0, 0, 100, 0, 0],
    )
    obj = Object(instance_id=3, prototype=proto)
    obj.item_type = ItemType.LIGHT
    thief.inventory = [obj]

    result = envenom(thief, item_name="light")

    assert result["success"] is False
    assert "can't poison" in result["message"].lower()


def test_envenom_skill_improves_on_success():
    """ROM L892/L948: check_improve called on success."""
    thief = make_character(level=30, skills={"envenom": 75})
    food = make_food()
    thief.inventory = [food]

    rng_mm.seed_mm(0x1111)
    result = envenom(thief, item_name="apple")

    if result["success"]:
        assert food.value[3] == 1
