"""Database schema boundary, constraint, and Alembic migration tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.db.base import Base
from app.db.models import (
    APPROVED_MODULE_08_TABLES,
    AdminUser,
    InternalAdminNote,
    WorkshopResource,
)
from app.db.session import build_engine

PROHIBITED_TABLES = {
    "payment_records",
    "payments",
    "transactions",
    "customers",
    "orders",
    "order_items",
    "fabrics",
    "fabric_variants",
    "fabric_inventory",
    "quotations",
    "pricing_rules",
    "measurements",
}


def test_metadata_contains_strictly_six_approved_tables() -> None:
    registered_tables = set(Base.metadata.tables.keys())
    assert len(registered_tables) == 6
    assert registered_tables == set(APPROVED_MODULE_08_TABLES)
    assert registered_tables.isdisjoint(PROHIBITED_TABLES)


def test_alembic_upgrade_downgrade_roundtrip(tmp_path: Path) -> None:
    migration_db = tmp_path / "alembic_roundtrip.db"
    db_url = f"sqlite:///{migration_db}"

    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", db_url)

    # Upgrade to head
    command.upgrade(cfg, "head")
    engine = build_engine(db_url)
    inspector = inspect(engine)
    tables_after_upgrade = set(inspector.get_table_names()) - {"alembic_version"}
    assert tables_after_upgrade == set(APPROVED_MODULE_08_TABLES)
    engine.dispose()

    # Downgrade to base
    command.downgrade(cfg, "base")
    engine = build_engine(db_url)
    inspector = inspect(engine)
    tables_after_downgrade = set(inspector.get_table_names()) - {"alembic_version"}
    assert tables_after_downgrade == set()
    engine.dispose()

    # Re-upgrade cleanly
    command.upgrade(cfg, "head")
    engine = build_engine(db_url)
    inspector = inspect(engine)
    assert (set(inspector.get_table_names()) - {"alembic_version"}) == set(
        APPROVED_MODULE_08_TABLES
    )
    engine.dispose()


def test_database_check_constraints_enforced(db_session: Session) -> None:
    # 1. Invalid role rejected by CHECK constraint
    bad_user = AdminUser(
        username="invalid_role_user",
        display_name="Bad Role",
        password_hash="$2b$10$abcdefghijklmnopqrstuv1234567890abcdefghijklmnopqrstu",
        role="SUPERADMIN_INVENTED",
        preferred_locale="en",
        is_active=True,
    )
    db_session.add(bad_user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 2. Workshop resource cannot claim automated live telemetry (status_is_manual_note must be True)
    bad_resource = WorkshopResource(
        display_name_en="Sewing Machine #1",
        display_name_gu="સિવણ મશીન #1",
        resource_category="SEWING_MACHINE",
        reported_count=3,
        status_is_manual_note=False,
    )
    db_session.add(bad_resource)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 3. Internal admin notes cannot be marked customer-visible
    bad_note = InternalAdminNote(
        target_type="ORDER",
        target_ref="ORD-0001",
        visibility="CUSTOMER_VISIBLE",
        content="Should never leak to customer updates",
    )
    db_session.add(bad_note)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
