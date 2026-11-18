"""Declarative base for Module 08 SQLAlchemy 2.0 models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for the six approved Module 08 internal tables."""
