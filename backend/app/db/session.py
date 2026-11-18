"""SQLAlchemy 2.0 engine, session management, and audit immutability DB triggers."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db import models as _models  # noqa: F401 - register 6 approved models on Base.metadata
from app.db.base import Base


def build_engine(database_url: str) -> Engine:
    is_sqlite = database_url.startswith("sqlite")
    connect_args: dict[str, Any] = {}
    engine_kwargs: dict[str, Any] = {"future": True}

    if is_sqlite:
        connect_args["check_same_thread"] = False
        if ":memory:" in database_url:
            engine_kwargs["poolclass"] = StaticPool
    else:
        engine_kwargs["pool_pre_ping"] = True

    engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)

    if is_sqlite:
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA busy_timeout=5000;")
            if ":memory:" not in database_url:
                cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.close()

    return engine


def install_audit_immutability_triggers(engine: Engine) -> None:
    """Install dialect-appropriate append-only triggers on ``admin_audit_logs``."""
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            conn.execute(
                text(
                    """
                    CREATE TRIGGER IF NOT EXISTS trg_admin_audit_logs_no_update
                    BEFORE UPDATE ON admin_audit_logs
                    BEGIN
                        SELECT RAISE(ABORT, 'AUDIT_LOG_IMMUTABLE: UPDATE forbidden on admin_audit_logs');
                    END;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TRIGGER IF NOT EXISTS trg_admin_audit_logs_no_delete
                    BEFORE DELETE ON admin_audit_logs
                    BEGIN
                        SELECT RAISE(ABORT, 'AUDIT_LOG_IMMUTABLE: DELETE forbidden on admin_audit_logs');
                    END;
                    """
                )
            )
        elif dialect == "postgresql":
            conn.execute(
                text(
                    """
                    CREATE OR REPLACE FUNCTION forbid_admin_audit_logs_mutation()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        RAISE EXCEPTION 'AUDIT_LOG_IMMUTABLE: % forbidden on admin_audit_logs', TG_OP;
                    END;
                    $$ LANGUAGE plpgsql;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    DROP TRIGGER IF EXISTS trg_admin_audit_logs_immutable ON admin_audit_logs;
                    CREATE TRIGGER trg_admin_audit_logs_immutable
                    BEFORE UPDATE OR DELETE ON admin_audit_logs
                    FOR EACH ROW EXECUTE FUNCTION forbid_admin_audit_logs_mutation();
                    """
                )
            )


def init_db_schema(engine: Engine) -> None:
    """Create the 6 approved Module 08 tables and install audit immutability triggers."""
    Base.metadata.create_all(bind=engine)
    install_audit_immutability_triggers(engine)


_default_engine: Engine | None = None
_default_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _default_engine
    if _default_engine is None:
        settings = get_settings()
        _default_engine = build_engine(settings.database_url)
    return _default_engine


def get_session_factory() -> sessionmaker[Session]:
    global _default_session_factory
    if _default_session_factory is None:
        _default_session_factory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _default_session_factory


def reset_db_globals() -> None:
    """Reset module-cached engine/sessionmaker (used in isolated tests)."""
    global _default_engine, _default_session_factory
    if _default_engine is not None:
        _default_engine.dispose()
    _default_engine = None
    _default_session_factory = None


def get_db() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
