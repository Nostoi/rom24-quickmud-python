"""FIGHT-048 — do_murder must call do_yell on victim, not return yell as command response.

ROM src/fight.c:2888: ``do_function(victim, &do_yell, buf)`` makes the VICTIM
yell "Help! I am being attacked by X!" area-wide (every area character sees
"$n yells 'Help! I am being attacked by X!'" where $n = victim).

Python built ``yell_msg`` inside ``do_murder`` but returned it to the attacker
as part of the command response string — the victim never yelled, no area
character heard anything.  Also, Python returned an extra "You attack $n!"
message that ROM never sends (the attacker sees only combat output from
multi_hit and possibly "*** You are now a KILLER!! ***" from check_killer).
"""

from __future__ import annotations

import pytest

from mud.commands.murder import do_murder
from mud.models.constants import Position
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_combatants():
    """Clan PC attacker + clan PC victim, both in room 3001."""
    attacker = create_test_character("Slayer", 3001)
    victim = create_test_character("Helpless", 3001)

    attacker.clan = 1  # _murder_safety_check clan gate
    attacker.position = int(Position.STANDING)

    victim.clan = 1  # _murder_safety_check victim clan gate
    victim.position = int(Position.STANDING)

    return attacker, victim


def test_murder_victim_gets_yell_message(monkeypatch: pytest.MonkeyPatch) -> None:
    # mirrors ROM src/fight.c:2888 — do_function(victim, &do_yell, buf).
    # Victim must receive "You yell '...'" after do_murder fires.
    attacker, victim = _make_combatants()
    monkeypatch.setattr("mud.commands.murder.check_killer", lambda a, v: None)
    monkeypatch.setattr("mud.commands.murder.multi_hit", lambda a, v, t: None)

    do_murder(attacker, "Helpless")

    assert any("You yell" in m for m in victim.messages), (
        "FIGHT-048: victim must receive 'You yell' TO_CHAR message — "
        "do_yell must be called on the victim, not returned to the attacker"
    )


def test_murder_return_value_not_yell(monkeypatch: pytest.MonkeyPatch) -> None:
    # ROM do_murder sends no message to attacker from do_murder itself.
    # The "You attack...Help!..." string must not appear in the return value.
    attacker, victim = _make_combatants()
    monkeypatch.setattr("mud.commands.murder.check_killer", lambda a, v: None)
    monkeypatch.setattr("mud.commands.murder.multi_hit", lambda a, v, t: None)

    result = do_murder(attacker, "Helpless")

    assert "being attacked" not in (result or "").lower(), (
        f"FIGHT-048: do_murder must not return victim yell to attacker; got: {result!r}"
    )
