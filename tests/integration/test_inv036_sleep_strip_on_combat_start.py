from mud.combat.engine import set_fighting
from mud.models.character import AffectData, Character
from mud.models.constants import AffectFlag, Position


def test_set_fighting_strips_raw_sleep_affect_data() -> None:
    """Combat start must unlink raw sleep affects, not only clear AFF_SLEEP."""

    sleeper = Character(name="Sleeper", is_npc=False, position=Position.SLEEPING)
    aggressor = Character(name="Aggressor", is_npc=True, position=Position.STANDING)
    sleep_affect = AffectData(
        type="sleep",
        level=20,
        duration=4,
        location=0,
        modifier=0,
        bitvector=int(AffectFlag.SLEEP),
    )

    sleeper.affected.append(sleep_affect)
    sleeper.affected_by |= AffectFlag.SLEEP

    # ROM src/fight.c:1424-1425 calls affect_strip(ch, gsn_sleep), which
    # unlinks matching AFFECT_DATA via src/handler.c:1426-1438.
    set_fighting(sleeper, aggressor)

    assert sleeper.fighting is aggressor
    assert sleeper.position == Position.FIGHTING
    assert not sleeper.has_affect(AffectFlag.SLEEP)
    assert sleep_affect not in sleeper.affected
