"""
Universal Database Datastore Package

This package provides a universal database abstraction layer supporting
multiple database types including DuckDB, PostgreSQL, MySQL, and more.

Example usage:
    from app.services.datastore import create_datastore

    # Create datastore from connection string
    datastore = create_datastore("postgresql://user:pass@host:5432/db")

    # Execute queries
    result = datastore.execute("SELECT * FROM users LIMIT 10")
    print(f"Database type: {datastore.dialect}")
"""

from .base_datastore import (
    BaseDatastore,
    ConnectionError,
    DatastoreError,
    UnsupportedDatabaseError,
)
from .connection_factory import ConnectionFactory, create_datastore
from .duckdb_datastore import DuckDBDatastore

# Try to import optional database implementations
try:
    from .postgresql_datastore import PostgreSQLDatastore
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

try:
    from .mysql_datastore import MySQLDatastore
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

__all__ = [
    # Base classes
    'BaseDatastore',
    'DatastoreError',
    'UnsupportedDatabaseError',
    'ConnectionError',

    # Factory
    'ConnectionFactory',
    'create_datastore',

    # Implementations
    'DuckDBDatastore',
]

# Add optional implementations to exports
if POSTGRESQL_AVAILABLE:
    __all__.append('PostgreSQLDatastore')

if MYSQL_AVAILABLE:
    __all__.append('MySQLDatastore')

# Version info
__version__ = '1.0.0'