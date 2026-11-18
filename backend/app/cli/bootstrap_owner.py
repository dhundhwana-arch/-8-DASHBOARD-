"""Explicit OWNER account bootstrap CLI (zero default production passwords).

Usage examples:
    # Interactive prompt (recommended for production setup):
    python -m app.cli.bootstrap_owner --username owner_divyesh --display-name "Shop Owner"

    # Non-interactive one-shot bootstrap via environment variables:
    BOOTSTRAP_OWNER_PASSWORD="..." python -m app.cli.bootstrap_owner \\
        --username owner_divyesh --display-name "Shop Owner" --non-interactive
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AdminDomainError
from app.core.security import hash_password, validate_password_strength
from app.db.models import AdminRole, AdminUser, AuditOutcome, SupportedLocale
from app.db.session import build_engine, init_db_schema
from app.services.audit_service import AuditAction, AuditService
from app.services.user_service import normalize_and_validate_username


def bootstrap_owner_account(
    db: Session,
    *,
    username: str,
    display_name: str,
    password: str,
    preferred_locale: SupportedLocale = SupportedLocale.EN,
    allow_additional_owner: bool = False,
    settings: Settings | None = None,
) -> AdminUser:
    """Create the initial OWNER account safely and record an ``OWNER_BOOTSTRAPPED`` audit event."""
    resolved_settings = settings or get_settings()
    normalized_username = normalize_and_validate_username(username)
    cleaned_display = display_name.strip()
    if not cleaned_display or len(cleaned_display) > 120:
        raise ValueError("Display name must be between 1 and 120 characters.")

    validate_password_strength(password, username=normalized_username)

    existing_user = db.scalar(
        select(AdminUser).where(AdminUser.username == normalized_username)
    )
    if existing_user is not None:
        raise ValueError(f"Username '{normalized_username}' already exists.")

    existing_owner_count = int(
        db.scalar(
            select(func.count())
            .select_from(AdminUser)
            .where(AdminUser.role == AdminRole.OWNER.value)
        )
        or 0
    )
    if existing_owner_count > 0 and not allow_additional_owner:
        raise ValueError(
            "An OWNER account already exists. Pass --allow-additional-owner explicitly "
            "if provisioning a second OWNER is intentional."
        )

    owner = AdminUser(
        username=normalized_username,
        display_name=cleaned_display,
        password_hash=hash_password(password, rounds=resolved_settings.bcrypt_rounds),
        role=AdminRole.OWNER.value,
        preferred_locale=preferred_locale.value,
        is_active=True,
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

    AuditService(resolved_settings).record_event(
        db,
        actor=owner,
        action_type=AuditAction.OWNER_BOOTSTRAPPED,
        resource_type="ADMIN_USER",
        resource_id=owner.public_id,
        outcome=AuditOutcome.SUCCESS,
        is_security_event=True,
        change_summary={
            "bootstrapped_username": owner.username,
            "role": owner.role,
            "preferred_locale": owner.preferred_locale,
        },
    )
    return owner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Provision the initial Module 08 OWNER account (no default passwords)."
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("BOOTSTRAP_OWNER_USERNAME", ""),
        help="Unique lowercase username for the OWNER account.",
    )
    parser.add_argument(
        "--display-name",
        default=os.environ.get("BOOTSTRAP_OWNER_DISPLAY_NAME", ""),
        help="Display name shown in the dashboard.",
    )
    parser.add_argument(
        "--locale",
        choices=["en", "gu"],
        default=os.environ.get("BOOTSTRAP_OWNER_LOCALE", "en"),
        help="Preferred UI locale ('en' or 'gu').",
    )
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="Ensure the 6 Module 08 tables and audit triggers exist before bootstrapping.",
    )
    parser.add_argument(
        "--allow-additional-owner",
        action="store_true",
        help="Explicitly allow creating an additional OWNER when one already exists.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Read password strictly from BOOTSTRAP_OWNER_PASSWORD without TTY prompt.",
    )
    args = parser.parse_args(argv)

    if not args.username or not args.display_name:
        print(
            "ERROR: --username and --display-name are required.",
            file=sys.stderr,
        )
        return 2

    password = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "")
    if not password:
        if args.non_interactive:
            print(
                "ERROR: BOOTSTRAP_OWNER_PASSWORD must be set when using --non-interactive.",
                file=sys.stderr,
            )
            return 2
        first = getpass.getpass("Enter strong OWNER password (>= 12 chars): ")
        second = getpass.getpass("Confirm OWNER password: ")
        if first != second:
            print("ERROR: Passwords did not match.", file=sys.stderr)
            return 2
        password = first

    try:
        settings = get_settings()
        engine = build_engine(settings.database_url)
        if args.init_schema:
            init_db_schema(engine)

        with Session(engine, expire_on_commit=False) as db:
            owner = bootstrap_owner_account(
                db,
                username=args.username,
                display_name=args.display_name,
                password=password,
                preferred_locale=SupportedLocale(args.locale),
                allow_additional_owner=args.allow_additional_owner,
                settings=settings,
            )
            print(
                f"SUCCESS: Provisioned OWNER account username='{owner.username}' "
                f"public_id='{owner.public_id}'."
            )
        engine.dispose()
        return 0
    except (AdminDomainError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
