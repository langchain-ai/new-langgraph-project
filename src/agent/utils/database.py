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
        """Get or create the connection pool."""
        if self._pool is None:
            self._pool = psycopg2.pool.SimpleConnectionPool(
                minconn=2,
                maxconn=10,
                host=database.host,
                port=database.port,
                database=database.database,
                user=database.username,
                password=database.password,
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
