"""
SQL Executor Service for extracting and executing SQL queries.
Enhanced with file generation for long content.
"""

import csv
import os
import re
import tempfile
from datetime import datetime

from app.services.datastore.duckdb_datastore import DuckDBDatastore
from config import Config


class SQLExecutor:
    """Service for extracting and executing SQL queries from AI responses."""

    def __init__(self, database_path: str = None):
        if database_path is None:
            database_path = Config.DATABASE_PATH
        self.datastore = DuckDBDatastore(database_path)
        self.temp_dir = tempfile.gettempdir()

    def extract_and_execute_sql(self, text: str) -> str:
        """
        Extract SQL from AI response and execute it against the database.
        Generate downloadable files for long content.
        """
        try:
            # Extract SQL code blocks
            sql_queries = self._extract_sql_queries(text)

            if not sql_queries:
                return text

            results = []
            download_links = []

            for i, sql in enumerate(sql_queries):
                print(f"Executing extracted SQL: {sql}")

                # Check if SQL is long and generate script file
                sql_lines = sql.strip().split('\n')
                if len(sql_lines) > 35:  # Threshold for long SQL
                    script_path = self._generate_sql_script(sql, i)
                    download_links.append({
                        'type': 'sql_script',
                        'filename': os.path.basename(script_path),
                        'path': script_path,
                        'description': (f'SQL Script {i+1} '
                                      f'({len(sql_lines)} lines)')
                    })

                try:
                    # Execute the SQL
                    result_df = self.datastore.execute(sql)

                    # Convert DataFrame to list of dictionaries for consistent handling
                    if result_df is not None and not result_df.empty:
                        result = result_df.to_dict('records')
                        result_count = len(result)

                        # Check if result should be shown in popup (> 5 rows)
                        if result_count > 5:  # Changed from 12 to 5
                            # Show only first 3 rows inline
                            truncated_result = result[:3]
                            result_text = self._format_result_as_markdown_table(
                                truncated_result
                            )

                            # Add full data popup for long results
                            full_table = self._format_result_as_markdown_table(result)
                            popup_id = f"data-popup-{i}"

                            result_text += f"\n\n*Showing first 3 rows of {result_count} total rows.*\n\n"
                            result_text += f'<div id="{popup_id}" class="hidden-data" style="display: none;">\n{full_table}\n</div>'

                            # Generate CSV for download (but don't show buttons - handled in table headers)
                            csv_path = self._generate_csv_file(result_df, i)
                            download_links.append({
                                'type': 'csv_data',
                                'filename': os.path.basename(csv_path),
                                'path': csv_path,
                                'description': (f'Query Results {i+1} '
                                              f'({result_count} rows)')
                            })
                        else:
                            # Short table - show normally (actions handled in table header)
                            result_text = self._format_result_as_markdown_table(result)
                            popup_id = f"data-popup-{i}"
                            full_table = self._format_result_as_markdown_table(result)
                            result_text += f'<div id="{popup_id}" class="hidden-data" style="display: none;">\n{full_table}\n</div>'

                        results.append(f"**Query Results:**\n{result_text}")
                    else:
                        results.append("**Query Results:** No data found.")

                except Exception as e:
                    error_msg = f"**SQL execution error:** {str(e)}"
                    print(f"SQL execution error: {e}")
                    results.append(error_msg)

            # Build final response without download section at top
            final_response = text

            # Note: Download links are generated but not displayed at the top
            # The download functionality is still available through inline options

            if results:
                final_response += "\n\n" + "\n\n".join(results)

            return final_response

        except Exception as e:
            print(f"Error in extract_and_execute_sql: {e}")
            return text

    def _extract_sql_queries(self, text: str) -> list:
        """Extract SQL code blocks from the text"""
        patterns = [
            r'```sql\s*\n(.*?)\n```',
            r'```\s*\n((?:SELECT|WITH|INSERT|UPDATE|DELETE|CREATE).*?)\n```',
        ]

        queries = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            queries.extend([match.strip() for match in matches if match.strip()])

        return queries

    def _generate_sql_script(self, sql: str, query_index: int) -> str:
        """Generate a downloadable SQL script file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sql_query_{query_index+1}_{timestamp}.sql"
        filepath = os.path.join(self.temp_dir, filename)

        # Add header comment
        header = f"""-- SQL Query Script
-- Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
-- Query Index: {query_index + 1}
--
-- Execute this script against your DuckDB database
--

"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header + sql)

        return filepath

    def _generate_csv_file(self, data, query_index: int) -> str:
        """Generate a downloadable CSV file from query results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"query_results_{query_index+1}_{timestamp}.csv"
        filepath = os.path.join(self.temp_dir, filename)

        try:
            # Handle pandas DataFrame
            if hasattr(data, 'to_csv'):
                data.to_csv(filepath, index=False, encoding='utf-8')
            elif isinstance(data, list) and data:
                # Handle list of dictionaries
                if isinstance(data[0], dict):
                    headers = list(data[0].keys())
                    with open(filepath, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=headers)
                        writer.writeheader()
                        writer.writerows(data)
                else:
                    # Handle list of tuples/lists
                    with open(filepath, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerows(data)
            else:
                # Create empty file if no data
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("")
        except Exception as e:
            print(f"Error generating CSV file: {e}")
            # Create a simple error file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Error generating CSV: {str(e)}")

        return filepath

    def _build_downloads_section(self, download_links: list) -> str:
        """Build the downloads section for the response"""
        if not download_links:
            return ""

        section = "## 📥 **Download Files**\n\n"

        for link in download_links:
            icon = "📄" if link['type'] == 'sql_script' else "📊"
            section += f"{icon} **{link['description']}**\n"
            section += f"   └── `{link['filename']}`\n\n"

        section += ("*Files are available for download and can be used with "
                   "your preferred SQL editor or data analysis tools.*\n")
        return section

    def _format_result_as_markdown_table(self, data: list) -> str:
        """Format query results as a markdown table"""
        if not data:
            return "No data found."

        # Handle different data formats
        if isinstance(data[0], dict):
            headers = list(data[0].keys())
            rows = [[row.get(header, '') for header in headers]
                   for row in data]
        elif isinstance(data[0], (list, tuple)):
            # Assume first row might be headers, or generate generic ones
            if (len(data) > 1 and
                all(isinstance(item, str) for item in data[0])):
                headers = data[0]
                rows = data[1:]
            else:
                headers = [f"Column {i+1}" for i in range(len(data[0]))]
                rows = data
        else:
            return str(data)

        # Build markdown table
        table = "|" + "|".join(str(h) for h in headers) + "|\n"
        table += "|" + "|".join("---" for _ in headers) + "|\n"

        for row in rows:
            table += ("|" +
                     "|".join(str(cell) if cell is not None else ""
                             for cell in row) + "|\n")

        return table


# Singleton instance
_sql_executor = None

def get_sql_executor() -> SQLExecutor:
    """Get the singleton SQL executor instance."""
    global _sql_executor
    if _sql_executor is None:
        _sql_executor = SQLExecutor()
    return _sql_executor