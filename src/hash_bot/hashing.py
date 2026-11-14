"""Hashing primitives kept separate from Telegram-specific code."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from argon2 import PasswordHasher, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_password_hasher = PasswordHasher()


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Outcome of checking a password against an encoded Argon2 hash."""

    matches: bool
    needs_rehash: bool = False


def hash_password(value: str) -> str:
    """Return a salted Argon2id password hash using safe library defaults."""
    if not value:
        raise ValueError("The value to hash cannot be empty.")
    return _password_hasher.hash(value)


def sha256_digest(value: str) -> str:
    """Return a deterministic SHA-256 hex digest for non-password data."""
    if not value:
        raise ValueError("The value to hash cannot be empty.")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_password(encoded_hash: str, password: str) -> VerificationResult:
    """Safely verify a password and report whether parameters are outdated."""
    if not encoded_hash or not password:
        raise ValueError("The hash and password cannot be empty.")

    try:
        _password_hasher.verify(encoded_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return VerificationResult(matches=False)

    return VerificationResult(
        matches=True,
        needs_rehash=_password_hasher.check_needs_rehash(encoded_hash),
    )


def is_argon2_hash(value: str) -> bool:
    """Return whether a string is a parseable encoded Argon2 hash."""
    try:
        extract_parameters(value)
    except (InvalidHashError, ValueError):
        return False
    return True
