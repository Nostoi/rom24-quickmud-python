from types import SimpleNamespace

from mud.commands import process_command
from mud.models.constants import DamageType, WeaponType, WearLocation, attack_lookup
from mud.world import create_test_character, initialize_world


def assert_attack_message(message: str, target: str) -> None:
    assert message.startswith("{2")
    assert target in message
    assert message.endswith("{x")


def deliver_kill(char, target: str) -> str:
    """Run `kill <target>` and return the attacker-facing combat line.

    INV-001/SINGLE-DELIVERY: do_kill returns "" (ROM's void do_kill); combat
    output is delivered via _push_message, which lands in char.messages for a
    connection-less test character. Returns the first line pushed by this
    command.
    """
    before = len(char.messages)
    process_command(char, f"kill {target}")
    pushed = char.messages[before:]
    return pushed[0] if pushed else ""


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
    # FIGHT-019: the THAC0 attack roll is the only melee-hit model (no flag).
    # Deterministic dicerolls
    monkeypatch.setattr("mud.utils.rng_mm.number_bits", lambda bits: 10)

    # Strong attacker (warrior32) should hit with diceroll 10
    atk, vic = setup_thac0_env()
    atk.ch_class = 3  # warrior
    atk.level = 32
    atk.hitroll = 0
    vic.hit = 50  # Increase HP to survive ROM damage calculation
    out = deliver_kill(atk, "vic")
    assert_attack_message(out, "Vic")

    # Weak attacker (mage0) should miss with same diceroll
    atk, vic = setup_thac0_env()
    atk.ch_class = 0  # mage
    atk.level = 0
    atk.hitroll = 0
    vic.hit = 50  # Increase HP to be consistent
    out = deliver_kill(atk, "vic")
    # FIGHT-028: setup_thac0_env sets dam_type=BASH → attack_dt != TYPE_HIT, so
    # ROM dam_message renders the attack noun even on a miss (src/fight.c:2200-2211).
    assert out == "{2Your slice misses Vic.{x"


def test_weapon_skill_influences_thac0(monkeypatch):
    # FIGHT-019: THAC0 is the only model — no feature flag to enable.
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
    atk.equipment[int(WearLocation.WIELD)] = weapon
    vic.hit = 50
    vic.armor = [-40, -40, -40, -40]
    process_command(atk, "kill vic")

    atk, vic = setup_thac0_env()
    atk.ch_class = 3
    atk.level = 32
    atk.hitroll = 0
    atk.skills["sword"] = 100
    atk.equipment[int(WearLocation.WIELD)] = weapon
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
    out = deliver_kill(atk, "vic")
    # FIGHT-028: setup_thac0_env sets dam_type=BASH → attack_dt != TYPE_HIT, so
    # ROM dam_message renders the attack noun even on a miss (src/fight.c:2200-2211).
    assert out == "{2Your slice misses Vic.{x"
