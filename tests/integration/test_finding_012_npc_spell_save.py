"""Regression for FINDING-012 (differential `spell_combat` scenario, 2026-05-29).

Casting a `saves_spell`-using offensive spell at a *real* NPC — a `MobInstance`
produced by `from_prototype`, as gameplay spawns them — must not crash.

ROM `CHAR_DATA.saving_throw` is a field shared by PCs and NPCs; `saves_spell`
(`src/magic.c:170`) reads `victim->saving_throw` for every target. The Python
`MobInstance` dataclass mirrors many `CHAR_DATA` fields but had **omitted**
`saving_throw`, so any offensive spell that routes through `saves_spell` raised
`AttributeError: 'MobInstance' object has no attribute 'saving_throw'` when cast
at an NPC.

No prior test caught it: every existing `magic_missile` test uses a `Character`
victim (which carries `saving_throw`) *or* monkeypatches `saves_spell` away
(see `tests/test_skills_damage.py::test_magic_missile_rolls_rom_damage_table`).
This test deliberately does neither — a `from_prototype` `MobInstance` victim and
the **real** `saves_spell`.

ROM C: src/magic.c:170 (`saves_spell` reads `victim->saving_throw`),
        src/db.c create_mobile (leaves a mob's `saving_throw` at 0).
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.spawning.templates import MobInstance
from mud.utils import rng_mm


def test_magic_missile_at_mob_instance_invokes_real_saves_spell_without_crashing():
    rng_mm.seed_mm(12345)

    caster = Character(name="Wizard", level=25, is_npc=False)
    proto = MobIndex(vnum=49050, short_descr="a practice dummy", player_name="dummy")
    proto.level = 20
    proto.damage_type = "beating"
    mob = MobInstance.from_prototype(proto)
    mob.hit = mob.max_hit = 200

    room = Room(vnum=49051)
    room.add_character(caster)
    room.add_character(mob)

    # The mob must carry the ROM CHAR_DATA saving_throw field (0 for mobs).
    assert mob.saving_throw == 0

    # REAL saves_spell (not monkeypatched) reads mob.saving_throw — must not raise
    # AttributeError. magic_missile returns the damage dealt and applies it.
    damage = skill_handlers.magic_missile(caster, mob)

    assert isinstance(damage, int)
    assert damage > 0
