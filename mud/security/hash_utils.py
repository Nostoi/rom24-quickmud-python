import hashlib
import os


def hash_password(password: str) -> str:
    """Return a salted hash for the given password."""
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + hashed.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    """Check password against the stored ``salt:hash`` string."""
    try:
        salt_hex, hash_hex = stored_hash.split(":")
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    new_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return new_hash.hex() == hash_hex
