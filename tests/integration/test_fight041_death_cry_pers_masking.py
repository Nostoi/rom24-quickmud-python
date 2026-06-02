"""FIGHT-041 — death_cry's in-room gore line must use per-recipient PERS masking.

ROM ``death_cry`` (``src/fight.c:1640``) broadcasts the selected gore line via
``act(msg, ch, NULL, NULL, TO_ROOM)``, so ``comm.c`` renders ``$n`` through
``PERS(ch, to)`` for every recipient — an invisible corpse-to-be masks to
"someone" for a witness without detect-invis. The Python ``death_cry``
(``mud/combat/death.py:329``) baked ``victim.name`` once via
``expand_placeholders`` + ``room.broadcast``, leaking the name (INV-025 class).

These tests pin ``number_bits`` to 0 → ``"$n hits the ground ... DEAD."`` (a
clean ``$n``-only template with no gore object), and assert the masked render.
"""

from __future__ import annotations

import pytest

from mud.combat.death import death_cry
from mud.models.character import Character
from mud.models.constants import AffectFlag, Sector
from mud.models.room import Room
from mud.utils import rng_mm


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name="Crypt", sector_type=int(Sector.CITY))
    room.people = []
    room.contents = []
    return room


def test_death_cry_masks_invisible_victim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rng_mm, "number_bits", lambda bits: 0)
    room = _room(9401)
    victim = Character(name="Victim", level=5, is_npc=False, room=room)
    witness = Character(name="Witness", level=5, is_npc=False, room=room)
    room.people.extend([victim, witness])
    victim.add_affect(AffectFlag.INVISIBLE)
    witness.messages.clear()

    death_cry(victim)

    # ROM act("$n hits the ground ... DEAD.", victim, TO_ROOM) → "Someone …".
    assert any(m == "Someone hits the ground ... DEAD." for m in witness.messages), witness.messages
    assert not any("Victim" in m for m in witness.messages), witness.messages


def test_death_cry_shows_name_to_sighted_witness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rng_mm, "number_bits", lambda bits: 0)
    room = _room(9402)
    victim = Character(name="Victim", level=5, is_npc=False, room=room)
    witness = Character(name="Witness", level=5, is_npc=False, room=room)
    room.people.extend([victim, witness])
    witness.messages.clear()

    death_cry(victim)

    assert any(m == "Victim hits the ground ... DEAD." for m in witness.messages), witness.messages
