import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    host: str = os.getenv("POSTGRES_HOST")
    port: int = int(os.getenv("POSTGRES_PORT")) if os.getenv("POSTGRES_PORT") else None
    database: str = os.getenv("POSTGRES_DB")
    username: str = os.getenv("POSTGRES_USER")
    password: str = os.getenv("POSTGRES_PASSWORD")
    schema: str = os.getenv("POSTGRES_SCHEMA")

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


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
