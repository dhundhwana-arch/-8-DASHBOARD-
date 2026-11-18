"""Cryptographic primitives: bcrypt password hashing, session token digests, and CSRF HMAC."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from functools import lru_cache

import bcrypt

from app.core.errors import ValidationDomainError

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_BYTES = 72  # bcrypt silently truncates past 72 UTF-8 bytes; enforce explicitly

_UPPER_RE = re.compile(r"[A-Z]")
_LOWER_RE = re.compile(r"[a-z]")
_DIGIT_RE = re.compile(r"[0-9]")
_SYMBOL_RE = re.compile(r"[^A-Za-z0-9\s]")

_WEAK_SUBSTRINGS: tuple[str, ...] = (
    "password",
    "changeme",
    "admin123",
    "welcome123",
    "qwerty123",
    "letmein",
)


def validate_password_strength(password: str, *, username: str | None = None) -> None:
    """Enforce strong password rules before hashing."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationDomainError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValidationDomainError(
            f"Password must not exceed {MAX_PASSWORD_BYTES} UTF-8 bytes."
        )
    if not _UPPER_RE.search(password):
        raise ValidationDomainError("Password must include at least one uppercase letter.")
    if not _LOWER_RE.search(password):
        raise ValidationDomainError("Password must include at least one lowercase letter.")
    if not _DIGIT_RE.search(password):
        raise ValidationDomainError("Password must include at least one digit.")
    if not _SYMBOL_RE.search(password):
        raise ValidationDomainError("Password must include at least one special character.")

    lowered = password.lower()
    for marker in _WEAK_SUBSTRINGS:
        if marker in lowered:
            raise ValidationDomainError("Password contains a disallowed common weak pattern.")

    if username and len(username.strip()) >= 3 and username.strip().lower() in lowered:
        raise ValidationDomainError("Password must not contain the username.")


def hash_password(password: str, *, rounds: int = 12) -> str:
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > MAX_PASSWORD_BYTES:
        raise ValidationDomainError(
            f"Password must not exceed {MAX_PASSWORD_BYTES} UTF-8 bytes."
        )
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


@lru_cache(maxsize=8)
def _dummy_bcrypt_hash(rounds: int) -> bytes:
    """Precomputed per-rounds dummy hash for timing-safe nonexistent-account checks."""
    return bcrypt.hashpw(b"dummy-nonexistent-user-timing-guard-secret!", bcrypt.gensalt(rounds=rounds))


def verify_password(plain_password: str, password_hash: str) -> bool:
    pw_bytes = plain_password.encode("utf-8")
    if len(pw_bytes) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(pw_bytes, password_hash.encode("utf-8"))
    except ValueError:
        return False


def verify_password_constant_time(
    plain_password: str,
    password_hash: str | None,
    *,
    rounds: int = 12,
) -> bool:
    """Verify password while performing an equivalent bcrypt check if the user does not exist."""
    pw_bytes = plain_password.encode("utf-8")[:MAX_PASSWORD_BYTES]
    if password_hash is None:
        bcrypt.checkpw(pw_bytes, _dummy_bcrypt_hash(rounds))
        return False
    if len(plain_password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        bcrypt.checkpw(pw_bytes, _dummy_bcrypt_hash(rounds))
        return False
    try:
        return bcrypt.checkpw(pw_bytes, password_hash.encode("utf-8"))
    except ValueError:
        return False


def generate_opaque_token(nbytes: int = 32) -> str:
    """Generate a cryptographically random URL-safe opaque token (default 256 bits)."""
    return secrets.token_urlsafe(nbytes)


def sha256_hex(raw_value: str) -> str:
    """Compute hex-encoded SHA-256 digest for storing session/CSRF tokens at rest."""
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def derive_session_csrf_token(
    *,
    session_id: str,
    session_token_hash: str,
    secret_key: str,
) -> str:
    """Deterministically derive a session-bound CSRF token using HMAC-SHA256.

    Only ``sha256_hex(csrf_token)`` is stored in ``admin_sessions.csrf_token_hash``.
    Because derivation requires both ``SESSION_SECRET_KEY`` and the HttpOnly session's
    server-side ``session_token_hash``, cross-origin attackers cannot forge it.
    """
    message = f"css-m08-csrf-v1:{session_id}:{session_token_hash}".encode()
    return hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_csrf_token(provided_token: str | None, expected_csrf_hash: str) -> bool:
    """Constant-time verification of ``X-CSRF-Token`` against stored SHA-256 digest."""
    if not provided_token or not expected_csrf_hash:
        return False
    candidate_hash = sha256_hex(provided_token.strip())
    return hmac.compare_digest(candidate_hash, expected_csrf_hash)
