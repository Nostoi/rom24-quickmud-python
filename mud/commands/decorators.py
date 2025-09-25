from functools import wraps

from mud.models.character import Character


def admin_only(func):
    @wraps(func)
    def wrapper(char: Character, *args, **kwargs):
        if not getattr(char, "is_admin", False):
            return "You do not have permission to use this command."
        return func(char, *args, **kwargs)

    return wrapper
