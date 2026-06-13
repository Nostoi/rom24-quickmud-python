"""FIGHT-066 — attack_round's defense-return string uses $N PERS, not a baked name.

ROM `check_parry`/`check_dodge`/`check_shield_block` (`src/fight.c:1316-1370`) emit
`act("$N parries/dodges/blocks your attack.", ch, NULL, victim, TO_CHAR)` — `$N` =
PERS(victim), capitalized. The real player delivery already does this via
`_push_message` + `pers()` inside those functions (FIGHT-031/032); but
`apply_damage`/`attack_round` also returned a latent `f"{victim.name} …"` baked
string. This test pins the return to the ROM-faithful PERS form so a future
refactor that delivers it can't reintroduce the baked keyword.
"""

from __future__ import annotations

from mud.combat import engine as combat_engine
from mud.combat.engine import apply_damage
from mud.models.character import Character
from mud.models.constants import DamageType, Position
from mud.models.room import Room

_TYPE_HIT = 1000  # mirrors engine.TYPE_HIT — gates _should_check_weapon_defenses


def test_fight066_parry_return_uses_pers_cap(monkeypatch):
    room = Room(vnum=99219, name="Arena")
    attacker = Character(name="Knight", level=20, is_npc=False, position=int(Position.FIGHTING))
    room.add_character(attacker)
    victim = Character(
        name="goblin", is_npc=True, short_descr="a green goblin", level=18, position=int(Position.FIGHTING)
    )
    room.add_character(victim)

    monkeypatch.setattr(combat_engine, "check_parry", lambda a, v: True)

    out = apply_damage(attacker, victim, 10, int(DamageType.SLASH), dt=_TYPE_HIT)
    assert out == "A green goblin parries your attack.", out
