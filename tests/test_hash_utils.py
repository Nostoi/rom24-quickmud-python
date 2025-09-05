from mud.security.hash_utils import hash_password, verify_password


def test_hash_password_unique_and_verifies():
    password = "swordfish"
    h1 = hash_password(password)
    h2 = hash_password(password)
    assert h1 != h2
    assert ":" in h1 and ":" in h2
    assert verify_password(password, h1)
    assert verify_password(password, h2)
    assert not verify_password("wrong", h1)
    assert not verify_password(password, "invalid")
