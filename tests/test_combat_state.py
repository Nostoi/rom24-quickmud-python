from mud.combat.engine import stop_fighting
from mud.models.character import Character, character_registry
from mud.models.constants import Position


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
