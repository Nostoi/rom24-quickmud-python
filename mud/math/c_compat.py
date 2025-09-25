"""C-compatibility helpers (division/modulo/clamp).

Matches C integer division semantics (truncate toward zero), unlike Python's
"//" which floors toward negative infinity.
"""

from __future__ import annotations


def c_div(a: int, b: int) -> int:
    """C-style integer division (truncate toward zero)."""
    if b == 0:
        raise ZeroDivisionError("c_div by zero")
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def c_mod(a: int, b: int) -> int:
    """C-style modulo consistent with c_div: a == b * c_div(a,b) + c_mod(a,b)."""
    if b == 0:
        raise ZeroDivisionError("c_mod by zero")
    return a - b * c_div(a, b)


def urange(low: int, val: int, high: int) -> int:
    """Clamp to [low, high] inclusive, like ROM's URANGE macro."""
    return max(low, min(val, high))
