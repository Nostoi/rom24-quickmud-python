"""Mitchell–Moore RNG shim for parity APIs.

This is a minimal shim exposing number_percent/range so call sites can migrate
off Python's random module. Internally delegates to a local RNG for now.
"""
from __future__ import annotations

from random import Random

_rng = Random()


def seed_mm(seed: int) -> None:
    _rng.seed(seed)


def number_percent() -> int:
    """Return 1..100 inclusive (ROM's number_percent)."""
    return _rng.randint(1, 100)


def number_range(a: int, b: int) -> int:
    """Return integer in [a, b] inclusive."""
    if a > b:
        a, b = b, a
    return _rng.randint(a, b)

