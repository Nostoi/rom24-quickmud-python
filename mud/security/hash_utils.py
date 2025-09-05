import bcrypt  # type: ignore[import-not-found]


def hash_password(password: str) -> str:
    """Return a bcrypt hash for the given password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, stored_hash: str) -> bool:
    """Validate ``password`` against ``stored_hash``."""
    try:
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    except ValueError:
        return False
