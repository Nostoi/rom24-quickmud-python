from mud.security.hash_utils import hash_password, verify_password


def test_hash_and_verify():
    hashed = hash_password("secret")
    assert hashed.startswith("$2")
    assert verify_password("secret", hashed)
    assert not verify_password("wrong", hashed)
