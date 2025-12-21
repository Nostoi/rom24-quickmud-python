from types import SimpleNamespace

from mud.commands import process_command
from mud.models.constants import DamageType, WeaponType, attack_lookup
from mud.world import create_test_character, initialize_world


def assert_attack_message(message: str, target: str) -> None:
    assert message.startswith("{2")
    assert target in message
    assert message.endswith("{x")


def setup_thac0_env():
    initialize_world("area/area.lst")
    atk = create_test_character("Atk", 3001)
    vic = create_test_character("Vic", 3001)
    vic.is_npc = True
    vic.armor = [0, 0, 0, 0]
    atk.dam_type = int(DamageType.BASH)
    atk.damroll = 3
    return atk, vic


def test_thac0_path_hit_and_miss(monkeypatch):
    # Enable THAC0 feature flag (patch engine's imported flag)
    monkeypatch.setattr("mud.combat.engine.COMBAT_USE_THAC0", True)

    # Deterministic dicerolls
    monkeypatch.setattr("mud.utils.rng_mm.number_bits", lambda bits: 10)

    # Strong attacker (warrior32) should hit with diceroll 10
    atk, vic = setup_thac0_env()
    atk.ch_class = 3  # warrior
    atk.level = 32
    atk.hitroll = 0
    vic.hit = 50  # Increase HP to survive ROM damage calculation
    out = process_command(atk, "kill vic")
    assert_attack_message(out, "Vic")

    # Weak attacker (mage0) should miss with same diceroll
    atk, vic = setup_thac0_env()
    atk.ch_class = 0  # mage
    atk.level = 0
    atk.hitroll = 0
    vic.hit = 50  # Increase HP to be consistent
    out = process_command(atk, "kill vic")
    assert out == "You miss Vic."


def test_weapon_skill_influences_thac0(monkeypatch):
    monkeypatch.setattr("mud.combat.engine.COMBAT_USE_THAC0", True)

    skills_used: list[int] = []

    def fake_compute_thac0(level: int, ch_class: int, *, hitroll: int, skill: int) -> int:
        skills_used.append(skill)
        return 0

    monkeypatch.setattr("mud.combat.engine.compute_thac0", fake_compute_thac0)

    attack_index = attack_lookup("slash")
    weapon_proto = SimpleNamespace(
        item_type="weapon",
        value=[int(WeaponType.SWORD), 2, 6, attack_index],
        new_format=True,
        level=20,
    )
    weapon = SimpleNamespace(
        prototype=weapon_proto,
        value=weapon_proto.value,
        item_type="weapon",
        weapon_flags=0,
        new_format=True,
        level=20,
        name="training sword",
    )

    atk, vic = setup_thac0_env()
    atk.ch_class = 3
    atk.level = 32
    atk.hitroll = 0
    atk.skills["sword"] = 0
    atk.equipment["wield"] = weapon
    vic.hit = 50
    vic.armor = [-40, -40, -40, -40]
    process_command(atk, "kill vic")

    atk, vic = setup_thac0_env()
    atk.ch_class = 3
    atk.level = 32
    atk.hitroll = 0
    atk.skills["sword"] = 100
    atk.equipment["wield"] = weapon
    vic.hit = 50
    vic.armor = [-40, -40, -40, -40]
    process_command(atk, "kill vic")

    assert skills_used == [20, 120]

    # Natural 0 always misses
    monkeypatch.setattr("mud.utils.rng_mm.number_bits", lambda bits: 0)
    atk, vic = setup_thac0_env()
    atk.ch_class = 3
    atk.level = 32
    vic.hit = 10
    out = process_command(atk, "kill vic")
    assert out == "You miss Vic."
