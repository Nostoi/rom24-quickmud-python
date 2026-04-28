"""Integration parity tests for ROM ``src/db2.c`` loaders.

Each test pins a single behavior of the area-file loaders against the
canonical ROM C reference. Gap IDs reference ``docs/parity/DB2_C_AUDIT.md``.
"""
from __future__ import annotations

from mud.loaders.base_loader import BaseTokenizer
from mud.loaders.json_loader import _load_mobs_from_json
from mud.loaders.mob_loader import load_mobiles
from mud.registry import mob_registry


def _are_fragment(vnum: int, ac_line: str, act_flags: str = "AB") -> list[str]:
    """Minimal new-format #MOBILES block ROM ``load_mobiles`` accepts."""

    return [
        f"#{vnum}",
        "guard~",
        "the city guard~",
        "A burly guard stands here.",
        "~",
        "A lawful, well-armored guard.",
        "~",
        "human~",
        f"{act_flags} 0 0 0",
        "20 0 1d1+0 1d1+0 1d4+0 beating",
        ac_line,
        "0 0 0 0",
        "stand stand male 0",
        "0 0 medium 0",
        "#0",
    ]


def test_load_mobiles_multiplies_armor_class_by_ten():
    """DB2-006: ROM ``src/db2.c:273-276`` stores ``fread_number * 10`` for
    every AC field. The .are loader must do the same so spawned NPCs use the
    correct ROM AC magnitude (negative-AC convention, lower = better)."""

    mob_registry.pop(99001, None)
    tokenizer = BaseTokenizer(_are_fragment(99001, "-15 -10 -5 1"))
    load_mobiles(tokenizer, area=None)

    mob = mob_registry[99001]
    assert mob.ac_pierce == -150
    assert mob.ac_bash == -100
    assert mob.ac_slash == -50
    assert mob.ac_exotic == 10

    mob_registry.pop(99001, None)


def test_load_mobiles_from_json_multiplies_armor_class_by_ten():
    """DB2-006: JSON area files store the raw .are number; the JSON loader
    must apply the same ``* 10`` normalization as ROM ``src/db2.c:273-276``
    so both load paths converge on identical in-memory MobIndex objects."""

    mob_registry.pop(99002, None)
    payload = {
        "id": 99002,
        "name": "the city guard",
        "ac_pierce": -15,
        "ac_bash": -10,
        "ac_slash": -5,
        "ac_exotic": 1,
    }
    _load_mobs_from_json([payload], area=None)

    mob = mob_registry[99002]
    assert mob.ac_pierce == -150
    assert mob.ac_bash == -100
    assert mob.ac_slash == -50
    assert mob.ac_exotic == 10

    mob_registry.pop(99002, None)


def test_load_mobiles_forces_act_is_npc_flag():
    """DB2-001: ROM ``src/db2.c:239`` ORs ``ACT_IS_NPC`` into every mob's
    act_flags unconditionally. The .are loader must do the same so a mob
    whose area-file flags string omits the ``A`` letter still tests as an
    NPC via ``IS_NPC()`` (``ActFlag.IS_NPC`` bit)."""

    from mud.models.constants import ActFlag

    mob_registry.pop(99003, None)
    tokenizer = BaseTokenizer(_are_fragment(99003, "0 0 0 0", act_flags="B"))
    load_mobiles(tokenizer, area=None)

    mob = mob_registry[99003]
    assert ActFlag.IS_NPC in mob.get_act_flags()

    mob_registry.pop(99003, None)


def test_load_mobiles_from_json_forces_act_is_npc_flag():
    """DB2-001: JSON loader must apply the same unconditional
    ``ACT_IS_NPC`` OR as ROM ``src/db2.c:239`` so JSON-only mobs without
    an explicit ``A`` letter still spawn as NPCs."""

    from mud.models.constants import ActFlag

    mob_registry.pop(99004, None)
    payload = {"id": 99004, "name": "the city guard", "act_flags": "B"}
    _load_mobs_from_json([payload], area=None)

    mob = mob_registry[99004]
    assert ActFlag.IS_NPC in mob.get_act_flags()

    mob_registry.pop(99004, None)


def test_load_mobiles_merges_race_table_flags():
    """DB2-002: ROM ``src/db2.c:239-242,279-286,295-297`` ORs the
    race_table[].{act,aff,off,imm,res,vuln,form,parts} bits into every
    mob's flag fields. The .are loader must do the same so a dragon
    spawns flying with infrared (race-derived AffectFlag.FLYING |
    AffectFlag.INFRARED), even when the area-file flags are blank."""

    from mud.models.constants import AffectFlag, convert_flags_from_letters

    mob_registry.pop(99005, None)
    fragment = _are_fragment(99005, "0 0 0 0", act_flags="A")
    fragment[7] = "dragon~"
    tokenizer = BaseTokenizer(fragment)
    load_mobiles(tokenizer, area=None)

    mob = mob_registry[99005]
    affected = convert_flags_from_letters(mob.affected_by, AffectFlag)
    assert AffectFlag.FLYING in affected
    assert AffectFlag.INFRARED in affected

    mob_registry.pop(99005, None)


def test_load_mobiles_from_json_merges_race_table_flags():
    """DB2-002: JSON loader must apply the same race-table flag merge as
    ROM ``src/db2.c:239-242,279-286,295-297`` so race-derived intrinsics
    are not silently dropped on the JSON load path."""

    from mud.models.constants import AffectFlag, convert_flags_from_letters

    mob_registry.pop(99006, None)
    payload = {"id": 99006, "name": "the wyrm", "race": "dragon"}
    _load_mobs_from_json([payload], area=None)

    mob = mob_registry[99006]
    affected = convert_flags_from_letters(mob.affected_by, AffectFlag)
    assert AffectFlag.FLYING in affected
    assert AffectFlag.INFRARED in affected

    mob_registry.pop(99006, None)


def test_load_mobiles_uppercases_first_char_of_long_descr_and_description():
    """DB2-003: ROM ``src/db2.c:236-237`` does
    ``pMobIndex->long_descr[0] = UPPER(...)`` and the same for ``description``
    to defend against area-builder typos. The .are loader must do the same so
    a mob with a lowercase first letter still renders capitalized in room
    output."""

    mob_registry.pop(99007, None)
    fragment = _are_fragment(99007, "0 0 0 0")
    fragment[3] = "a burly guard stands here."
    fragment[5] = "a lawful, well-armored guard."
    tokenizer = BaseTokenizer(fragment)
    load_mobiles(tokenizer, area=None)

    mob = mob_registry[99007]
    assert mob.long_descr.startswith("A burly")
    assert mob.description.startswith("A lawful")

    mob_registry.pop(99007, None)


def test_load_mobiles_from_json_uppercases_first_char_of_long_descr_and_description():
    """DB2-003: JSON loader must apply the same first-char uppercasing as
    ROM ``src/db2.c:236-237`` so JSON-only mobs cannot render lowercase
    long_descr/description in the room output."""

    mob_registry.pop(99008, None)
    payload = {
        "id": 99008,
        "name": "the city guard",
        "long_description": "a burly guard stands here.",
        "description": "a lawful, well-armored guard.",
    }
    _load_mobs_from_json([payload], area=None)

    mob = mob_registry[99008]
    assert mob.long_descr.startswith("A burly")
    assert mob.description.startswith("A lawful")

    mob_registry.pop(99008, None)
