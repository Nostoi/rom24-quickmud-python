"""MAGIC-033 — know_alignment renders via ROM act("$N …") semantics.

ROM `spell_know_alignment` (`src/magic.c:3674-3690`) builds an alignment-band
message and emits it with a single `act(msg, ch, NULL, victim, TO_CHAR)` — every
tier starts with `$N` = PERS(victim), capitalized. Three divergences in the Python:

  1. NPC victims must render the **short_descr** (PERS), capitalized — the Python
     baked the keyword `name`.
  2. There is **no "You …" self-variant** — ROM always uses `$N`, so a self-cast
     shows the caster's own name (PERS(ch, ch) = name), not "You …".
  3. The most-evil tier is ROM's literal "$N is the embodiment of pure evil!." —
     note the double `!.` (a ROM typo, preserved verbatim).
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position, Sex
from mud.models.room import Room
from mud.skills.handlers import know_alignment


def test_magic033_know_alignment_npc_uses_pers_shortdescr_capitalized():
    room = Room(vnum=99205, name="Sanctum")
    caster = Character(name="Diviner", level=24, is_npc=False, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []
    goblin = Character(
        name="goblin", is_npc=True, short_descr="a green goblin", alignment=900, position=int(Position.STANDING)
    )
    room.add_character(goblin)

    msg = know_alignment(caster, goblin)
    assert msg == "A green goblin has a pure and good aura.", msg


def test_magic033_know_alignment_self_cast_shows_name_not_you():
    room = Room(vnum=99206, name="Sanctum")
    caster = Character(
        name="Diviner", level=24, is_npc=False, alignment=-120, sex=int(Sex.MALE), position=int(Position.STANDING)
    )
    room.add_character(caster)
    caster.messages = []

    msg = know_alignment(caster)
    # alignment -120 -> "lies to $S friends"; ROM has no "You" variant.
    assert msg == "Diviner lies to his friends.", msg


def test_magic033_know_alignment_most_evil_tier_preserves_rom_typo():
    room = Room(vnum=99207, name="Sanctum")
    caster = Character(name="Diviner", level=24, is_npc=False, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []
    demon = Character(
        name="demon", is_npc=True, short_descr="a vile demon", alignment=-1000, position=int(Position.STANDING)
    )
    room.add_character(demon)

    msg = know_alignment(caster, demon)
    assert msg == "A vile demon is the embodiment of pure evil!.", msg
