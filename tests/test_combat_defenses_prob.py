from mud.commands import process_command
from mud.models.constants import DamageType
from mud.world import create_test_character, initialize_world


def setup_function(_):
    initialize_world("area/area.lst")


def _setup_pair():
    attacker = create_test_character("Attacker", 3001)
    victim = create_test_character("Victim", 3001)
    victim.is_npc = True  # Ensure victim is NPC to avoid PK restrictions
    attacker.hitroll = 100
    attacker.damroll = 3
    attacker.dam_type = int(DamageType.BASH)
    victim.armor = [0, 0, 0, 0]
    victim.hit = 50
    return attacker, victim


def test_shield_block_triggers_before_parry_and_dodge(monkeypatch):
    from mud.utils import rng_mm

    attacker, victim = _setup_pair()
    # Set ROM-style skill attributes that our implementation uses
    victim.skills["shield block"] = 100  # Will give 100/5 + 3 = 23% base chance
    victim.skills["parry"] = 100
    victim.skills["dodge"] = 100
    # Must have shield equipped for shield block to work
    victim.has_shield_equipped = True
    # Ensure percent roll always hits the threshold
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)
    out = process_command(attacker, "kill victim")
    assert out == "Victim blocks your attack with a shield."


def test_parry_triggers_when_no_shield(monkeypatch):
    from mud.utils import rng_mm

    attacker, victim = _setup_pair()
    # Set ROM-style skill attribute that our implementation uses
    victim.skills["parry"] = 100  # Will give 100/2 = 50% base chance
    victim.has_weapon_equipped = True
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)
    out = process_command(attacker, "kill victim")
    assert out == "Victim parries your attack."


def test_dodge_triggers_when_no_shield_or_parry(monkeypatch):
    from mud.utils import rng_mm

    attacker, victim = _setup_pair()
    # Set ROM-style skill attribute that our implementation uses
    victim.skills["dodge"] = 100  # Will give (100/2) + (victim.level/2) base chance
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)
    out = process_command(attacker, "kill victim")
    assert out == "Victim dodges your attack."
