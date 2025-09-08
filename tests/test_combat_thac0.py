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
