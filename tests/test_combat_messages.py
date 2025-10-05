from mud.combat.messages import TYPE_HIT, dam_message
from mud.models.character import Character


def _make_character(name: str) -> Character:
    return Character(name=name, max_hit=100, hit=100, is_npc=False)


def test_dam_message_uses_rom_tiers():
    attacker = _make_character("Attacker")
    victim = _make_character("Victim")

    messages = dam_message(attacker, victim, 80, TYPE_HIT, immune=False)

    assert messages.attacker == "{2You *** DEVASTATE *** Victim!{x"
    assert messages.victim == "{4Attacker *** DEVASTATES *** you!{x"
    assert messages.room == "{3Attacker *** DEVASTATES *** Victim!{x"


def test_dam_message_handles_immune():
    attacker = _make_character("Mage")
    victim = _make_character("Golem")

    messages = dam_message(attacker, victim, 0, "fireball", immune=True)

    assert messages.attacker == "{2Golem is unaffected by your fireball!{x"
    assert messages.victim == "{4Mage's fireball is powerless against you.{x"
    assert messages.room == "{3Golem is unaffected by Mage's fireball!{x"
    assert not messages.self_inflicted

