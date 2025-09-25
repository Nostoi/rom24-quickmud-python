"""Mitchell–Moore RNG for ROM parity.

Implements ROM's RNG surface with C-style gating:
- number_mm(): Mitchell–Moore generator (OLD_RAND branch in ROM) — returns a
  non‑negative int with lower bits used by callers.
- number_percent(): returns 1..100 inclusive using bitmask + while-gate.
- number_range(a,b): ROM power-of-two mask with while-gate to avoid bias.
- number_bits(width): lower ``width`` bits of ``number_mm()``.
- dice(n,size): sum of ``number_range(1,size)`` repeated ``n`` times.

References:
- C src/db.c:number_mm/number_percent/number_range/number_bits/dice
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

MASK_30 = (1 << 30) - 1


@dataclass
class _MMState:
    state: list[int]
    i1: int
    i2: int


_mm: _MMState | None = None


def _init_state(seed: int) -> _MMState:
    # Mirrors ROM init_mm() when OLD_RAND is defined
    state = [0] * 55
    i1 = 55 - 55  # 0
    i2 = 55 - 24  # 31
    state[0] = seed & MASK_30
    state[1] = 1
    for i in range(2, 55):
        state[i] = (state[i - 1] + state[i - 2]) & MASK_30
    return _MMState(state=state, i1=i1, i2=i2)


def _ensure_mm() -> _MMState:
    global _mm
    if _mm is None:
        # Default seed: time ^ pid like ROM's srandom(time ^ getpid) branch
        seed = int(time.time()) ^ os.getpid()
        _mm = _init_state(seed)
    return _mm


def seed_mm(seed: int) -> None:
    """Seed the Mitchell–Moore generator deterministically."""
    global _mm
    _mm = _init_state(int(seed))


def number_mm() -> int:
    """ROM Mitchell–Moore output with 6 LSBs discarded (>> 6 in callers).

    We return the full value; public helpers mask/shift per ROM usage.
    """
    mm = _ensure_mm()
    iRand = (mm.state[mm.i1] + mm.state[mm.i2]) & MASK_30
    mm.state[mm.i1] = iRand
    mm.i1 += 1
    if mm.i1 == 55:
        mm.i1 = 0
    mm.i2 += 1
    if mm.i2 == 55:
        mm.i2 = 0
    # Return with 6 LSBs discarded to mirror ROM behavior.
    return iRand >> 6


def number_percent() -> int:
    """Return 1..100 inclusive using ROM's 7-bit mask + while-gate."""
    # while ((percent = number_mm() & (128 - 1)) > 99);
    # return 1 + percent;
    percent = number_mm() & (128 - 1)
    while percent > 99:
        percent = number_mm() & (128 - 1)
    return 1 + percent


def number_range(from_val: int, to_val: int) -> int:
    """Return integer in [from_val, to_val] inclusive using ROM logic.

    Matches ROM C exactly: if (to = to - from + 1) <= 1, return from.
    This handles the case where to_val < from_val by returning from_val.
    """
    if from_val == 0 and to_val == 0:
        return 0

    # ROM logic: to = to - from + 1
    to = to_val - from_val + 1
    if to <= 1:
        return from_val

    power = 2
    while power < to:
        power <<= 1

    # while ((number = number_mm () & (power - 1)) >= to);
    number = number_mm() & (power - 1)
    while number >= to:
        number = number_mm() & (power - 1)

    return from_val + number


def number_fuzzy(number: int) -> int:
    """Stick a little fuzz on a number like ROM's number_fuzzy."""

    roll = number_bits(2)
    if roll == 0:
        number -= 1
    elif roll == 3:
        number += 1
    return max(1, number)


def number_bits(width: int) -> int:
    if width <= 0:
        return 0
    return number_mm() & ((1 << width) - 1)


def dice(number: int, size: int) -> int:
    if size == 0:
        return 0
    if size == 1:
        return number
    total = 0
    for _ in range(number):
        total += number_range(1, size)
    return total
