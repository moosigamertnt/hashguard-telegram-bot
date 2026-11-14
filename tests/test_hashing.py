import pytest
from argon2 import PasswordHasher

from hash_bot.hashing import (
    hash_password,
    is_argon2_hash,
    sha256_digest,
    verify_password,
)


def test_argon2_hash_can_be_verified() -> None:
    encoded = hash_password("correct horse battery staple")
    assert encoded.startswith("$argon2id$")
    assert PasswordHasher().verify(encoded, "correct horse battery staple") is True


def test_argon2_uses_a_random_salt() -> None:
    assert hash_password("same-password") != hash_password("same-password")


def test_password_verification_reports_a_match() -> None:
    encoded = hash_password("portfolio-ready")
    result = verify_password(encoded, "portfolio-ready")
    assert result.matches is True
    assert result.needs_rehash is False


def test_password_verification_rejects_wrong_password() -> None:
    encoded = hash_password("right-password")
    assert verify_password(encoded, "wrong-password").matches is False


@pytest.mark.parametrize("value", ["not-a-hash", "$argon2id$broken", ""])
def test_argon2_hash_validation_rejects_malformed_values(value: str) -> None:
    assert is_argon2_hash(value) is False


def test_argon2_hash_validation_accepts_generated_hash() -> None:
    assert is_argon2_hash(hash_password("hello")) is True


def test_sha256_is_deterministic() -> None:
    assert sha256_digest("hello") == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


@pytest.mark.parametrize("function", [hash_password, sha256_digest])
def test_empty_input_is_rejected(function) -> None:
    with pytest.raises(ValueError):
        function("")
