from mud.combat.engine import set_fighting, stop_fighting
from mud.models.character import Character, SpellEffect, character_registry
from mud.models.constants import AffectFlag, Position


def test_stop_fighting_clears_both_sides():
    character_registry.clear()

    attacker = Character(name="Attacker", is_npc=False)
    attacker.position = Position.FIGHTING
    attacker.default_pos = int(Position.STANDING)
    attacker.hit = 42

    defender = Character(name="Defender", is_npc=True)
    defender.position = Position.FIGHTING
    defender.default_pos = int(Position.RESTING)
    defender.hit = 30

    bystander = Character(name="Watcher", is_npc=True)
    bystander.position = Position.FIGHTING
    bystander.default_pos = int(Position.STANDING)
    bystander.hit = 25

    attacker.fighting = defender
    defender.fighting = attacker

    character_registry.extend([attacker, defender, bystander])

    try:
        stop_fighting(attacker, both=True)

        assert attacker.fighting is None
        assert defender.fighting is None
        assert attacker.position == Position.STANDING
        assert defender.position == Position.RESTING
        assert bystander.position == Position.FIGHTING
    finally:
        character_registry.clear()


def test_set_fighting_strips_sleep_spell_effect():
    character_registry.clear()

    attacker = Character(name="Sleeper", is_npc=False)
    attacker.position = Position.SLEEPING
    attacker.default_pos = int(Position.STANDING)

    victim = Character(name="Intruder", is_npc=True)
    victim.position = Position.STANDING

    sleep_effect = SpellEffect(
        name="sleep",
        duration=4,
        level=12,
        affect_flag=AffectFlag.SLEEP,
        wear_off_message="You feel less drowsy.",
    )

    assert attacker.apply_spell_effect(sleep_effect) is True
    assert attacker.has_affect(AffectFlag.SLEEP)
    assert "sleep" in attacker.spell_effects

    try:
        set_fighting(attacker, victim)

        assert attacker.fighting is victim
        assert attacker.position == Position.FIGHTING
        assert not attacker.has_affect(AffectFlag.SLEEP)
        assert "sleep" not in attacker.spell_effects
    finally:
        character_registry.clear()


def test_set_fighting_announces_sleep_wear_off():
    character_registry.clear()

    sleeper = Character(name="Dozer", is_npc=False)
    sleeper.position = Position.SLEEPING
    sleeper.default_pos = int(Position.STANDING)

    aggressor = Character(name="Sneak", is_npc=True)
    aggressor.position = Position.STANDING

    sleep_effect = SpellEffect(
        name="sleep",
        duration=4,
        level=12,
        affect_flag=AffectFlag.SLEEP,
        wear_off_message="You feel less tired.",
    )

    assert sleeper.apply_spell_effect(sleep_effect)
    assert sleeper.has_affect(AffectFlag.SLEEP)

    try:
        set_fighting(sleeper, aggressor)

        assert "You feel less tired." in sleeper.messages
    finally:
        character_registry.clear()
