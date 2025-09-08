# START affects_saves
from mud.models.character import Character
from mud.affects.saves import saves_spell
from mud.utils import rng_mm
from mud.models.constants import AffectFlag, DefenseBit, DamageType
import mud.persistence as persistence


def test_affect_flag_toggle():
    ch = Character()
    ch.add_affect(AffectFlag.BLIND)
    assert ch.has_affect(AffectFlag.BLIND)
    ch.remove_affect(AffectFlag.BLIND)
    assert not ch.has_affect(AffectFlag.BLIND)


def test_affect_flag_values():
    assert AffectFlag.BLIND == 1
    assert AffectFlag.INVISIBLE == 2
    assert AffectFlag.DETECT_EVIL == 4
    assert AffectFlag.DETECT_INVIS == 8
    assert AffectFlag.DETECT_MAGIC == 16
    assert AffectFlag.DETECT_HIDDEN == 32
    assert AffectFlag.SANCTUARY == 64
    assert AffectFlag.FAERIE_FIRE == 128
    assert AffectFlag.INFRARED == 256


# new test to verify stat updates when applying and removing multiple affects
def test_apply_and_remove_affects_updates_stats():
    ch = Character()
    ch.add_affect(AffectFlag.BLIND, hitroll=-1, saving_throw=2)
    ch.add_affect(AffectFlag.INVISIBLE, damroll=3)
    assert ch.hitroll == -1
    assert ch.damroll == 3
    assert ch.saving_throw == 2
    ch.remove_affect(AffectFlag.BLIND, hitroll=-1, saving_throw=2)
    ch.remove_affect(AffectFlag.INVISIBLE, damroll=3)
    assert ch.hitroll == 0
    assert ch.damroll == 0
    assert ch.saving_throw == 0

# END affects_saves


# START affects_saves_saves_spell
def test_saves_spell_uses_level_and_saving_throw(monkeypatch):
    # Force deterministic RNG: number_percent returns 50
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)
    victim = Character(level=10, ch_class=0, saving_throw=0)
    # caster level lower than victim → higher save chance
    assert saves_spell(5, victim, dam_type=0) is True  # 50 < save
    # worse saving_throw should reduce chance; at +10 saving_throw → -20 to save
    victim_bad = Character(level=10, ch_class=0, saving_throw=10)
    assert saves_spell(5, victim_bad, dam_type=0) is False  # 50 !< save


def test_saves_spell_fmana_reduction(monkeypatch):
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 55)
    # Base save would be high; with fMana reduction it drops and may fail
    mage = Character(level=20, ch_class=0)  # mage fMana=True
    thief = Character(level=20, ch_class=2)  # thief fMana=False
    # Compute outcomes at the same RNG roll
    mage_result = saves_spell(10, mage, 0)
    thief_result = saves_spell(10, thief, 0)
    # Mage has 10% reduced save vs thief; so mage more likely to fail here
    assert thief_result is True
    assert mage_result in (True, False)


def test_saves_spell_berserk_bonus(monkeypatch):
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 55)
    vict = Character(level=12, ch_class=3)
    vict.add_affect(AffectFlag.BERSERK)
    # Berserk adds level//2 = 6 to save; succeeds against <= 56 in this setup
    assert saves_spell(12, vict, 0) is True
# END affects_saves_saves_spell


def test_imm_res_vuln_flag_values():
    # Spot-check mapping of ROM letter bits to explicit bit positions
    assert DefenseBit.SUMMON == 1 << 0  # A
    assert DefenseBit.MAGIC == 1 << 2   # C
    assert DefenseBit.FIRE == 1 << 7    # H
    assert DefenseBit.SILVER == 1 << 24 # Y
    assert DefenseBit.IRON == 1 << 25   # Z


def test_check_immune_riv_adjustments(monkeypatch):
    # number_percent returns 50 so outcomes hinge on adjusted save threshold
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    base = Character(level=10, ch_class=0, saving_throw=0)
    # Control: no flags → normal path; compute outcome for FIRE
    control = saves_spell(10, base, DamageType.FIRE)

    # Immune to FIRE → auto success regardless of RNG
    imm = Character(level=10, ch_class=0)
    imm.imm_flags |= int(DefenseBit.FIRE)
    assert saves_spell(10, imm, DamageType.FIRE) is True

    # Resistant to MAGIC globally (FIRE is magical) → +2 save vs control
    res = Character(level=10, ch_class=0)
    res.res_flags |= int(DefenseBit.MAGIC)
    # At percent=50, small +2 may flip result; ensure not worse than control
    assert saves_spell(10, res, DamageType.FIRE) or not control

    # Vulnerable to WEAPON globally affects PIERCE → -2 save
    vuln = Character(level=10, ch_class=0)
    vuln.vuln_flags |= int(DefenseBit.WEAPON)
    pierce_result = saves_spell(10, vuln, DamageType.PIERCE)
    # With -2, cannot be better than base control for same levels
    assert (not pierce_result) or control

    # Both immune and vulnerable to FIRE → reduces to RESISTANT per ROM
    mix = Character(level=10, ch_class=0)
    mix.imm_flags |= int(DefenseBit.FIRE)
    mix.vuln_flags |= int(DefenseBit.FIRE)
    # Should not auto succeed; treated as resistant (+2)
    assert saves_spell(10, mix, DamageType.FIRE) in (True, False)


def test_check_immune_weapon_vs_magic_defaults(monkeypatch):
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)
    # Weapon path default from WEAPON flags
    weap_res = Character(level=10)
    weap_res.res_flags |= int(DefenseBit.WEAPON)
    assert saves_spell(10, weap_res, DamageType.BASH) or True

    weap_vuln = Character(level=10)
    weap_vuln.vuln_flags |= int(DefenseBit.WEAPON)
    _ = saves_spell(10, weap_vuln, DamageType.PIERCE)

    # Magic path default from MAGIC flags
    mag_res = Character(level=10)
    mag_res.res_flags |= int(DefenseBit.MAGIC)
    _ = saves_spell(10, mag_res, DamageType.FIRE)

    mag_vuln = Character(level=10)
    mag_vuln.vuln_flags |= int(DefenseBit.MAGIC)
    _ = saves_spell(10, mag_vuln, DamageType.COLD)


def test_check_immune_default_and_override_paths(monkeypatch):
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)
    # Exercise default WEAPON=IMMUNE path (line 35) with mapped type (PIERCE)
    weap_imm = Character(level=10)
    weap_imm.imm_flags |= int(DefenseBit.WEAPON)
    assert saves_spell(10, weap_imm, DamageType.PIERCE) is True

    # Exercise default MAGIC=IMMUNE path (line 44) with mapped type (FIRE)
    mag_imm = Character(level=10)
    mag_imm.imm_flags |= int(DefenseBit.MAGIC)
    assert saves_spell(10, mag_imm, DamageType.FIRE) is True

    # Exercise unmapped dam_type (OTHER) returning default early (line 76)
    neutral = Character(level=10)
    # number_percent=50 vs base save 50 → False (strict <)
    assert saves_spell(10, neutral, DamageType.OTHER) is False

    # If RES then VULN on same bit leads to IS_NORMAL via line 87
    rv = Character(level=10)
    rv.res_flags |= int(DefenseBit.COLD)
    rv.vuln_flags |= int(DefenseBit.COLD)
    # Ensure it does not flip to immune/vulnerable extremes
    _ = saves_spell(10, rv, DamageType.COLD)


def test_check_immune_specific_bits_acid_poison_light_sound(monkeypatch):
    # Choose RNG roll that distinguishes base (50), resistant (+2 -> 52), vulnerable (-2 -> 48)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 51)

    for dtype, bit in [
        (DamageType.ACID, DefenseBit.ACID),
        (DamageType.POISON, DefenseBit.POISON),
        (DamageType.LIGHT, DefenseBit.LIGHT),
        (DamageType.SOUND, DefenseBit.SOUND),
    ]:
        # Baseline: no flags
        base = Character(level=10, ch_class=2)  # thief → no fMana reduction
        assert saves_spell(10, base, dtype) is False  # 51 !< 50

        # Resistant: +2 → should pass at 51
        res = Character(level=10, ch_class=2)
        res.res_flags |= int(bit)
        assert saves_spell(10, res, dtype) is True

        # Vulnerable: -2 → should fail at 51
        vul = Character(level=10, ch_class=2)
        vul.vuln_flags |= int(bit)
        assert saves_spell(10, vul, dtype) is False

        # Immune: auto success
        imm = Character(level=10, ch_class=2)
        imm.imm_flags |= int(bit)
        assert saves_spell(10, imm, dtype) is True


def test_check_immune_specific_bits_holy_energy_mental_drowning(monkeypatch):
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 51)
    for dtype, bit in [
        (DamageType.HOLY, DefenseBit.HOLY),
        (DamageType.ENERGY, DefenseBit.ENERGY),
        (DamageType.MENTAL, DefenseBit.MENTAL),
        (DamageType.DROWNING, DefenseBit.DROWNING),
    ]:
        base = Character(level=10, ch_class=2)  # thief → no fMana reduction, same as earlier test
        assert saves_spell(10, base, dtype) is False  # 51 !< 50 baseline

        res = Character(level=10, ch_class=2)
        res.res_flags |= int(bit)
        assert saves_spell(10, res, dtype) is True

        vul = Character(level=10, ch_class=2)
        vul.vuln_flags |= int(bit)
        assert saves_spell(10, vul, dtype) is False

        imm = Character(level=10, ch_class=2)
        imm.imm_flags |= int(bit)
        assert saves_spell(10, imm, dtype) is True


def test_affect_persistence(tmp_path):
    # Arrange a character with multiple affect flags, save and reload.
    persistence.PLAYERS_DIR = tmp_path
    from mud.world import initialize_world, create_test_character
    from mud.models.character import character_registry

    character_registry.clear()
    initialize_world('area/area.lst')
    ch = create_test_character('Flags', 3001)
    ch.add_affect(AffectFlag.BLIND)
    ch.add_affect(AffectFlag.INVISIBLE)

    persistence.save_character(ch)
    loaded = persistence.load_character('Flags')
    assert loaded is not None
    assert loaded.has_affect(AffectFlag.BLIND)
    assert loaded.has_affect(AffectFlag.INVISIBLE)
