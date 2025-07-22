"""
SQL Dialect Manager

This module manages SQL dialect differences between database engines,
providing database-specific SQL syntax and function mappings.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class DialectInfo:
    """Information about a SQL dialect."""
    name: str
    display_name: str
    quote_char: str
    limit_syntax: str
    date_functions: Dict[str, str]
    string_functions: Dict[str, str]
    numeric_functions: Dict[str, str]
    aggregate_functions: Dict[str, str]
    data_types: Dict[str, str]
    features: List[str]


class SQLDialectManager:
    """
    Manages SQL dialect differences between database engines.
    Provides database-specific SQL syntax and function mappings.
    """

    def __init__(self):
        """Initialize the dialect manager with supported dialects."""
        self._dialects = self._initialize_dialects()

    def _initialize_dialects(self) -> Dict[str, DialectInfo]:
        """Initialize supported SQL dialects."""
        return {
            'duckdb': DialectInfo(
                name='duckdb',
                display_name='DuckDB',
                quote_char='"',
                limit_syntax='LIMIT {limit}',
                date_functions={
                    'current_date': 'CURRENT_DATE',
                    'current_timestamp': 'CURRENT_TIMESTAMP',
                    'extract_year': 'EXTRACT(YEAR FROM {column})',
                    'extract_month': 'EXTRACT(MONTH FROM {column})',
                    'date_trunc': "DATE_TRUNC('{part}', {column})",
                    'date_diff': 'DATEDIFF({part}, {start}, {end})',
                },
                string_functions={
                    'concat': 'CONCAT({args})',
                    'upper': 'UPPER({column})',
                    'lower': 'LOWER({column})',
                    'length': 'LENGTH({column})',
                    'substring': 'SUBSTRING({column} FROM {start} FOR {length})',
                    'replace': 'REPLACE({column}, {search}, {replace})',
                },
                numeric_functions={
                    'round': 'ROUND({column}, {digits})',
                    'floor': 'FLOOR({column})',
                    'ceil': 'CEIL({column})',
                    'abs': 'ABS({column})',
                    'power': 'POWER({base}, {exponent})',
                },
                aggregate_functions={
                    'count': 'COUNT({column})',
                    'sum': 'SUM({column})',
                    'avg': 'AVG({column})',
                    'min': 'MIN({column})',
                    'max': 'MAX({column})',
                    'median': 'APPROX_QUANTILE({column}, 0.5)',
                    'stddev': 'STDDEV({column})',
                    'variance': 'VAR_SAMP({column})',
                },
                data_types={
                    'integer': 'INTEGER',
                    'bigint': 'BIGINT',
                    'decimal': 'DECIMAL({precision}, {scale})',
                    'float': 'DOUBLE',
                    'string': 'VARCHAR',
                    'text': 'TEXT',
                    'date': 'DATE',
                    'timestamp': 'TIMESTAMP',
                    'boolean': 'BOOLEAN',
                },
                features=[
                    'window_functions',
                    'cte',
                    'json_functions',
                    'array_functions',
                    'pivot',
                    'unpivot'
                ]
            ),

            'postgresql': DialectInfo(
                name='postgresql',
                display_name='PostgreSQL',
                quote_char='"',
                limit_syntax='LIMIT {limit}',
                date_functions={
                    'current_date': 'CURRENT_DATE',
                    'current_timestamp': 'CURRENT_TIMESTAMP',
                    'extract_year': 'EXTRACT(YEAR FROM {column})',
                    'extract_month': 'EXTRACT(MONTH FROM {column})',
                    'date_trunc': "DATE_TRUNC('{part}', {column})",
                    'date_diff': "EXTRACT(DAYS FROM {end} - {start})",
                },
                string_functions={
                    'concat': 'CONCAT({args})',
                    'upper': 'UPPER({column})',
                    'lower': 'LOWER({column})',
                    'length': 'LENGTH({column})',
                    'substring': 'SUBSTRING({column} FROM {start} FOR {length})',
                    'replace': 'REPLACE({column}, {search}, {replace})',
                },
                numeric_functions={
                    'round': 'ROUND({column}, {digits})',
                    'floor': 'FLOOR({column})',
                    'ceil': 'CEIL({column})',
                    'abs': 'ABS({column})',
                    'power': 'POWER({base}, {exponent})',
                },
                aggregate_functions={
                    'count': 'COUNT({column})',
                    'sum': 'SUM({column})',
                    'avg': 'AVG({column})',
                    'min': 'MIN({column})',
                    'max': 'MAX({column})',
                    'median': 'PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {column})',
                    'stddev': 'STDDEV({column})',
                    'variance': 'VARIANCE({column})',
                },
                data_types={
                    'integer': 'INTEGER',
                    'bigint': 'BIGINT',
                    'decimal': 'DECIMAL({precision}, {scale})',
                    'float': 'REAL',
                    'string': 'VARCHAR',
                    'text': 'TEXT',
                    'date': 'DATE',
                    'timestamp': 'TIMESTAMP',
                    'boolean': 'BOOLEAN',
                },
                features=[
                    'window_functions',
                    'cte',
                    'json_functions',
                    'array_functions',
                    'full_text_search',
                    'recursive_queries'
                ]
            ),

            'mysql': DialectInfo(
                name='mysql',
                display_name='MySQL',
                quote_char='`',
                limit_syntax='LIMIT {limit}',
                date_functions={
                    'current_date': 'CURDATE()',
                    'current_timestamp': 'NOW()',
                    'extract_year': 'YEAR({column})',
                    'extract_month': 'MONTH({column})',
                    'date_trunc': 'DATE({column})',  # MySQL has limited date_trunc
                    'date_diff': 'DATEDIFF({end}, {start})',
                },
                string_functions={
                    'concat': 'CONCAT({args})',
                    'upper': 'UPPER({column})',
                    'lower': 'LOWER({column})',
                    'length': 'CHAR_LENGTH({column})',
                    'substring': 'SUBSTRING({column}, {start}, {length})',
                    'replace': 'REPLACE({column}, {search}, {replace})',
                },
                numeric_functions={
                    'round': 'ROUND({column}, {digits})',
                    'floor': 'FLOOR({column})',
                    'ceil': 'CEILING({column})',
                    'abs': 'ABS({column})',
                    'power': 'POWER({base}, {exponent})',
                },
                aggregate_functions={
                    'count': 'COUNT({column})',
                    'sum': 'SUM({column})',
                    'avg': 'AVG({column})',
                    'min': 'MIN({column})',
                    'max': 'MAX({column})',
                    'median': 'MEDIAN({column})',  # MySQL 8.0+
                    'stddev': 'STDDEV({column})',
                    'variance': 'VARIANCE({column})',
                },
                data_types={
                    'integer': 'INT',
                    'bigint': 'BIGINT',
                    'decimal': 'DECIMAL({precision}, {scale})',
                    'float': 'FLOAT',
                    'string': 'VARCHAR({length})',
                    'text': 'TEXT',
                    'date': 'DATE',
                    'timestamp': 'TIMESTAMP',
                    'boolean': 'BOOLEAN',
                },
                features=[
                    'window_functions',  # MySQL 8.0+
                    'cte',  # MySQL 8.0+
                    'json_functions',  # MySQL 5.7+
                    'full_text_search'
                ]
            )
        }

    def get_dialect_info(self, dialect: str) -> Optional[DialectInfo]:
        """
        Get dialect information for a specific database.

        Args:
            dialect: Database dialect name

        Returns:
            DialectInfo: Dialect information or None if not supported
        """
        return self._dialects.get(dialect.lower())

    def get_supported_dialects(self) -> List[str]:
        """
        Get list of supported SQL dialects.

        Returns:
            List[str]: List of dialect names
        """
        return list(self._dialects.keys())

    def get_function_sql(self, dialect: str, function_type: str,
                        function_name: str, **kwargs) -> Optional[str]:
        """
        Get SQL for a specific function in the given dialect.

        Args:
            dialect: Database dialect name
            function_type: Type of function (date, string, numeric, aggregate)
            function_name: Name of the function
            **kwargs: Function parameters

        Returns:
            str: SQL string or None if not supported
        """
        dialect_info = self.get_dialect_info(dialect)
        if not dialect_info:
            return None

        function_map = getattr(dialect_info, f'{function_type}_functions', {})
        if function_name not in function_map:
            return None

        template = function_map[function_name]
        try:
            return template.format(**kwargs)
        except KeyError:
            return template

    def quote_identifier(self, dialect: str, identifier: str) -> str:
        """
        Quote an identifier using the dialect's quote character.

        Args:
            dialect: Database dialect name
            identifier: Identifier to quote

        Returns:
            str: Quoted identifier
        """
        dialect_info = self.get_dialect_info(dialect)
        if not dialect_info:
            return identifier

        quote_char = dialect_info.quote_char
        return f"{quote_char}{identifier}{quote_char}"

    def format_limit_clause(self, dialect: str, limit: int) -> str:
        """
        Format a LIMIT clause for the given dialect.

        Args:
            dialect: Database dialect name
            limit: Number of rows to limit

        Returns:
            str: LIMIT clause
        """
        dialect_info = self.get_dialect_info(dialect)
        if not dialect_info:
            return f"LIMIT {limit}"

        return dialect_info.limit_syntax.format(limit=limit)

    def has_feature(self, dialect: str, feature: str) -> bool:
        """
        Check if a dialect supports a specific feature.

        Args:
            dialect: Database dialect name
            feature: Feature name to check

        Returns:
            bool: True if feature is supported
        """
        dialect_info = self.get_dialect_info(dialect)
        if not dialect_info:
            return False

        return feature in dialect_info.features

    def get_compatible_function(self, dialect: str, function_name: str) -> Optional[str]:
        """
        Get compatible function name for a dialect.
        Useful for cross-dialect query generation.

        Args:
            dialect: Target database dialect
            function_name: Original function name

        Returns:
            str: Compatible function name or None
        """
        dialect_info = self.get_dialect_info(dialect)
        if not dialect_info:
            return None

        # Search through all function types
        for func_type in ['date_functions', 'string_functions',
                         'numeric_functions', 'aggregate_functions']:
            functions = getattr(dialect_info, func_type, {})
            if function_name in functions:
                return functions[function_name]

        return None


# Global instance
dialect_manager = SQLDialectManager()