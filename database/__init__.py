"""
Database package for XP & Progress tracking system.
Uses Aiven PostgreSQL for persistent storage.
"""

from .db_connection import get_db, init_db

__all__ = ["get_db", "init_db"]
