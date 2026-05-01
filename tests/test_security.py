from app.security import hash_password, verify_password


def test_password_hash_round_trip():
    password = "Citizen@123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_password_hash_rejects_invalid_password():
    hashed = hash_password("Admin@123")
    assert not verify_password("wrong-password", hashed)
