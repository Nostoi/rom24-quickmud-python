# START affects_saves
from mud.models.character import Character
from mud.models.constants import AffectFlag


def test_affect_flag_toggle():
    ch = Character()
    ch.add_affect(AffectFlag.BLIND)
    assert ch.affected_by & AffectFlag.BLIND
    ch.remove_affect(AffectFlag.BLIND)
    assert ch.affected_by == 0


# END affects_saves
