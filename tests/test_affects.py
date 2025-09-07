# START affects_saves
from mud.models.character import Character
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
