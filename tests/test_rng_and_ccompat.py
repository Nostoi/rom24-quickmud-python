from mud.utils import rng_mm
from mud.math.c_compat import c_div, c_mod, urange


def test_rng_seed_and_number_percent():
    rng_mm.seed_mm(12345)
    a = [rng_mm.number_percent() for _ in range(5)]
    rng_mm.seed_mm(12345)
    b = [rng_mm.number_percent() for _ in range(5)]
    assert a == b  # deterministic


def test_number_range_swaps_bounds_and_inclusive():
    rng_mm.seed_mm(1)
    # Ensure it works when a > b and result lies within inclusive bounds
    for _ in range(10):
        val = rng_mm.number_range(10, 7)  # swapped internally to [7,10]
        assert 7 <= val <= 10


def test_c_div_and_c_mod_parity_with_c():
    # Division truncates toward zero
    assert c_div(7, 3) == 2
    assert c_div(-7, 3) == -2
    assert c_div(7, -3) == -2
    assert c_div(-7, -3) == 2
    # Modulo matches a == b * c_div(a,b) + c_mod(a,b)
    for a in (-7, -6, -1, 0, 1, 6, 7):
        for b in (1, 2, 3):
            assert a == b * c_div(a, b) + c_mod(a, b)


def test_c_div_c_mod_zero_division():
    import pytest

    with pytest.raises(ZeroDivisionError):
        c_div(1, 0)
    with pytest.raises(ZeroDivisionError):
        c_mod(1, 0)


def test_urange_clamps_values():
    assert urange(0, -5, 10) == 0
    assert urange(0, 5, 10) == 5
    assert urange(0, 15, 10) == 10

