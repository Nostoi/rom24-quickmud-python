from __future__ import annotations

from mud.utils import rng_mm


def test_number_mm_sequence_matches_golden_seed_12345() -> None:
    # Golden derived from ROM Mitchell–Moore algorithm (OLD_RAND path)
    rng_mm.seed_mm(12345)
    got = [rng_mm.number_mm() for _ in range(10)]
    # fmt: off
    expected = [
        9518999, 8058464, 800248, 8858713, 9658962,
        1740460, 11399423, 13139883, 7762090, 4124758,
    ]
    # fmt: on
    assert got == expected


def test_number_percent_gating_and_range_bits_and_dice() -> None:
    rng_mm.seed_mm(12345)
    # 10-step golden for percent, 1..100 inclusive
    assert [rng_mm.number_percent() for _ in range(10)] == [
        24,
        97,
        90,
        83,
        45,
        44,
        43,
        87,
        2,
        89,
    ]

    rng_mm.seed_mm(12345)
    # Range 1..6 produces only values in range; first 10 shown
    r = [rng_mm.number_range(1, 6) for _ in range(10)]
    assert r == [1, 1, 2, 3, 5, 4, 3, 2, 1, 2]
    assert all(1 <= x <= 6 for x in r)

    rng_mm.seed_mm(12345)
    # Bits returns lower-width masked values
    bits = [rng_mm.number_bits(5) for _ in range(5)]
    assert bits == [23, 0, 24, 25, 18]

    rng_mm.seed_mm(12345)
    # Dice sums number_range(1,size)
    assert rng_mm.dice(2, 6) == 2
