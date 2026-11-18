"""Password hashing, strength policy, zero-default-account check, and bootstrap CLI tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cli.bootstrap_owner import main as bootstrap_cli_main
from app.core.errors import ValidationDomainError
from app.core.security import (
    hash_password,
    validate_password_strength,
    verify_password,
    verify_password_constant_time,
)
from app.db.models import AdminAuditLog, AdminRole, AdminUser
from app.db.session import build_engine, reset_db_globals
from app.services.audit_service import AuditAction


def test_fresh_database_has_zero_default_accounts(db_session: Session) -> None:
    count = db_session.scalar(select(func.count()).select_from(AdminUser))
    assert count == 0


def test_bcrypt_password_hashing_and_verification() -> None:
    secret = "Strong#TailorPass2026"
    hashed = hash_password(secret, rounds=10)
    assert hashed != secret
    assert hashed.startswith("$2b$10$")
    assert verify_password(secret, hashed) is True
    assert verify_password("Wrong#TailorPass2026", hashed) is False
    assert verify_password_constant_time(secret, None, rounds=10) is False
    assert verify_password_constant_time(secret, hashed, rounds=10) is True


@pytest.mark.parametrize(
    ("bad_password", "username"),
    [
        ("Short1!", "owner_user"),
        ("alllowercase123!", "owner_user"),
        ("ALLUPPERCASE123!", "owner_user"),
        ("NoDigitsHere!!!!", "owner_user"),
        ("NoSymbolsHere1234", "owner_user"),
        ("MyPassword1234!@", "owner_user"),  # contains 'password'
        ("Owner_User#2026!", "owner_user"),  # contains username
        ("A" * 70 + "a1!", "owner_user"),  # > 72 UTF-8 bytes
    ],
)
def test_password_strength_rejects_weak_inputs(bad_password: str, username: str) -> None:
    with pytest.raises(ValidationDomainError):
        validate_password_strength(bad_password, username=username)


def test_bootstrap_owner_cli_provisions_owner_and_blocks_silent_duplicate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli_db = tmp_path / "bootstrap_cli.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{cli_db}")
    monkeypatch.setenv("BCRYPT_ROUNDS", "10")
    monkeypatch.setenv("BOOTSTRAP_OWNER_PASSWORD", "Dhundhwana#Owner99!")
    from app.core.config import get_settings

    get_settings.cache_clear()
    reset_db_globals()

    exit_code = bootstrap_cli_main(
        [
            "--username",
            "dhundhwana_owner",
            "--display-name",
            "Business Owner",
            "--locale",
            "gu",
            "--init-schema",
            "--non-interactive",
        ]
    )
    assert exit_code == 0

    # Attempting to bootstrap a second OWNER without --allow-additional-owner must fail
    exit_code_dup = bootstrap_cli_main(
        [
            "--username",
            "second_owner",
            "--display-name",
            "Second Owner",
            "--non-interactive",
        ]
    )
    assert exit_code_dup == 1

    engine = build_engine(f"sqlite:///{cli_db}")
    with Session(engine) as check_db:
        owners = list(check_db.scalars(select(AdminUser)).all())
        assert len(owners) == 1
        assert owners[0].username == "dhundhwana_owner"
        assert owners[0].role == AdminRole.OWNER.value
        assert owners[0].preferred_locale == "gu"

        audit_row = check_db.scalar(
            select(AdminAuditLog).where(
                AdminAuditLog.action_type == AuditAction.OWNER_BOOTSTRAPPED.value
            )
        )
        assert audit_row is not None
        assert "Dhundhwana#Owner99!" not in str(audit_row.change_summary)
    engine.dispose()
    get_settings.cache_clear()
    reset_db_globals()
