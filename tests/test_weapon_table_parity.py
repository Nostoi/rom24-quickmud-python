from __future__ import annotations

from types import SimpleNamespace

from mud.account.account_service import lookup_weapon_choice
from mud.models.character import from_orm
from mud.models.constants import (
    OBJ_VNUM_SCHOOL_AXE,
    OBJ_VNUM_SCHOOL_DAGGER,
    OBJ_VNUM_SCHOOL_FLAIL,
    OBJ_VNUM_SCHOOL_MACE,
    OBJ_VNUM_SCHOOL_POLEARM,
    OBJ_VNUM_SCHOOL_STAFF,
    OBJ_VNUM_SCHOOL_SWORD,
    OBJ_VNUM_SCHOOL_WHIP,
    WeaponType,
)


def _db_char_with_weapon(default_weapon_vnum: int) -> SimpleNamespace:
    return SimpleNamespace(
        name="WeaponTester",
        level=1,
        hp=20,
        room_vnum=3700,
        race=0,
        ch_class=0,
        sex=1,
        true_sex=1,
        alignment=0,
        act=0,
        hometown_vnum=3001,
        perm_stats="",
        size=0,
        form=0,
        parts=0,
        imm_flags=0,
        res_flags=0,
        vuln_flags=0,
        practice=5,
        train=3,
        perm_hit=100,
        perm_mana=100,
        perm_move=100,
        default_weapon_vnum=default_weapon_vnum,
        newbie_help_seen=False,
        creation_points=40,
        creation_groups="",
        creation_skills="",
        prompt=None,
        comm=0,
        player=None,
    )


def test_weapon_table_matches_rom_const_c_rows() -> None:
    """Mirror ROM `src/const.c:76-86` weapon_table exactly."""
    from mud.models.weapon_table import WEAPON_TABLE

    assert [
        (entry.name, entry.school_vnum, entry.weapon_type, entry.skill_name)
        for entry in WEAPON_TABLE
    ] == [
        ("sword", OBJ_VNUM_SCHOOL_SWORD, WeaponType.SWORD, "sword"),
        ("mace", OBJ_VNUM_SCHOOL_MACE, WeaponType.MACE, "mace"),
        ("dagger", OBJ_VNUM_SCHOOL_DAGGER, WeaponType.DAGGER, "dagger"),
        ("axe", OBJ_VNUM_SCHOOL_AXE, WeaponType.AXE, "axe"),
        ("staff", OBJ_VNUM_SCHOOL_STAFF, WeaponType.SPEAR, "spear"),
        ("flail", OBJ_VNUM_SCHOOL_FLAIL, WeaponType.FLAIL, "flail"),
        ("whip", OBJ_VNUM_SCHOOL_WHIP, WeaponType.WHIP, "whip"),
        ("polearm", OBJ_VNUM_SCHOOL_POLEARM, WeaponType.POLEARM, "polearm"),
    ]


def test_lookup_weapon_choice_uses_full_rom_weapon_table() -> None:
    """Mirror ROM table names, not a hand-maintained subset."""
    assert lookup_weapon_choice("staff") == OBJ_VNUM_SCHOOL_STAFF
    assert lookup_weapon_choice("axe") == OBJ_VNUM_SCHOOL_AXE
    assert lookup_weapon_choice("flail") == OBJ_VNUM_SCHOOL_FLAIL
    assert lookup_weapon_choice("whip") == OBJ_VNUM_SCHOOL_WHIP
    assert lookup_weapon_choice("polearm") == OBJ_VNUM_SCHOOL_POLEARM


def test_from_orm_seeds_staff_weapon_as_spear_skill() -> None:
    """Mirror ROM `nanny.c:653` through the canonical weapon_table mapping."""
    char = from_orm(_db_char_with_weapon(OBJ_VNUM_SCHOOL_STAFF))

    assert char.pcdata.learned.get("spear", 0) >= 40


def test_from_orm_seeds_all_school_weapon_skills_from_weapon_table() -> None:
    """Every ROM school weapon vnum should seed its linked weapon skill."""
    from mud.models.weapon_table import WEAPON_TABLE

    for entry in WEAPON_TABLE:
        char = from_orm(_db_char_with_weapon(entry.school_vnum))
        assert char.pcdata.learned.get(entry.skill_name, 0) >= 40, entry.name
