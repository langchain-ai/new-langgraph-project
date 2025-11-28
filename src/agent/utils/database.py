"""Simple database connection pool manager."""

import psycopg2
from psycopg2 import pool

from ..config.settings import database


class DatabaseManager:
    """Simple singleton database connection pool manager."""

    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_pool(self):
        """Get or create the connection pool.

        Creates a psycopg2 connection pool using configuration from DatabaseConfig.
        Automatically handles both local and remote database connections based on
        the USE_REMOTE_DB environment variable.

        Returns:
            psycopg2.pool.SimpleConnectionPool: Database connection pool (2-10 connections).
        """
        if self._pool is None:
            conn_params = database.get_connection_params()
            self._pool = psycopg2.pool.SimpleConnectionPool(
                minconn=2,
                maxconn=10,
                **conn_params
            )
        return self._pool

    def get_connection(self):
        """Get a connection from the pool."""
        pool = self.get_pool()
        return pool.getconn()

    def return_connection(self, conn):
        """Return a connection to the pool."""
        pool = self.get_pool()
        pool.putconn(conn)


# Global instance
db_manager = DatabaseManager()
