from mud.combat.messages import TYPE_HIT, dam_message, render_for
from mud.models.character import Character
from mud.models.room import Room

# Shared dummy room so visibility checks (`can_see`) succeed for
# both characters — without it, `pers()` returns "someone" because
# `can_see_character` bails when either party has no room.
_DUMMY_ROOM = Room(vnum=99999, name="X", description="", room_flags=0, sector_type=0)


def _make_character(name: str) -> Character:
    char = Character(name=name, max_hit=100, hit=100, is_npc=False)
    char.room = _DUMMY_ROOM
    return char


def test_dam_message_uses_rom_tiers():
    """Verify ROM-exact wording when both characters are visible.

    `dam_message` returns templates; `render_for(template, attacker,
    victim, observer)` substitutes ROM PERS()-rendered names per
    recipient (DAMMSG-001/002/003). For these visible characters,
    PERS returns the real name regardless of observer.
    """
    attacker = _make_character("Attacker")
    victim = _make_character("Victim")

    messages = dam_message(attacker, victim, 80, TYPE_HIT, immune=False)

    assert render_for(messages.attacker, attacker, victim, attacker) == "{2You *** DEVASTATE *** Victim!{x"
    assert render_for(messages.victim, attacker, victim, victim) == "{4Attacker *** DEVASTATES *** you!{x"
    assert render_for(messages.room, attacker, victim, attacker) == "{3Attacker *** DEVASTATES *** Victim!{x"


def test_dam_message_handles_immune():
    attacker = _make_character("Mage")
    victim = _make_character("Golem")

    messages = dam_message(attacker, victim, 0, "fireball", immune=True)

    assert render_for(messages.attacker, attacker, victim, attacker) == "{2Golem is unaffected by your fireball!{x"
    assert render_for(messages.victim, attacker, victim, victim) == "{4Mage's fireball is powerless against you.{x"
    assert render_for(messages.room, attacker, victim, attacker) == "{3Golem is unaffected by Mage's fireball!{x"
    assert not messages.self_inflicted
