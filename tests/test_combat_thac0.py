from mud.combat import engine as combat_engine


def test_thac0_interpolation_at_levels():
    # Class ids: 0 mage, 1 cleric, 2 thief, 3 warrior
    # Exact endpoints should match class_table constants (20 at level 0)
    assert combat_engine.compute_thac0(0, 0, hitroll=0, skill=100) == 20
    assert combat_engine.compute_thac0(0, 1, hitroll=0, skill=100) == 20
    assert combat_engine.compute_thac0(0, 2, hitroll=0, skill=100) == 20
    assert combat_engine.compute_thac0(0, 3, hitroll=0, skill=100) == 20

    # After ROM adjustments (halve negatives; then clamp below -5):
    # mage 32: 6
    # cleric 32: 2
    # thief 32: -4 → halve ⇒ -2
    # warrior 32: -10 → halve ⇒ -5 (then not < -5)
    assert combat_engine.compute_thac0(32, 0, hitroll=0, skill=100) == 6
    assert combat_engine.compute_thac0(32, 1, hitroll=0, skill=100) == 2
    assert combat_engine.compute_thac0(32, 2, hitroll=0, skill=100) == -2
    assert combat_engine.compute_thac0(32, 3, hitroll=0, skill=100) == -5


def test_thac0_hitroll_and_skill_adjustments():
    # Baseline mage, mid level
    base = combat_engine.compute_thac0(16, 0, hitroll=0, skill=100)
    # Increasing hitroll lowers thac0
    better_hitroll = combat_engine.compute_thac0(16, 0, hitroll=10, skill=100)
    assert better_hitroll < base
    # Lower weapon skill increases thac0
    low_skill = combat_engine.compute_thac0(16, 0, hitroll=0, skill=50)
    assert low_skill > base


def test_thac0_npc_pair_overrides_class_table():
    """FIGHT-019: NPC attackers derive (thac0_00, thac0_32) from ACT flags, not the
    PC class table (ROM src/fight.c:445-457). thac0_00 is always 20; thac0_32 is
    -10 (WARRIOR), -4 (THIEF / default), 2 (CLERIC), 6 (MAGE). The same ROM
    post-interpolation adjustments then apply, so an NPC warrior matches the PC
    warrior endpoints while a default NPC ("as good as a thief") matches the thief."""
    # NPC warrior pair (20, -10) reproduces the warrior-32 endpoint (-10 → halve ⇒ -5).
    assert combat_engine.compute_thac0(32, 0, hitroll=0, skill=100, thac0_pair=(20, -10)) == -5
    # NPC mage pair (20, 6) reproduces the mage-32 endpoint (6).
    assert combat_engine.compute_thac0(32, 0, hitroll=0, skill=100, thac0_pair=(20, 6)) == 6
    # Default NPC ("as good as a thief", -4) reproduces the thief-32 endpoint (-2).
    assert combat_engine.compute_thac0(32, 0, hitroll=0, skill=100, thac0_pair=(20, -4)) == -2
    # All pairs start at thac0_00 = 20 at level 0.
    assert combat_engine.compute_thac0(0, 0, hitroll=0, skill=100, thac0_pair=(20, -10)) == 20
