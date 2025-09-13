import pytest

from helpers import ensure_can_move as _ensure_can_move_helper


@pytest.fixture
def ensure_can_move():
    """Callable fixture to provision movement points on a character-like entity.

    Usage: ensure_can_move(char[, points])
    """
    return _ensure_can_move_helper


@pytest.fixture
def movable_char_factory():
    """Factory fixture that creates a test character with movement set.

    Example:
        ch = movable_char_factory('Tester', 3001, points=200)
    """
    from mud.world import create_test_character

    def _factory(name: str, room_vnum: int, *, points: int = 100):
        ch = create_test_character(name, room_vnum)
        _ensure_can_move_helper(ch, points)
        return ch

    return _factory
