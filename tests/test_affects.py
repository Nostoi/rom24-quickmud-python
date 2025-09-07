# START affects_saves
from mud.models.character import Character
from mud.models.constants import AffectFlag


def test_affect_flag_toggle():
    ch = Character()
    ch.add_affect(AffectFlag.BLIND)
    assert ch.has_affect(AffectFlag.BLIND)
    ch.remove_affect(AffectFlag.BLIND)
    assert not ch.has_affect(AffectFlag.BLIND)


# END affects_saves
