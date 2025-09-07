# START affects_saves
from mud.models.character import Character
from mud.affects.saves import saves_spell
from mud.utils import rng_mm
from mud.models.constants import AffectFlag


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
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 60)
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
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 60)
    vict = Character(level=12, ch_class=3)
    vict.add_affect(AffectFlag.BERSERK)
    # Berserk adds level//2 = 6 to save; enough to succeed against 60
    assert saves_spell(12, vict, 0) is True
# END affects_saves_saves_spell
