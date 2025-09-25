def ensure_can_move(entity, points: int = 100) -> None:
    """Ensure the given character-like entity has movement points and fields.

    - Sets `move` and `max_move` to `points`.
    - Initializes `affected_by` and `wait` to safe defaults if missing.
    """
    # Movement pool
    entity.move = getattr(entity, "move", 0) or points
    entity.max_move = getattr(entity, "max_move", 0) or points
    # Flags used by movement checks
    if not hasattr(entity, "affected_by"):
        entity.affected_by = 0
    if not hasattr(entity, "wait"):
        entity.wait = 0
