"""
Database Connection Factory

This module provides a factory for creating database datastore instances
based on connection strings or configuration.
"""

import re
from typing import Dict, Optional, Type
from urllib.parse import urlparse

from app.services.datastore.base_datastore import (
    BaseDatastore,
    ConnectionError,
    UnsupportedDatabaseError,
)
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.datastore.mysql_datastore import MySQLDatastore
from app.services.datastore.postgresql_datastore import PostgreSQLDatastore


class ConnectionFactory:
    """
    Factory class for creating database datastore instances.
    Automatically detects database type from connection strings.
    """

    # Registry of supported database types
    _DATASTORE_REGISTRY: Dict[str, Type[BaseDatastore]] = {
        'duckdb': DuckDBDatastore,
        'postgresql': PostgreSQLDatastore,
        'postgres': PostgreSQLDatastore,  # Alternative name
        'mysql': MySQLDatastore,
        'mariadb': MySQLDatastore,  # MariaDB uses MySQL protocol
    }

    # Common file extensions for database files
    _FILE_EXTENSIONS = {
        '.db': 'duckdb',
        '.duckdb': 'duckdb',
        '.sqlite': 'duckdb',  # DuckDB can read SQLite files
        '.sqlite3': 'duckdb',
    }

    @classmethod
    def create_datastore(cls, connection_string: str) -> BaseDatastore:
        """
        Create a datastore instance based on the connection string.

        Args:
            connection_string: Database connection string or file path

        Returns:
            BaseDatastore: Appropriate datastore implementation

        Raises:
            UnsupportedDatabaseError: If database type is not supported
            ConnectionError: If connection fails
        """
        try:
            db_type = cls._detect_database_type(connection_string)
            datastore_class = cls._get_datastore_class(db_type)

            # Create and test the connection
            datastore = datastore_class(connection_string)

            if not datastore.test_connection():
                raise ConnectionError(
                    f"Failed to connect to {db_type} database: {connection_string}"
                )

            return datastore

        except Exception as e:
            if isinstance(e, (UnsupportedDatabaseError, ConnectionError)):
                raise
            raise ConnectionError(f"Failed to create datastore: {e}")

    @classmethod
    def _detect_database_type(cls, connection_string: str) -> str:
        """
        Detect database type from connection string.

        Args:
            connection_string: Database connection string or file path

        Returns:
            str: Database type identifier

        Raises:
            UnsupportedDatabaseError: If database type cannot be determined
        """
        # Check if it's a URL-style connection string
        if '://' in connection_string:
            parsed = urlparse(connection_string)
            scheme = parsed.scheme.lower()

            if scheme in cls._DATASTORE_REGISTRY:
                return scheme

            # Handle special cases
            if scheme in ['postgres', 'postgresql']:
                return 'postgresql'
            elif scheme in ['mysql', 'mariadb']:
                return 'mysql'

        # Check if it's a file path
        elif cls._is_file_path(connection_string):
            return cls._detect_file_database_type(connection_string)

        # Default fallback - assume DuckDB for simple strings
        return 'duckdb'

    @classmethod
    def _is_file_path(cls, connection_string: str) -> bool:
        """Check if the connection string looks like a file path."""
        return (
            '/' in connection_string or
            '\\' in connection_string or
            '.' in connection_string or
            connection_string == ':memory:'
        )

    @classmethod
    def _detect_file_database_type(cls, file_path: str) -> str:
        """
        Detect database type from file extension.

        Args:
            file_path: Database file path

        Returns:
            str: Database type identifier
        """
        # Special cases
        if file_path == ':memory:':
            return 'duckdb'

        # Check file extension
        for ext, db_type in cls._FILE_EXTENSIONS.items():
            if file_path.lower().endswith(ext):
                return db_type

        # Default to DuckDB for unknown file types
        return 'duckdb'

    @classmethod
    def _get_datastore_class(cls, db_type: str) -> Type[BaseDatastore]:
        """
        Get datastore class for the given database type.

        Args:
            db_type: Database type identifier

        Returns:
            Type[BaseDatastore]: Datastore class

        Raises:
            UnsupportedDatabaseError: If database type is not supported
        """
        if db_type not in cls._DATASTORE_REGISTRY:
            raise UnsupportedDatabaseError(
                f"Unsupported database type: {db_type}. "
                f"Supported types: {list(cls._DATASTORE_REGISTRY.keys())}"
            )

        return cls._DATASTORE_REGISTRY[db_type]

    @classmethod
    def get_supported_databases(cls) -> list:
        """
        Get list of supported database types.

        Returns:
            list: List of supported database type identifiers
        """
        return list(cls._DATASTORE_REGISTRY.keys())

    @classmethod
    def register_datastore(cls, db_type: str, datastore_class: Type[BaseDatastore]):
        """
        Register a new datastore type.

        Args:
            db_type: Database type identifier
            datastore_class: Datastore implementation class
        """
        cls._DATASTORE_REGISTRY[db_type] = datastore_class

    @classmethod
    def is_supported(cls, connection_string: str) -> bool:
        """
        Check if a connection string is supported.

        Args:
            connection_string: Database connection string or file path

        Returns:
            bool: True if supported
        """
        try:
            db_type = cls._detect_database_type(connection_string)
            return db_type in cls._DATASTORE_REGISTRY
        except Exception:
            return False


# Convenience function for creating datastores
def create_datastore(connection_string: str) -> BaseDatastore:
    """
    Create a datastore instance from a connection string.

    Args:
        connection_string: Database connection string or file path

    Returns:
        BaseDatastore: Configured datastore instance
    """
    return ConnectionFactory.create_datastore(connection_string)