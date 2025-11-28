import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    # Database mode selection
    use_remote_db: bool = os.getenv("USE_REMOTE_DB", "false").lower() == "true"

    # Remote database configuration (Azure)
    db_url: str | None = os.getenv("DB_URL")

    # Local database configuration
    host: str | None = os.getenv("POSTGRES_HOST")
    port: int | None = int(os.getenv("POSTGRES_PORT")) if os.getenv("POSTGRES_PORT") else None
    database: str | None = os.getenv("POSTGRES_DB")
    username: str | None = os.getenv("POSTGRES_USER")
    password: str | None = os.getenv("POSTGRES_PASSWORD")

    # Schema configuration (used in both modes)
    schema: str = os.getenv("POSTGRES_SCHEMA", "acr")

    def __post_init__(self):
        """Validate configuration based on selected database mode.

        Raises:
            ValueError: If required environment variables are missing for the selected mode.
        """
        if self.use_remote_db:
            if not self.db_url:
                raise ValueError(
                    "Remote database mode enabled (USE_REMOTE_DB=true) but DB_URL is not set. "
                    "Please provide the Azure PostgreSQL connection string via DB_URL environment variable."
                )
        else:
            missing = []
            if not self.host:
                missing.append("POSTGRES_HOST")
            if not self.port:
                missing.append("POSTGRES_PORT")
            if not self.database:
                missing.append("POSTGRES_DB")
            if not self.username:
                missing.append("POSTGRES_USER")
            if not self.password:
                missing.append("POSTGRES_PASSWORD")

            if missing:
                raise ValueError(
                    f"Local database mode enabled (USE_REMOTE_DB=false) but required "
                    f"environment variables are missing: {', '.join(missing)}"
                )

    @property
    def connection_string(self) -> str:
        """Get the connection string for the current database configuration.

        Returns:
            str: PostgreSQL connection string (DSN format).
        """
        if self.use_remote_db:
            return self.db_url
        else:
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    def get_connection_params(self) -> dict:
        """Get psycopg2 connection parameters for the current database mode.

        Returns dict suitable for unpacking into psycopg2.pool.SimpleConnectionPool():
        - Remote mode: {"dsn": "postgresql://..."}
        - Local mode: {"host": "...", "port": ..., "database": "...", "user": "...", "password": "..."}

        Returns:
            dict: Connection parameters for psycopg2 connection pool.
        """
        if self.use_remote_db:
            return {"dsn": self.db_url}
        else:
            return {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "user": self.username,
                "password": self.password,
            }


@dataclass
class ClaudeConfig:
    api_key: str = os.getenv("ANTHROPIC_API_KEY")
    model: str = os.getenv("CLAUDE_MODEL")
    temperature: float = (
        float(os.getenv("CLAUDE_TEMPERATURE"))
        if os.getenv("CLAUDE_TEMPERATURE")
        else None
    )
    max_tokens: int = (
        int(os.getenv("CLAUDE_MAX_TOKENS")) if os.getenv("CLAUDE_MAX_TOKENS") else None
    )

    def get_llm(self):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            anthropic_api_key=self.api_key,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )


# Global instances
database = DatabaseConfig()
claude = ClaudeConfig()
