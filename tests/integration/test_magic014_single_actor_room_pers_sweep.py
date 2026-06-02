"""Regression for MAGIC-014 — INV-025 manual-room-loop PERS sweep remainder.

The 2.12.30 INV-025 pass converted the `_act_room` call sites to the shared
`act_to_room` helper but missed handlers that baked `_character_name()` into a
`room.broadcast(...)` call or a hand-rolled `for occupant in room.people` loop.
ROM emits each of these single-actor spell-effect room lines as
`act("$n ...", actor, NULL, NULL, TO_ROOM)`, so `comm.c` renders `$n` per
recipient via `PERS(actor, to)` — masking an actor the recipient cannot see to
"someone" (capitalized "Someone" at sentence start).

This batch converts the remaining ~11 `$n`-only sites: create_rose
(`magic.c:1536`), earthquake (`:2263`), giant_strength (`:3041`), haste
(`:3104`) + its slow-dispel leg (`:3088`), pass_door (`:3887`), sleep (`:4380`),
slow (`:4434`) + its haste-dispel leg (`:4420`), stone_skin (`:4465`), weaken
(`:4581`). All are `$n`-only (no `$s`), so a *visible* actor renders the same
name as before; only the masking of an unseen actor changes.

This test proves the masking for a representative sample (one target-actor with a
plain `$n`, one with `$n's`, one caster-actor) — an invisible actor renders
"Someone" to a sighted witness, while a visible actor renders the real name.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, Sector
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _lit_room(vnum: int = 3055) -> Room:
    # CITY sector is never dark (ROM room_is_dark), so visibility is deterministic.
    room = Room(vnum=vnum, name="Plaza", sector_type=int(Sector.CITY))
    room.people = []
    return room


def test_haste_room_line_masks_invisible_target() -> None:
    caster = Character(name="Mage", level=30, is_npc=False)
    target = Character(name="Runner", level=20, is_npc=False)
    witness = Character(name="Witness", level=18, is_npc=False)
    room = _lit_room()
    for ch in (caster, target, witness):
        room.add_character(ch)

    # Visible target → name renders.
    witness.messages.clear()
    assert skill_handlers.haste(caster, target) is True
    assert witness.messages[-1] == "Runner is moving more quickly.", witness.messages

    # Invisible target → ROM `$n` masks to "Someone" for the sighted witness.
    target2 = Character(name="Sneak", level=20, is_npc=False)
    room.add_character(target2)
    target2.add_affect(AffectFlag.INVISIBLE)
    witness.messages.clear()
    assert skill_handlers.haste(caster, target2) is True
    assert witness.messages[-1] == "Someone is moving more quickly.", witness.messages


def test_giant_strength_room_line_masks_invisible_target() -> None:
    caster = Character(name="Mage", level=30, is_npc=False)
    target = Character(name="Sneak", level=20, is_npc=False)
    witness = Character(name="Witness", level=18, is_npc=False)
    room = _lit_room()
    for ch in (caster, target, witness):
        room.add_character(ch)
    target.add_affect(AffectFlag.INVISIBLE)
    witness.messages.clear()

    assert skill_handlers.giant_strength(caster, target) is True
    # ROM `$n's` → masked actor renders "Someone's".
    assert witness.messages[-1] == "Someone's muscles surge with heightened power.", witness.messages


def test_earthquake_room_line_masks_invisible_caster() -> None:
    caster = Character(name="Mage", level=30, is_npc=False)
    witness = Character(name="Witness", level=18, is_npc=False)
    room = _lit_room()
    for ch in (caster, witness):
        room.add_character(ch)
    caster.add_affect(AffectFlag.INVISIBLE)
    witness.messages.clear()

    skill_handlers.earthquake(caster)
    # Caster-actor line; an invisible caster masks to "Someone" for the witness.
    # (The tremble line is broadcast before the area damage, so assert presence.)
    assert "Someone makes the earth tremble and shiver." in witness.messages, witness.messages
