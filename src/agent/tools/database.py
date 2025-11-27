"""Database tools for the Coder agent with async wrappers."""
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain_core.tools import tool

from ..utils.database import db_manager

# Thread pool for blocking DB operations
_executor = ThreadPoolExecutor(max_workers=5)


def _sync_test_connection() -> str:
    """Sync implementation of database connection test."""
    try:
        # Get connection from pool
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        # Test basic query
        cursor.execute("SELECT 1 as test_value")
        result = cursor.fetchone()

        # Get database version
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]

        # Get current database name
        cursor.execute("SELECT current_database()")
        db_name = cursor.fetchone()[0]

        cursor.close()
        db_manager.return_connection(conn)

        return (
            f"✅ Database connection successful!\n"
            f"Database: {db_name}\n"
            f"Test query result: {result[0]}\n"
            f"Version: {version[:50]}..."
        )

    except Exception as e:
        return f"❌ Database connection failed: {str(e)}"


def _sync_execute_query(query: str) -> str:
    """Sync implementation of query execution."""
    try:
        # Validate query type (basic security check)
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            return "❌ Only SELECT queries are allowed for audit data retrieval."

        # Get connection from pool
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        # Execute the query
        cursor.execute(query)
        results = cursor.fetchall()

        # Get column names
        column_names = (
            [desc[0] for desc in cursor.description] if cursor.description else []
        )

        cursor.close()
        db_manager.return_connection(conn)

        # Format results
        if not results:
            return "✅ Query executed successfully. No results returned."

        # Create formatted output
        output = f"✅ Query executed successfully. {len(results)} row(s) returned.\n\n"

        # Add column headers
        if column_names:
            header = " | ".join(column_names)
            separator = "-" * len(header)
            output += f"{header}\n{separator}\n"

        # Add data rows
        for row in results:
            formatted_row = " | ".join(
                str(value) if value is not None else "NULL" for value in row
            )
            output += f"{formatted_row}\n"

        return output

    except Exception as e:
        return f"❌ Query execution failed: {str(e)}"


@tool(
    description="Test PostgreSQL database connection pool functionality and verify connectivity. Use when auditor requests database testing or connectivity verification.",
)
async def test_database_connection() -> str:
    """Test database connection pool functionality.

    This tool verifies that the database connection pool is working correctly by:
    1. Getting a connection from the pool
    2. Executing a simple test query (SELECT 1)
    3. Checking the database version and connection status
    4. Returning the connection to the pool

    Returns:
        str: Success message with database info, or error details if connection fails

    Use this tool when:
    - Testing initial database connectivity
    - Verifying the connection pool is functioning
    - Debugging database connection issues
    - Confirming database credentials and network access
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _sync_test_connection)


@tool(
    description="""Execute SQL queries against the PostgreSQL audit database.

    Usage: execute_query("SELECT column1, column2 FROM acr.table_name WHERE condition")

    Examples:
    - execute_query("SELECT * FROM acr.audit_debit_on_revenue WHERE year = 2024")
    - execute_query("SELECT account, debit_amount FROM acr.audit_debit_on_revenue WHERE is_outside_materiality = true")

    Security: Only SELECT queries are allowed. Use proper WHERE clauses to filter results.""",
)
async def execute_query(query: str) -> str:
    """Execute a SQL query against the audit database.

    This tool executes SQL queries against the PostgreSQL database containing audit data by:
    1. Getting a connection from the pool
    2. Executing the provided SQL query
    3. Fetching and formatting results
    4. Returning the connection to the pool

    Args:
        query (str): The SQL query to execute. Should be a SELECT statement for data retrieval.

    Returns:
        str: Query results in formatted table format, or error details if query fails

    Use this tool when:
    - Retrieving audit test results from pre-computed tables
    - Querying transaction data for analysis
    - Applying materiality thresholds and filters
    - Executing business logic queries requested by the auditor

    Security Notes:
    - Only SELECT queries are recommended for audit data retrieval
    - Avoid queries that could modify data (INSERT, UPDATE, DELETE)
    - Use proper WHERE clauses to limit result sets
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _sync_execute_query, query)
