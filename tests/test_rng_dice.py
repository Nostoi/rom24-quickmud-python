from __future__ import annotations

from mud.utils import rng_mm


def test_dice_rom_special_cases_and_boundaries() -> None:
    # size==0 → 0
    rng_mm.seed_mm(12345)
    assert rng_mm.dice(3, 0) == 0

    # size==1 → number (sum of 1s)
    rng_mm.seed_mm(12345)
    assert rng_mm.dice(2, 1) == 2

    # General boundaries: n..n*size inclusive
    rng_mm.seed_mm(12345)
    for n, s in [(1, 6), (2, 6), (3, 4)]:
        v = rng_mm.dice(n, s)
        assert n <= v <= n * s


def test_dice_matches_sum_of_number_range_calls() -> None:
    rng_mm.seed_mm(54321)
    a = rng_mm.number_range(1, 6) + rng_mm.number_range(1, 6)
    rng_mm.seed_mm(54321)
    b = rng_mm.dice(2, 6)
    assert a == b
