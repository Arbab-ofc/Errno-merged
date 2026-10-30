"""Shared SQLAlchemy metadata base, without database connection side effects."""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
