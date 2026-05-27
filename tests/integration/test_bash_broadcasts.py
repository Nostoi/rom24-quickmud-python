"""BCAST-030 — bash skill TO_VICT and TO_NOTVICT broadcasts.

ROM C (src/fight.c:2455-2484):

Success path:
- act("$n sends you sprawling with a powerful bash!", ch, NULL, victim, TO_VICT)
- act("$n sends $N sprawling with a powerful bash.", ch, NULL, victim, TO_NOTVICT)

Failure path:
- act("$n falls flat on $s face.", ch, NULL, victim, TO_NOTVICT)
- act("You evade $n's bash, causing $m to fall flat on $s face.", ch, NULL, victim, TO_VICT)
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import character_registry
from mud.models.constants import Sex
from mud.models.room import Room
from mud.registry import room_registry
from mud.skills.handlers import bash
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clean_state():
    rooms = set(room_registry)
    char_ids = {id(c) for c in character_registry}
    yield
    for vnum in list(room_registry):
        if vnum not in rooms:
            room_registry.pop(vnum, None)
    character_registry[:] = [c for c in character_registry if id(c) in char_ids]
    for attr in ("players", "char_list", "descriptor_list"):
        if hasattr(global_registry, attr):
            delattr(global_registry, attr)


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="")
    room_registry[vnum] = room
    return room


def _char(name: str, room_vnum: int, *, sex: int = Sex.MALE):
    char = create_test_character(name, room_vnum)
    char.sex = int(sex)
    char.messages = []
    char.hit = 1000
    char.max_hit = 1000
    return char


def test_bash_success_emits_to_vict_and_to_notvict() -> None:
    _room(60100)
    attacker = _char("Attacker", 60100, sex=Sex.MALE)
    victim = _char("Victim", 60100, sex=Sex.FEMALE)
    bystander = _char("Watcher", 60100, sex=Sex.NONE)

    bash(attacker, victim, success=True, chance=80)

    vict_msgs = "\n".join(victim.messages)
    assert "Attacker sends you sprawling with a powerful bash!" in vict_msgs, (
        f"missing TO_VICT broadcast; got: {victim.messages!r}"
    )

    note_msgs = "\n".join(bystander.messages)
    assert "Attacker sends Victim sprawling with a powerful bash." in note_msgs, (
        f"missing TO_NOTVICT broadcast; got: {bystander.messages!r}"
    )

    # Actor must not receive TO_VICT or TO_NOTVICT text.
    actor_msgs = "\n".join(attacker.messages)
    assert "sends you sprawling" not in actor_msgs
    assert "sends Victim sprawling" not in actor_msgs
    # Victim must not receive the TO_NOTVICT text.
    assert "sends Victim sprawling" not in vict_msgs


def test_bash_failure_emits_to_vict_and_to_notvict_with_pronouns() -> None:
    _room(60200)
    attacker = _char("Attacker", 60200, sex=Sex.FEMALE)
    victim = _char("Victim", 60200, sex=Sex.MALE)
    bystander = _char("Watcher", 60200, sex=Sex.NONE)

    bash(attacker, victim, success=False, chance=10)

    # TO_NOTVICT: "$n falls flat on $s face." — $s = her (attacker female)
    note_msgs = "\n".join(bystander.messages)
    assert "Attacker falls flat on her face." in note_msgs, (
        f"missing TO_NOTVICT failure broadcast; got: {bystander.messages!r}"
    )

    # TO_VICT: "You evade $n's bash, causing $m to fall flat on $s face."
    # $m = her, $s = her (both from attacker)
    vict_msgs = "\n".join(victim.messages)
    assert "You evade Attacker's bash, causing her to fall flat on her face." in vict_msgs, (
        f"missing TO_VICT failure broadcast; got: {victim.messages!r}"
    )

    # Actor must not receive the broadcasts.
    actor_msgs = "\n".join(attacker.messages)
    assert "falls flat on her face." not in actor_msgs
    assert "You evade" not in actor_msgs
